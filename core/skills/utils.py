"""Skill 公共工具。"""

from __future__ import annotations

from typing import Any, Callable

from core.chunker.chunk_models import DocumentChunk
from core.rag.citation_checker import CitationChecker, CitationCheckResult


def unique_source_files(chunks: list[DocumentChunk]) -> list[str]:
    """提取去重后的来源文件名。"""
    return list({c.metadata.get("source_file", "Unknown") for c in chunks})


def validate_citations(answer: str, chunks: list[DocumentChunk], llm=None, question: str = "") -> tuple[str, CitationCheckResult]:
    """校验并清理回答中的非法引用编号。"""
    checker = CitationChecker()
    from core.rag.evidence import evidence_records, evidence_context, GROUNDING_RULES
    records = evidence_records(chunks)
    if llm is not None and chunks:
        answer = llm.chat([
            {"role": "system", "content": GROUNDING_RULES},
            {"role": "user", "content": f"问题：{question}\n\n证据：\n{evidence_context(records)}\n\n候选答案：\n{answer}"},
        ], stream=False)
    result = checker.check(answer, len(chunks))
    if not result.is_valid:
        answer = checker.strip_invalid_citations(answer, len(chunks))
        answer = "⚠️ 该回答未通过引用编号检查，请以下方原文和证据摘录为准。\n\n" + answer
    result.details['references'] = records
    return answer, result


def stream_checked_answer(answer: str, on_token: Callable | None, stop_event: Any = None) -> None:
    """在后验校验之后，将最终文本按字符流式输出。"""
    if not on_token:
        return
    for token in answer:
        if stop_event and stop_event.is_set():
            break
        on_token(token)


def emit_agent_step(on_step: Callable | None, step_type: str, detail: str, metadata: dict | None = None) -> None:
    """兼容 API/UI 的 AgentStep 回调格式。"""
    if not on_step:
        return
    from core.rag.agent import AgentStep

    on_step(AgentStep(step_type, "", detail, 0, metadata or {}))
