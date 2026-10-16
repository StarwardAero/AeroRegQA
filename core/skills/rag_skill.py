"""RAG Skill — 封装原有 AgenticRAG 为标准 Skill。"""

from __future__ import annotations

from typing import Any, Callable

from utils.logger import get_logger
from core.skills.base_skill import BaseSkill, SkillResult
from core.rag.agent import AgenticRAG

log = get_logger(__name__)


class RAGSkill(BaseSkill):
    """知识库检索问答 Skill — 核心 Skill，处理法规条款查询、审定要求等。"""

    def __init__(self, agent: AgenticRAG) -> None:
        self.agent = agent

    @property
    def name(self) -> str:
        return "rag"

    @property
    def description(self) -> str:
        return "知识库检索问答：查询适航法规条款、审定要求、管理规定等具体内容"

    @property
    def keywords(self) -> list[str]:
        return ["法规", "条款", "CCAR", "适航", "审定", "要求", "规定", "条例", "标准"]

    def execute(
        self,
        question: str,
        chat_history: list[dict],
        stop_event: Any = None,
        on_step: Callable | None = None,
        on_token: Callable | None = None,
    ) -> SkillResult:
        log.info(f"[RAGSkill] Executing for: {question[:60]}...")
        response = self.agent.run(
            question=question,
            chat_history=chat_history,
            stop_event=stop_event,
            on_step=on_step,
            on_token=on_token,
        )
        return SkillResult(
            answer=response.final_answer,
            sources=response.sources,
            skill_name=self.name,
            iterations=response.total_iterations,
            was_interrupted=response.was_interrupted,
            metadata={"steps": [s.__dict__ for s in response.steps]},
        )
