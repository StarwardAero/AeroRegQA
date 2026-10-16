"""Compliance Check Skill — 合规性检查分析。"""

from __future__ import annotations

from typing import Any, Callable

from utils.logger import get_logger
from core.skills.base_skill import BaseSkill, SkillResult
from core.vectorstore.retriever import HybridRetriever
from core.rag.llm_client import LLMClient
from core.skills.utils import emit_agent_step, stream_checked_answer, unique_source_files, validate_citations
from config.prompts import COMPLIANCE_CHECK_SYSTEM_PROMPT, format_compliance_prompt

log = get_logger(__name__)


class ComplianceCheckSkill(BaseSkill):
    """合规性检查 Skill — 对用户场景进行法规合规性分析。"""

    def __init__(self, retriever: HybridRetriever, llm: LLMClient) -> None:
        self.retriever = retriever
        self.llm = llm

    @property
    def name(self) -> str:
        return "compliance_check"

    @property
    def description(self) -> str:
        return "合规性检查：根据用户给出的具体场景参数，判断是否满足适航法规要求"

    @property
    def keywords(self) -> list[str]:
        return ["合规", "是否满足", "是否符合", "需要满足", "起飞重量", "许可"]

    def execute(
        self,
        question: str,
        chat_history: list[dict],
        stop_event: Any = None,
        on_step: Callable | None = None,
        on_token: Callable | None = None,
    ) -> SkillResult:
        log.info(f"[ComplianceCheckSkill] Executing for: {question[:60]}...")

        # 检索多条法规以进行全面合规检查
        chunks = self.retriever.retrieve(question, top_k=8)
        context = self.retriever.format_context(chunks)
        sources = unique_source_files(chunks)

        emit_agent_step(on_step, "retrieve", f"检索到 {len(chunks)} 个法规条款", {"sources": sources})

        prompt = format_compliance_prompt(context, question)
        messages = [
            {"role": "system", "content": COMPLIANCE_CHECK_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        answer = self.llm.chat(messages, stream=False)
        answer, citation_result = validate_citations(answer, chunks)
        emit_agent_step(on_step, "citation_check", f"引用校验: {citation_result.valid_citations}/{citation_result.total_citations}", citation_result.__dict__)
        stream_checked_answer(answer, on_token, stop_event)

        return SkillResult(
            answer=answer,
            sources=sources,
            skill_name=self.name,
            iterations=1,
            metadata={"citation_check": citation_result.__dict__},
            was_interrupted=bool(stop_event and stop_event.is_set()),
        )
