"""Skill 抽象基类 — 所有 Skill 必须继承此基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class SkillResult:
    """Skill 执行结果的统一数据结构。"""
    answer: str                              # 最终回答文本
    sources: list[str] = field(default_factory=list)   # 来源列表
    skill_name: str = ""                     # 实际执行的 Skill 名称
    confidence: float = 0.0                  # 执行置信度 (0-1)
    iterations: int = 0                      # 迭代次数（如有）
    metadata: dict = field(default_factory=dict)       # 扩展元数据
    was_interrupted: bool = False            # 是否被用户中断


class BaseSkill(ABC):
    """Skill 抽象基类。

    每个 Skill 代表一种特定的问答处理能力。
    Router 会根据用户意图选择合适的 Skill 执行。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Skill 唯一标识名称（英文小写，用于路由匹配）。"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Skill 功能描述（中文，供 Router LLM 理解能力边界）。"""
        ...

    @property
    def keywords(self) -> list[str]:
        """Skill 关联关键词（用于规则预过滤）。"""
        return []

    @abstractmethod
    def execute(
        self,
        question: str,
        chat_history: list[dict],
        stop_event: Any = None,
        on_step: Callable | None = None,
        on_token: Callable | None = None,
    ) -> SkillResult:
        """执行 Skill 核心逻辑。

        Args:
            question: 用户原始问题
            chat_history: 对话历史
            stop_event: 中断事件
            on_step: 步骤回调
            on_token: Token 流式回调

        Returns:
            SkillResult
        """
        ...

    def to_dict(self) -> dict:
        """序列化为字典，供 Router Prompt 使用。"""
        return {
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
        }
