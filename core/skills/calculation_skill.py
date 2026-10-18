"""计算分析 Skill — 处理涉及数值计算、统计分析的问题。

适用场景：
- 法规中的数值参数计算（限高、限速、限重等）
- 多个法规条款的参数对比
- 适航审定标准中的数值要求汇总
"""

from __future__ import annotations

import re
from typing import Callable

from core.skills.base_skill import BaseSkill, SkillResult
from core.skills.utils import emit_agent_step, stream_checked_answer, unique_source_files, validate_citations


class CalculationSkill(BaseSkill):
    """计算分析 Skill：提取法规数值参数并进行结构化分析。"""

    def __init__(self, llm_client, retriever) -> None:
        self._llm = llm_client
        self._retriever = retriever

    @property
    def name(self) -> str:
        return "calculation"

    @property
    def description(self) -> str:
        return "处理涉及数值计算、参数统计、数据提取的法规问题"

    @property
    def keywords(self) -> list[str]:
        return [
            "计算", "多少", "数值", "限高", "限速", "限重",
            "最大", "最小", "范围", "标准值", "参数",
            "统计", "百分比", "概率", "数量",
        ]

    def execute(
        self,
        question: str,
        chat_history: list[dict] | None = None,
        stop_event=None,
        on_step: Callable | None = None,
        on_token: Callable | None = None,
    ) -> SkillResult:
        """检索法规中的数值信息并进行结构化分析。"""
        emit_agent_step(on_step, "calculation_retrieve", "正在检索相关数值参数...")

        # 检索
        chunks = self._retriever.retrieve(question, top_k=6)
        if not chunks:
            return SkillResult(
                answer="未找到相关的数值参数信息。",
                sources=[],
                skill_name=self.name,
                confidence=0.2,
            )

        context = self._retriever.format_context(chunks)

        # 提取数值并分析
        emit_agent_step(on_step, "calculation_analyze", "正在分析数值参数...")

        system_prompt = (
            "你是民航法规数值分析专家。请从以下参考资料中提取与用户问题相关的数值参数，"
            "并进行结构化整理。\n\n"
            "要求：\n"
            "1. 所有数值必须标注来源引用编号 [n]。\n"
            "2. 使用表格或列表清晰呈现参数。\n"
            "3. 如有多个来源的不同数值，明确标注差异。\n"
            "4. 如需计算，展示计算过程。\n"
            "5. 不要编造数据，仅使用参考资料中出现的数值。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"参考资料：\n{context}\n\n问题：{question}",
            },
        ]

        answer = self._llm.chat(messages)
        answer, citation_result = validate_citations(answer, chunks, self._llm, question)
        emit_agent_step(on_step, "citation_check", f"引用校验: {citation_result.valid_citations}/{citation_result.total_citations}", citation_result.__dict__)
        stream_checked_answer(answer, on_token, stop_event)

        sources = unique_source_files(chunks)

        return SkillResult(
            answer=answer,
            sources=sources,
            skill_name=self.name,
            confidence=0.8,
            metadata={"chunks_used": len(chunks), "citation_check": citation_result.__dict__},
        )
