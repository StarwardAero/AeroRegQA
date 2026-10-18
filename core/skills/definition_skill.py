"""Definition Skill — 术语解释与概念辨析。"""

from __future__ import annotations

from typing import Any, Callable

from utils.logger import get_logger
from core.skills.base_skill import BaseSkill, SkillResult
from core.vectorstore.retriever import HybridRetriever
from core.rag.llm_client import LLMClient
from core.skills.utils import emit_agent_step, stream_checked_answer, unique_source_files, validate_citations
from config.prompts import DEFINITION_SYSTEM_PROMPT, format_definition_prompt

log = get_logger(__name__)


class DefinitionSkill(BaseSkill):
    """术语解释 Skill — 解释适航领域专业术语、缩写和概念。"""

    def __init__(self, retriever: HybridRetriever, llm: LLMClient) -> None:
        self.retriever = retriever
        self.llm = llm

    @property
    def name(self) -> str:
        return "definition"

    @property
    def description(self) -> str:
        return "术语解释与概念辨析：解释适航领域的专业术语、缩写、概念定义"

    @property
    def keywords(self) -> list[str]:
        return ["什么是", "定义", "解释", "含义", "意思", "概念", "区别"]

    def execute(
        self,
        question: str,
        chat_history: list[dict],
        stop_event: Any = None,
        on_step: Callable | None = None,
        on_token: Callable | None = None,
    ) -> SkillResult:
        log.info(f"[DefinitionSkill] Executing for: {question[:60]}...")

        # 精确检索：以较小的 top_k 获取最相关的定义
        chunks = self.retriever.retrieve(question, top_k=5)
        context = self.retriever.format_context(chunks)
        sources = unique_source_files(chunks)

        emit_agent_step(on_step, "retrieve", f"检索到 {len(chunks)} 个文档片段", {"sources": sources})

        prompt = format_definition_prompt(context, question)
        messages = [
            {"role": "system", "content": DEFINITION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        answer = self.llm.chat(messages, stream=False)
        answer, citation_result = validate_citations(answer, chunks, self.llm, question)
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
