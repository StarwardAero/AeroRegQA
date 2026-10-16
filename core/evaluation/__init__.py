"""LLM 效果评测框架 — 对 RAG 问答系统进行多维度自动化评测。

提供：
- EvaluationMetrics: 评测指标（忠实度、完整性、引用准确率、无幻觉率）
- RAGEvaluator: 自动化评测 RAG 系统的端到端质量
- BatchEvaluator: 批量测试集评测 + 统计分析
- ModelComparator: 多模型对比评测

评测维度（RAGAS 风格）：
1. Faithfulness（忠实度）：回答是否忠于检索到的上下文
2. Relevance（相关性）：回答是否切题
3. Citation Accuracy（引用准确率）：引用编号是否正确对应
4. Hallucination Rate（幻觉率）：是否编造了不在上下文中的信息
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EvaluationResult:
    """单条评测结果。"""
    question: str
    answer: str
    context: str = ""
    # 多维度分数 (0-1)
    faithfulness: float = 0.0
    relevance: float = 0.0
    citation_accuracy: float = 0.0
    hallucination_free: float = 0.0
    recall: float = 0.0               # 检索召回率：检索到的相关文档覆盖率
    # 聚合分数
    overall_score: float = 0.0
    # 元数据
    model_name: str = ""
    latency_ms: int = 0
    token_count: int = 0
    skill_name: str = ""
    details: dict = field(default_factory=dict)


class RAGEvaluator:
    """RAG 系统效果评测器。

    使用 LLM-as-Judge 模式进行多维度评估。
    """

    def __init__(self, judge_llm) -> None:
        self.judge_llm = judge_llm

    def evaluate(
        self,
        question: str,
        answer: str,
        context: str = "",
        reference_answer: str = "",
    ) -> EvaluationResult:
        """对单条 QA 进行多维度评测。"""
        start = time.time()

        result = EvaluationResult(
            question=question,
            answer=answer,
            context=context,
        )

        # LLM-as-Judge 多维度评测
        eval_prompt = self._build_eval_prompt(question, answer, context, reference_answer)
        messages = [
            {"role": "system", "content": (
                "你是一个严格的 RAG 系统质量评估专家。"
                "请对给定的问答结果进行多维度评分。"
                "输出严格 JSON 格式。"
            )},
            {"role": "user", "content": eval_prompt},
        ]

        try:
            response = self.judge_llm.chat(
                messages=messages,
                response_format={"type": "json_object"},
            )
            # chat() 返回纯文本字符串；部分模型即使指定 JSON 也可能包裹说明文本
            content = response if isinstance(response, str) else ""
            content = self._extract_json(content)
            if content:
                scores = json.loads(content)
                result.faithfulness = scores.get("faithfulness", 0)
                result.relevance = scores.get("relevance", 0)
                result.citation_accuracy = scores.get("citation_accuracy", 0)
                result.hallucination_free = scores.get("hallucination_free", 0)
                result.recall = scores.get("recall", 0)
                result.details = scores.get("details", {})
                # 加权聚合分（加入召回率权重）
                result.overall_score = (
                    result.faithfulness * 0.25
                    + result.relevance * 0.20
                    + result.citation_accuracy * 0.15
                    + result.hallucination_free * 0.20
                    + result.recall * 0.20
                )
        except Exception as exc:
            logger.warning(f"[Evaluator] 评测失败: {exc}")

        result.latency_ms = int((time.time() - start) * 1000)
        return result

    @staticmethod
    def _extract_json(text: str) -> str:
        """从模型输出中提取 JSON 对象，降低评测解析失败率。"""
        if not text:
            return ""
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        if text.startswith("{") and text.endswith("}"):
            return text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return match.group(0) if match else text

    def _build_eval_prompt(
        self,
        question: str,
        answer: str,
        context: str,
        reference_answer: str,
    ) -> str:
        ref_section = f"\n参考答案：\n{reference_answer}\n" if reference_answer else ""
        return f"""请评估以下 RAG 问答的质量：

问题：{question}

检索上下文：
{context[:8000]}

系统回答：
{answer[:4000]}
{ref_section}
请从以下四个维度评分（0-1，精确到小数点后两位）：

1. **faithfulness**（忠实度）：回答内容是否完全基于检索上下文，不包含上下文之外的信息？
2. **relevance**（相关性）：回答是否直接回应了用户的问题？
3. **citation_accuracy**（引用准确率）：引用编号 [n] 是否正确对应上下文中的片段？
4. **hallucination_free**（无幻觉率）：回答中是否没有编造的信息？1.0=完全无幻觉
5. **recall**（检索召回率）：检索到的上下文是否覆盖了回答问题所需的全部关键信息？1.0=完全覆盖

输出格式：
{{
    "faithfulness": 0.85,
    "relevance": 0.90,
    "citation_accuracy": 0.80,
    "hallucination_free": 0.95,
    "recall": 0.85,
    "details": {{
        "faithfulness_issues": ["具体问题"],
        "hallucination_examples": ["具体幻觉"],
        "missing_citations": ["缺失引用"],
        "missing_information": ["未检索到的关键信息"],
        "summary": "总结"
    }}
}}"""


class BatchEvaluator:
    """批量评测器 — 对测试集进行批量评测并统计。"""

    def __init__(self, evaluator: RAGEvaluator) -> None:
        self.evaluator = evaluator

    def evaluate_batch(
        self,
        test_cases: list[dict],
        on_progress: callable = None,
    ) -> dict:
        """批量评测。

        Args:
            test_cases: [{"question": str, "answer": str, "context": str, "reference": str}, ...]

        Returns:
            {
                "results": [EvaluationResult, ...],
                "summary": {
                    "avg_faithfulness": float,
                    "avg_relevance": float,
                    "avg_citation_accuracy": float,
                    "avg_hallucination_free": float,
                    "avg_overall": float,
                    "total": int,
                }
            }
        """
        results = []
        total = len(test_cases)

        for idx, case in enumerate(test_cases):
            logger.info(f"[Judge] 评测 {idx+1}/{total}: {case.get('question', '')[:30]}...")
            try:
                result = self.evaluator.evaluate(
                    question=case.get("question", ""),
                    answer=case.get("answer", ""),
                    context=case.get("context", ""),
                    reference_answer=case.get("reference", ""),
                )
            except Exception as exc:
                logger.warning(f"[Judge] 评测 {idx+1} 失败: {exc}, 使用零分")
                result = EvaluationResult(
                    question=case.get("question", ""),
                    answer=case.get("answer", ""),
                )
            result.model_name = case.get("model_name", "")
            result.skill_name = case.get("skill_name", "")
            results.append(result)
            if on_progress:
                try:
                    on_progress(idx + 1, total, results)
                except TypeError:
                    on_progress(idx + 1, total)

        # 统计分析
        n = max(len(results), 1)
        summary = {
            "avg_faithfulness": sum(r.faithfulness for r in results) / n,
            "avg_relevance": sum(r.relevance for r in results) / n,
            "avg_citation_accuracy": sum(r.citation_accuracy for r in results) / n,
            "avg_hallucination_free": sum(r.hallucination_free for r in results) / n,
            "avg_recall": sum(r.recall for r in results) / n,
            "avg_overall": sum(r.overall_score for r in results) / n,
            "total": len(results),
        }

        return {"results": results, "summary": summary}


class ModelComparator:
    """多模型对比评测器。

    对同一组测试问题，使用不同 LLM 模型生成回答并评测，
    方便进行模型选型决策。
    """

    def __init__(self, evaluator: RAGEvaluator) -> None:
        self.evaluator = evaluator

    def compare(
        self,
        test_questions: list[str],
        model_answers: dict[str, list[str]],
        contexts: list[str] | None = None,
        references: list[str] | None = None,
    ) -> dict:
        """对比多模型在同一测试集上的表现。

        Args:
            test_questions: 测试问题列表
            model_answers: {model_name: [答案列表]}
            contexts: 对应的检索上下文列表
            references: 参考答案列表

        Returns:
            {
                "model_scores": {model_name: {avg scores}},
                "ranking": [model_name sorted by overall score],
                "details": {model_name: [EvaluationResult]}
            }
        """
        model_scores = {}
        details = {}

        for model_name, answers in model_answers.items():
            model_results = []
            for i, (q, a) in enumerate(zip(test_questions, answers)):
                ctx = contexts[i] if contexts and i < len(contexts) else ""
                ref = references[i] if references and i < len(references) else ""
                result = self.evaluator.evaluate(q, a, ctx, ref)
                result.model_name = model_name
                model_results.append(result)

            n = max(len(model_results), 1)
            model_scores[model_name] = {
                "avg_faithfulness": round(sum(r.faithfulness for r in model_results) / n, 3),
                "avg_relevance": round(sum(r.relevance for r in model_results) / n, 3),
                "avg_citation_accuracy": round(sum(r.citation_accuracy for r in model_results) / n, 3),
                "avg_hallucination_free": round(sum(r.hallucination_free for r in model_results) / n, 3),
                "avg_recall": round(sum(r.recall for r in model_results) / n, 3),
                "avg_overall": round(sum(r.overall_score for r in model_results) / n, 3),
                "avg_latency_ms": round(sum(r.latency_ms for r in model_results) / n, 1),
            }
            details[model_name] = model_results

        # 排名
        ranking = sorted(
            model_scores.keys(),
            key=lambda m: model_scores[m]["avg_overall"],
            reverse=True,
        )

        return {
            "model_scores": model_scores,
            "ranking": ranking,
            "details": details,
        }
