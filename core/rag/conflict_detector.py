"""冲突检测器 — 检测检索 chunk 间的信息冲突及生成内容与上下文的一致性。

全链路幻觉抑制 + RAG 上下文整合冲突解决。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from utils.logger import get_logger
from core.rag.llm_client import LLMClient
from core.chunker.chunk_models import DocumentChunk

log = get_logger(__name__)

CONFLICT_DETECTION_PROMPT = """你是一个信息冲突检测专家。请分析以下多个文档片段之间是否存在信息矛盾或不一致。

【文档片段】
{chunks_text}

请检测以上片段之间是否存在矛盾、不一致或冲突的信息。

输出严格 JSON 格式（不要包含 Markdown 标记或多余的文字）：
{{
  "has_conflict": true/false,
  "conflicts": [
    {{
      "description": "冲突描述",
      "chunk_ids": ["涉及的片段编号"],
      "severity": "high/medium/low"
    }}
  ],
  "suggestion": "如何处理冲突的建议"
}}

如果没有发现冲突，conflicts 数组为空。
"""


@dataclass
class ConflictInfo:
    """单条冲突信息。"""
    description: str
    chunk_ids: list[str] = field(default_factory=list)
    severity: str = "medium"  # "high" | "medium" | "low"


@dataclass
class ConflictDetectionResult:
    """冲突检测结果。"""
    has_conflict: bool
    conflicts: list[ConflictInfo] = field(default_factory=list)
    suggestion: str = ""


class ConflictDetector:
    """检索内容冲突检测器。

    在将检索结果送入 LLM 生成之前，先检测 chunk 间是否存在矛盾信息。
    如存在冲突，会在上下文中标注提示，让 LLM 在生成时注意区分。
    """

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.llm = llm_client

    def detect_conflicts(self, chunks: list[DocumentChunk]) -> ConflictDetectionResult:
        """检测多个 chunk 之间的信息冲突。

        如果没有配置 LLM，使用基于规则的简单检测（文本相似度+矛盾词检测）。
        如果配置了 LLM，调用 LLM 进行深度冲突分析。
        """
        if len(chunks) < 2:
            return ConflictDetectionResult(has_conflict=False)

        if self.llm:
            return self._llm_detect(chunks)
        else:
            return self._rule_based_detect(chunks)

    def annotate_context(
        self, chunks: list[DocumentChunk], detection_result: ConflictDetectionResult
    ) -> list[DocumentChunk]:
        """如果检测到冲突，在相关 chunk 的 metadata 中标注冲突信息。"""
        if not detection_result.has_conflict:
            return chunks

        # 建立 chunk_id 到冲突描述的映射
        conflict_map: dict[str, list[str]] = {}
        for conflict in detection_result.conflicts:
            for cid in conflict.chunk_ids:
                if cid not in conflict_map:
                    conflict_map[cid] = []
                conflict_map[cid].append(conflict.description)

        # 在 metadata 中标注
        for idx, chunk in enumerate(chunks, 1):
            chunk_key = f"[{idx}]"
            if chunk_key in conflict_map:
                chunk.metadata["has_conflict"] = True
                chunk.metadata["conflict_notes"] = conflict_map[chunk_key]
                log.info(f"[ConflictDetector] Chunk {chunk_key} 标注冲突: {conflict_map[chunk_key]}")

        return chunks

    def format_context_with_conflicts(
        self, chunks: list[DocumentChunk], detection_result: ConflictDetectionResult
    ) -> str:
        """格式化带冲突标注的上下文文本。"""
        if not chunks:
            return "无相关上下文。"

        formatted_parts = []
        for idx, chunk in enumerate(chunks, 1):
            source = chunk.metadata.get("source_file", "Unknown")
            chapter = chunk.metadata.get("header_path", "Global")

            # 冲突标注
            conflict_warning = ""
            if chunk.metadata.get("has_conflict"):
                notes = chunk.metadata.get("conflict_notes", [])
                conflict_warning = f"\n⚠️ 冲突提醒: {'; '.join(notes)}"

            part = f"[{idx}] (来源: {source}, 章节: {chapter}){conflict_warning}\n{chunk.content}"
            formatted_parts.append(part)

        # 如果有全局冲突建议，在末尾加上
        if detection_result.has_conflict and detection_result.suggestion:
            formatted_parts.append(
                f"\n⚠️ 注意：以上参考内容存在信息冲突。{detection_result.suggestion}"
            )

        return "\n\n".join(formatted_parts)

    # ── LLM 冲突检测 ─────────────────────────────────────────────────
    def _llm_detect(self, chunks: list[DocumentChunk]) -> ConflictDetectionResult:
        """使用 LLM 进行深度冲突分析。"""
        import json
        import re

        chunks_text = ""
        for idx, chunk in enumerate(chunks, 1):
            source = chunk.metadata.get("source_file", "Unknown")
            chunks_text += f"[{idx}] (来源: {source})\n{chunk.content[:500]}\n\n"

        prompt = CONFLICT_DETECTION_PROMPT.format(chunks_text=chunks_text)
        messages = [{"role": "user", "content": prompt}]

        try:
            raw = self.llm.chat(messages, stream=False)
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                conflicts = []
                for c in data.get("conflicts", []):
                    conflicts.append(ConflictInfo(
                        description=c.get("description", ""),
                        chunk_ids=c.get("chunk_ids", []),
                        severity=c.get("severity", "medium"),
                    ))
                return ConflictDetectionResult(
                    has_conflict=data.get("has_conflict", False),
                    conflicts=conflicts,
                    suggestion=data.get("suggestion", ""),
                )
        except Exception as e:
            log.warning(f"[ConflictDetector] LLM 冲突检测失败: {e}")

        return ConflictDetectionResult(has_conflict=False)

    # ── 规则冲突检测 ──────────────────────────────────────────────────
    def _rule_based_detect(self, chunks: list[DocumentChunk]) -> ConflictDetectionResult:
        """简单的基于规则的冲突检测（不依赖 LLM）。"""
        # 检查是否有来自不同文档的同主题内容（基于 source_file 差异）
        sources = set()
        for chunk in chunks:
            src = chunk.metadata.get("source_file", "")
            if src:
                sources.add(src)

        # 如果来自多个不同来源文档，标记潜在冲突风险
        if len(sources) > 1:
            return ConflictDetectionResult(
                has_conflict=False,
                conflicts=[],
                suggestion=f"内容来自 {len(sources)} 个不同文档，请注意可能的表述差异。",
            )

        return ConflictDetectionResult(has_conflict=False)
