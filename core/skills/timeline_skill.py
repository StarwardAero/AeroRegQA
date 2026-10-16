"""时间线梳理 Skill — 处理法规演变历史、时间节点类问题。

适用场景：
- 某项法规的出台、修订历程
- 适航管理政策的演变时间线
- 关键时间节点梳理（生效日期、过渡期等）
"""

from __future__ import annotations

from typing import Callable

from core.skills.base_skill import BaseSkill, SkillResult
from core.skills.utils import emit_agent_step, stream_checked_answer, unique_source_files, validate_citations


class TimelineSkill(BaseSkill):
    """时间线梳理 Skill：提取并整理法规相关的时间线。"""

    def __init__(self, llm_client, retriever) -> None:
        self._llm = llm_client
        self._retriever = retriever

    @property
    def name(self) -> str:
        return "timeline"

    @property
    def description(self) -> str:
        return "梳理法规演变历史、时间节点、发展历程等时间相关问题"

    @property
    def keywords(self) -> list[str]:
        return [
            "时间", "历史", "历程", "发展", "演变", "沿革",
            "何时", "什么时候", "生效", "修订", "颁布", "废止",
            "过渡期", "截止", "年", "月", "日期", "阶段",
        ]

    def execute(
        self,
        question: str,
        chat_history: list[dict] | None = None,
        stop_event=None,
        on_step: Callable | None = None,
        on_token: Callable | None = None,
    ) -> SkillResult:
        emit_agent_step(on_step, "timeline_retrieve", "正在检索时间线相关信息...")

        chunks = self._retriever.retrieve(question, top_k=6)
        if not chunks:
            return SkillResult(
                answer="未找到相关的时间线信息。",
                sources=[],
                skill_name=self.name,
                confidence=0.2,
            )

        context = self._retriever.format_context(chunks)

        emit_agent_step(on_step, "timeline_analyze", "正在整理时间线...")

        system_prompt = (
            "你是民航法规历史研究专家。请从参考资料中提取与用户问题相关的时间信息，"
            "整理为清晰的时间线。\n\n"
            "要求：\n"
            "1. 按时间顺序排列，使用如下格式：\n"
            "   - **YYYY年MM月** — 事件描述 [引用编号]\n"
            "2. 如果时间不精确（仅有年份），标注为「约YYYY年」。\n"
            "3. 标注每个时间节点的重要程度（关键/一般）。\n"
            "4. 在时间线后给出简要的演变趋势分析。\n"
            "5. 不要编造时间信息，仅使用资料中出现的日期。\n"
            "6. 如参考资料中时间信息有限，如实说明。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"参考资料：\n{context}\n\n问题：{question}"},
        ]

        answer = self._llm.chat(messages)
        answer, citation_result = validate_citations(answer, chunks)
        emit_agent_step(on_step, "citation_check", f"引用校验: {citation_result.valid_citations}/{citation_result.total_citations}", citation_result.__dict__)
        stream_checked_answer(answer, on_token, stop_event)

        sources = unique_source_files(chunks)

        return SkillResult(
            answer=answer,
            sources=sources,
            skill_name=self.name,
            confidence=0.75,
            metadata={"chunks_used": len(chunks), "citation_check": citation_result.__dict__},
        )
