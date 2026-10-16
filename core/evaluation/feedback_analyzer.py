"""用户反馈分析器 — 分析用户点踩的 case，用 LLM 找出共性问题。

功能：
  1. 读取 user_feedbacks 表中的差评记录
  2. 对差评 case 做聚类分析（检索问题 / 幻觉 / 回答不完整 / 路由错误）
  3. 用 LLM 生成改进建议报告

使用方式：
  from core.evaluation.feedback_analyzer import FeedbackAnalyzer
  analyzer = FeedbackAnalyzer(db_client, llm_client)
  report = analyzer.analyze()
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from utils.logger import get_logger

if TYPE_CHECKING:
    from core.database.models import MySQLClient
    from core.rag.llm_client import LLMClient

log = get_logger(__name__)


class FeedbackAnalyzer:
    """用户反馈分析器。

    分析用户差评，识别系统薄弱环节，生成改进建议。
    """

    # 差评原因分类
    ISSUE_CATEGORIES = [
        "检索不到相关文档",
        "回答存在幻觉/编造",
        "回答不完整/遗漏信息",
        "路由错误（分给了不合适的 Skill）",
        "上下文冲突/新旧法规混淆",
        "响应太慢",
        "格式不符合预期",
        "其他",
    ]

    def __init__(self, db_client: MySQLClient, llm_client: LLMClient) -> None:
        self.db = db_client
        self.llm = llm_client

    def analyze(self, limit: int = 50) -> dict:
        """分析最近的用户差评，返回分析报告。

        Returns:
            {
                "total_feedbacks": int,
                "positive_count": int,
                "negative_count": int,
                "positive_rate": float,
                "issues": [{"category": str, "count": int}, ...],
                "recommendations": [str, ...],
                "top_negative_queries": [str, ...],
            }
        """
        # 读取反馈数据
        feedbacks = self._load_feedbacks(limit)
        if not feedbacks:
            return self._empty_report()

        positive = [f for f in feedbacks if f.get("rating", 0) >= 4]
        negative = [f for f in feedbacks if f.get("rating", 0) <= 2]

        total = len(feedbacks)
        positive_rate = len(positive) / max(total, 1)

        # 用 LLM 分析差评共性
        issues = []
        recommendations = []
        top_negative_queries = []

        if negative:
            # 尝试用 LLM 分析
            try:
                analysis = self._llm_analyze_negative(negative[:20])
                issues = analysis.get("issues", [])
                recommendations = analysis.get("recommendations", [])
            except Exception as e:
                log.warning(f"LLM 分析差评失败: {e}")

            # 提取差评中的问题
            top_negative_queries = [
                f.get("comment", "无评论")[:100]
                for f in negative[:10]
            ]

        # 如果没有 LLM 分析结果，用规则分类
        if not issues:
            issues = self._rule_based_classify(negative)

        return {
            "total_feedbacks": total,
            "positive_count": len(positive),
            "negative_count": len(negative),
            "positive_rate": round(positive_rate, 3),
            "issues": issues,
            "recommendations": recommendations or [
                "建议对差评 case 逐一排查检索质量和幻觉情况",
                "关注高频差评问题类型，优先修复",
            ],
            "top_negative_queries": top_negative_queries,
        }

    def _load_feedbacks(self, limit: int) -> list[dict]:
        """从数据库加载反馈记录。"""
        try:
            with self.db.get_session() as session:
                from core.database.models import UserFeedback
                records = (
                    session.query(UserFeedback)
                    .order_by(UserFeedback.timestamp.desc())
                    .limit(limit)
                    .all()
                )
                return [
                    {
                        "rating": r.rating,
                        "comment": r.comment or "",
                        "conversation_id": r.conversation_id,
                        "timestamp": r.timestamp.isoformat() if r.timestamp else "",
                    }
                    for r in records
                ]
        except Exception as e:
            log.warning(f"加载反馈数据失败: {e}")
            return []

    def _llm_analyze_negative(self, negative_feedbacks: list[dict]) -> dict:
        """用 LLM 分析差评的共性问题和改进建议。"""
        feedbacks_text = "\n".join(
            f"- 评分: {f.get('rating')}, 评论: {f.get('comment', '无')[:200]}"
            for f in negative_feedbacks[:20]
        )

        prompt = f"""你是 RAG 系统质量分析师。以下是用户对系统回答的差评：

{feedbacks_text}

请分析这些差评的共性问题和改进建议。输出严格 JSON 格式：

{{
    "issues": [
        {{"category": "问题类别", "count": 出现次数, "description": "具体描述"}},
        ...
    ],
    "recommendations": [
        "改进建议1",
        "改进建议2",
        ...
    ]
}}

注意：
- category 从以下选项中选择：检索不到相关文档、回答存在幻觉/编造、回答不完整/遗漏信息、路由错误、上下文冲突、响应太慢、格式不符合预期、其他
- count 是估算的出现次数
- recommendations 是具体的、可操作的改进建议"""

        messages = [
            {"role": "system", "content": "你是 RAG 系统质量分析师，输出严格 JSON。"},
            {"role": "user", "content": prompt},
        ]

        import json
        import re

        response = self.llm.chat(messages, stream=False)
        json_match = re.search(r'\{.*\}', str(response), re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"issues": [], "recommendations": []}

    def _rule_based_classify(self, negative: list[dict]) -> list[dict]:
        """基于规则的差评分类（LLM 不可用时的降级方案）。"""
        category_count: Counter = Counter()
        for f in negative:
            comment = (f.get("comment") or "").lower()
            if any(kw in comment for kw in ["找不到", "没搜到", "检索", "没有相关"]):
                category_count["检索不到相关文档"] += 1
            elif any(kw in comment for kw in ["编造", "不存在", "幻觉", "假的", "不真实"]):
                category_count["回答存在幻觉/编造"] += 1
            elif any(kw in comment for kw in ["不完整", "遗漏", "缺少", "不全"]):
                category_count["回答不完整/遗漏信息"] += 1
            elif any(kw in comment for kw in ["慢", "等太久", "超时"]):
                category_count["响应太慢"] += 1
            elif any(kw in comment for kw in ["格式", "排版", "乱"]):
                category_count["格式不符合预期"] += 1
            else:
                category_count["其他"] += 1

        return [
            {"category": cat, "count": cnt, "description": f"用户反馈提及 {cat} 相关问题"}
            for cat, cnt in category_count.most_common()
        ]

    @staticmethod
    def _empty_report() -> dict:
        """返回空报告。"""
        return {
            "total_feedbacks": 0,
            "positive_count": 0,
            "negative_count": 0,
            "positive_rate": 0.0,
            "issues": [],
            "recommendations": ["暂无用户反馈数据，建议先收集用户反馈"],
            "top_negative_queries": [],
        }
