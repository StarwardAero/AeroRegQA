"""Chitchat Skill — 闲聊/超出范围问题处理。"""

from __future__ import annotations

from typing import Any, Callable

from utils.logger import get_logger
from core.skills.base_skill import BaseSkill, SkillResult
from config.prompts import CHITCHAT_RESPONSE_TEMPLATE

log = get_logger(__name__)


class ChitchatSkill(BaseSkill):
    """闲聊 Skill — 礼貌拒绝非适航问题并引导回正题。"""

    @property
    def name(self) -> str:
        return "chitchat"

    @property
    def description(self) -> str:
        return "闲聊与超出范围：处理与适航法规无关的问题，礼貌引导用户回到正题"

    @property
    def keywords(self) -> list[str]:
        return ["你好", "你是谁", "闲聊", "天气", "写诗"]

    def execute(
        self,
        question: str,
        chat_history: list[dict],
        stop_event: Any = None,
        on_step: Callable | None = None,
        on_token: Callable | None = None,
    ) -> SkillResult:
        log.info(f"[ChitchatSkill] Handling off-topic question: {question[:60]}...")

        answer = CHITCHAT_RESPONSE_TEMPLATE

        # 如果有 on_token 回调，模拟流式输出
        if on_token:
            for char in answer:
                if stop_event and stop_event.is_set():
                    break
                on_token(char)

        return SkillResult(
            answer=answer,
            sources=[],
            skill_name=self.name,
            iterations=0,
            was_interrupted=bool(stop_event and stop_event.is_set()),
        )
