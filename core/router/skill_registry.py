"""Skill 注册表 — 管理所有已注册 Skill 的中心化注册表。"""

from __future__ import annotations

from utils.logger import get_logger
from core.skills.base_skill import BaseSkill

log = get_logger(__name__)


class SkillRegistry:
    """Skill 注册与查找中心。

    所有 Skill 在系统初始化时注册到此处，
    Router 通过 registry 获取可用 Skill 列表与元信息。
    """

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """注册一个 Skill。"""
        if skill.name in self._skills:
            log.warning(f"Skill '{skill.name}' 已存在，将被覆盖")
        self._skills[skill.name] = skill
        log.info(f"Registered Skill: {skill.name} — {skill.description}")

    def get(self, name: str) -> BaseSkill | None:
        """按名称获取 Skill 实例。"""
        return self._skills.get(name)

    def list_skills(self) -> list[dict]:
        """返回所有 Skill 的元信息列表（供 Router Prompt 使用）。"""
        return [skill.to_dict() for skill in self._skills.values()]

    def list_names(self) -> list[str]:
        """返回所有已注册 Skill 的名称。"""
        return list(self._skills.keys())

    @property
    def default_skill_name(self) -> str:
        """默认 Skill 名称（当路由失败时的兜底）。"""
        return "rag"

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        return name in self._skills
