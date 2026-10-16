"""模型路由器 — 根据 Skill 类型和问题复杂度自动选择合适的模型。

三级模型策略（DeepSeek V4 + R1）：
  - lite:     DeepSeek V4（简单任务：闲聊、路由分类）
  - main:     DeepSeek V4（常规任务：RAG问答、对比分析、流程说明）
  - reasoner: DeepSeek R1（复杂任务：Judge评估、多文档综合、深度分析）

设计原则：
  - 简单问题用 V4 即可（省钱）
  - 复杂问题给 R1（保证质量）
  - Judge 评估必须用 R1（评估不准会导致错误的重试）

使用示例：
    from core.router.model_router import ModelRouter, ModelTier
    router = ModelRouter(settings)
    model_name, tier = router.select(skill_name="rag")
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from utils.logger import get_logger

if TYPE_CHECKING:
    from config.settings import Settings

log = get_logger(__name__)


class ModelTier(str, Enum):
    """模型层级。"""
    LITE = "lite"         # 轻量模型（简单任务）
    MAIN = "main"         # 主模型（常规任务）
    REASONER = "reasoner" # 推理模型（复杂任务）


@dataclass
class ModelSelection:
    """模型选择结果。"""
    model_name: str
    tier: ModelTier
    reason: str


# ── Skill → 模型层级映射 ──────────────────────────────────────────
# 根据 Skill 的复杂度决定用哪级模型
SKILL_MODEL_TIER: dict[str, ModelTier] = {
    # 简单任务 → 轻量模型
    "chitchat":     ModelTier.LITE,
    "definition":   ModelTier.LITE,
    "concept":      ModelTier.LITE,

    # 常规任务 → 主模型
    "rag":              ModelTier.MAIN,
    "comparison":       ModelTier.MAIN,
    "procedure":        ModelTier.MAIN,
    "compliance_check": ModelTier.MAIN,
    "calculation":      ModelTier.MAIN,
    "timeline":         ModelTier.MAIN,

    # 复杂任务 → 推理模型
    "summary":      ModelTier.REASONER,    # 全局摘要需要深度理解
    "multi_doc":    ModelTier.REASONER,    # 跨文档综合推理
    "export":       ModelTier.REASONER,    # 复杂的报告生成
    "judge":        ModelTier.REASONER,    # Judge 评估必须用强模型
}

# ── Judge 评估专用 ─────────────────────────────────────────────────
# Judge 始终用推理模型，不按 Skill 走
JUDGE_MODEL_TIER = ModelTier.REASONER


class ModelRouter:
    """三级模型路由器。

    决定逻辑：
      1. Judge 评估 → 强制用 reasoner（不可降级）
      2. 有明确 Skill → 按 SKILL_MODEL_TIER 查表
      3. 未知 Skill → 默认用 main
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def select(self, skill_name: str = "", is_judge: bool = False) -> ModelSelection:
        """根据 Skill 选择模型。

        Args:
            skill_name: Skill 名称（如 "rag", "chitchat", "comparison"）
            is_judge: 是否是 Judge 评估调用

        Returns:
            ModelSelection（模型名、层级、选择理由）
        """
        # Judge 强制用推理模型
        if is_judge:
            return ModelSelection(
                model_name=self._settings.LLM_JUDGE_MODEL_NAME,
                tier=ModelTier.REASONER,
                reason="Judge 评估必须用强模型以保证评分准确性",
            )

        # 按 Skill 查表
        tier = SKILL_MODEL_TIER.get(skill_name, ModelTier.MAIN)
        model_name = self._get_model_for_tier(tier)

        reason = f"Skill '{skill_name}' → 模型层级 '{tier.value}'"
        if skill_name not in SKILL_MODEL_TIER:
            reason = f"Skill '{skill_name}' 不在映射表中，默认用主模型"

        log.info(f"[ModelRouter] {reason} → {model_name}")
        return ModelSelection(model_name=model_name, tier=tier, reason=reason)

    def _get_model_for_tier(self, tier: ModelTier) -> str:
        """获取指定层级对应的模型名。"""
        mapping = {
            ModelTier.LITE:     self._settings.LLM_LITE_MODEL_NAME,
            ModelTier.MAIN:     self._settings.LLM_MODEL_NAME,
            ModelTier.REASONER: self._settings.LLM_REASONER_MODEL_NAME,
        }
        return mapping.get(tier, self._settings.LLM_MODEL_NAME)

    def get_judge_model(self) -> str:
        """获取 Judge 评估专用模型名。"""
        return self._settings.LLM_JUDGE_MODEL_NAME

    def get_router_model(self) -> str:
        """获取意图路由专用模型名（轻量即可）。"""
        return self._settings.LLM_ROUTER_MODEL_NAME

    def estimate_cost(
        self, model_name: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """估算单次调用的成本（元）。

        Args:
            model_name: 模型名称
            prompt_tokens: 输入 token 数
            completion_tokens: 输出 token 数

        Returns:
            估算成本（元）
        """
        input_cost = self._settings.MODEL_COST_PER_1M_INPUT.get(model_name, 1.0)
        output_cost = self._settings.MODEL_COST_PER_1M_OUTPUT.get(model_name, 2.0)
        cost = (prompt_tokens / 1_000_000) * input_cost + (completion_tokens / 1_000_000) * output_cost
        return round(cost, 6)
