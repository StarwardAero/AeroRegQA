"""意图路由器 — 基于 LLM + 规则 的多层防线意图分类。

防线设计（解决乱选 Skill 问题）：
  1. 关键词预过滤：正则/关键词快速缩小候选范围
  2. LLM 结构化分类：输出 JSON（skill + confidence + reason）
  3. 置信度阈值：低于阈值降级到默认 RAGSkill
  4. Few-shot 示例：提升分类准确率
  5. Fallback 链：执行失败时自动切换候选 Skill
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from utils.logger import get_logger
from core.rag.llm_client import LLMClient
from core.router.skill_registry import SkillRegistry
from core.router.examples import format_few_shot_examples
from config.prompts import ROUTER_SYSTEM_PROMPT, format_router_prompt

log = get_logger(__name__)


@dataclass
class RoutingDecision:
    """路由决策结果。"""
    skill_name: str
    confidence: float
    reason: str
    fallback_skills: list[str]    # 备选 Skill 列表（按优先级）
    method: str = "llm"           # 决策方式: "keyword" | "llm" | "default"


# ── 关键词预过滤规则 ──────────────────────────────────────────────────
KEYWORD_RULES: list[dict] = [
    {
        "skill": "chitchat",
        "patterns": [
            r"^(你好|嗨|hi|hello|早上好|晚上好)",
            r"你(是谁|叫什么|能做什么)",
            r"(帮我)?写(一首诗|故事|小说)",
            r"今天天气",
        ],
    },
    {
        "skill": "summary",
        "patterns": [
            r"(总结|概括|归纳|梳理|摘要).{0,10}(内容|要点|全文|法规|条例)",
        ],
    },
    {
        "skill": "definition",
        "patterns": [
            r"(什么是|是什么|定义|解释|含义|意思).{0,20}(？|\?|$)",
            r"[A-Z]{2,}.*是什么",
        ],
    },
    {
        "skill": "compliance_check",
        "patterns": [
            r"(是否合规|合规性|是否满足|是否符合|需要满足)",
            r"(起飞重量|最大起飞|载荷).{0,10}\d+",
        ],
    },
    # ── 新增 Skills 关键词规则 ──
    {
        "skill": "calculation",
        "patterns": [
            r"(多少|几|限高|限速|限重|数值).{0,10}(米|千克|kg|km|公里|小时)",
            r"(最大|最小|上限|下限).{0,6}(起飞重量|飞行高度|速度|距离|载荷)",
            r"\d+.{0,6}(是否超过|是否满足|能否)",
        ],
    },
    {
        "skill": "comparison",
        "patterns": [
            r"(对比|比较|区别|差异|不同|异同).{0,10}(法规|条例|规定|标准|类别)",
            r"(和|与|跟).{0,15}(有什么|有何|哪些).{0,6}(区别|不同|差异)",
            r"(微型|轻型|小型|中型|大型).{0,6}(和|与|跟).{0,8}(微型|轻型|小型|中型|大型)",
            r"(相比|相较|相对于).{0,30}(差异|不同|区别|影响)",
            r"(主要差异|主要区别|核心差异|核心区别)",
            r"(有什么|有何|哪些).{0,12}(不同|区别|差异)",
            r"eVTOL.{0,30}(传统无人机|无人机).{0,30}(不同|区别|差异)",
            r"(传统无人机|无人机).{0,30}eVTOL.{0,30}(不同|区别|差异)",
            r"(风险对象|审定重点|运行环境|导航路径规划影响)",
            r"(法规明文要求|明文要求).{0,30}(工程影响|工程推导|技术影响)",
        ],
    },
    {
        "skill": "timeline",
        "patterns": [
            r"(发展历程|演变|沿革|时间线|历史)",
            r"(什么时候|何时|哪一年).{0,10}(颁布|生效|实施|修订|废止)",
            r"(从|自).{0,8}(年|月).{0,6}(以来|至今|到)",
        ],
    },
    {
        "skill": "export",
        "patterns": [
            r"(生成|撰写|出具|输出).{0,6}(报告|分析报告|评估报告|综合报告)",
            r"(汇总|整理|汇编).{0,6}(所有|全部|相关).{0,6}(法规|规定|要求)",
        ],
    },
]


class IntentRouter:
    """多层防线意图路由器。

    路由流程:
        1. 关键词预过滤 → 如命中，直接返回（confidence=0.9）
        2. LLM 结构化分类 → 输出 JSON
        3. 置信度检查 → 低于阈值则降级到默认 Skill
    """

    def __init__(
        self,
        llm_client: LLMClient,
        registry: SkillRegistry,
        confidence_threshold: float = 0.7,
    ) -> None:
        self.llm = llm_client
        self.registry = registry
        self.confidence_threshold = confidence_threshold

    def route(self, question: str, chat_history: list[dict] | None = None) -> RoutingDecision:
        """执行意图路由，返回 RoutingDecision。"""
        log.info(f"[IntentRouter] Routing question: {question[:60]}...")

        # ── 第 1 层：关键词预过滤 ──
        keyword_result = self._keyword_prefilter(question)
        if keyword_result:
            log.info(f"[IntentRouter] 关键词命中 → {keyword_result}")
            return RoutingDecision(
                skill_name=keyword_result,
                confidence=0.9,
                reason="关键词规则匹配",
                fallback_skills=self._get_fallback_chain(keyword_result),
                method="keyword",
            )

        # ── 第 2 层：LLM 结构化分类 ──
        try:
            decision = self._llm_classify(question, chat_history)
        except Exception as e:
            log.error(f"[IntentRouter] LLM 分类失败: {e}，降级到默认 Skill")
            default = self.registry.default_skill_name
            return RoutingDecision(
                skill_name=default,
                confidence=0.5,
                reason=f"LLM 分类异常: {e}",
                fallback_skills=[],
                method="default",
            )

        # ── 第 3 层：置信度检查 ──
        if decision.confidence < self.confidence_threshold:
            log.warning(
                f"[IntentRouter] 置信度 {decision.confidence:.2f} < {self.confidence_threshold}，"
                f"降级到默认 Skill"
            )
            default = self.registry.default_skill_name
            decision.fallback_skills = [decision.skill_name] + decision.fallback_skills
            decision.skill_name = default
            decision.reason += f"（置信度不足，降级为 {default}）"
            decision.method = "default"

        # ── 第 4 层：验证 Skill 存在性 ──
        if decision.skill_name not in self.registry:
            log.warning(f"[IntentRouter] Skill '{decision.skill_name}' 未注册，降级到默认")
            decision.skill_name = self.registry.default_skill_name

        log.info(
            f"[IntentRouter] 路由结果: skill={decision.skill_name}, "
            f"confidence={decision.confidence:.2f}, method={decision.method}"
        )
        return decision

    # ── 关键词预过滤 ──────────────────────────────────────────────────
    def _keyword_prefilter(self, question: str) -> Optional[str]:
        """基于正则规则快速预判。命中返回 skill_name，未命中返回 None。"""
        for rule in KEYWORD_RULES:
            for pattern in rule["patterns"]:
                if re.search(pattern, question, re.IGNORECASE):
                    return rule["skill"]
        return None

    # ── LLM 分类 ─────────────────────────────────────────────────────
    def _llm_classify(self, question: str, chat_history: list[dict] | None) -> RoutingDecision:
        """调用 LLM 进行结构化意图分类。"""
        skills_info = self.registry.list_skills()
        few_shot = format_few_shot_examples()

        prompt = format_router_prompt(
            question=question,
            skills=json.dumps(skills_info, ensure_ascii=False, indent=2),
            few_shot_examples=few_shot,
        )

        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        raw = self.llm.chat(messages, stream=False)
        parsed = self._parse_classification(raw)
        return parsed

    def _parse_classification(self, raw_text: str) -> RoutingDecision:
        """解析 LLM 返回的 JSON 分类结果。"""
        # 尝试从文本中提取 JSON
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                skill_name = data.get("skill", self.registry.default_skill_name)
                confidence = float(data.get("confidence", 0.5))
                reason = data.get("reason", "LLM 分类")

                # 约束 confidence 到 [0, 1]
                confidence = max(0.0, min(1.0, confidence))

                return RoutingDecision(
                    skill_name=skill_name,
                    confidence=confidence,
                    reason=reason,
                    fallback_skills=self._get_fallback_chain(skill_name),
                    method="llm",
                )
            except (json.JSONDecodeError, ValueError) as e:
                log.warning(f"[IntentRouter] JSON 解析失败: {e}")

        # 解析失败，返回默认
        return RoutingDecision(
            skill_name=self.registry.default_skill_name,
            confidence=0.5,
            reason="LLM 返回格式异常，降级到默认",
            fallback_skills=[],
            method="default",
        )

    # ── Fallback 链 ───────────────────────────────────────────────────
    def _get_fallback_chain(self, primary_skill: str) -> list[str]:
        """根据主 Skill 生成备选 Skill 链。"""
        all_names = self.registry.list_names()
        # 优先将 rag 作为 fallback（除非它本身就是 primary）
        fallback = []
        if primary_skill != "rag" and "rag" in all_names:
            fallback.append("rag")
        for name in all_names:
            if name != primary_skill and name not in fallback and name != "chitchat":
                fallback.append(name)
        return fallback
