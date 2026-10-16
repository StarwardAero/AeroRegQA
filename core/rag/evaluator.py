"""RAG 系统评估指标"""
import re
import time
from dataclasses import dataclass, field
from typing import Optional, Any
from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class EvaluationResult:
    """单次评估结果"""
    question: str
    answer: str
    sources: list[str]
    response_time: float          # 响应时间（秒）
    citation_rate: float          # 引用率：回答中引用的来源数 / 检索到的来源数
    retrieval_count: int          # 检索到的文档数
    iterations: int               # RAG 迭代次数
    judge_score: Optional[float] = None  # 裁判评分（如果有）


@dataclass
class BatchEvaluationReport:
    """批量评估报告"""
    total_questions: int
    avg_response_time: float
    avg_citation_rate: float
    avg_iterations: float
    avg_judge_score: Optional[float]
    results: list[EvaluationResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "total_questions": self.total_questions,
            "avg_response_time": round(self.avg_response_time, 2),
            "avg_citation_rate": round(self.avg_citation_rate, 2),
            "avg_iterations": round(self.avg_iterations, 2),
            "avg_judge_score": round(self.avg_judge_score, 2) if self.avg_judge_score else None,
            "results": [
                {
                    "question": r.question,
                    "answer_preview": r.answer[:200] + "..." if len(r.answer) > 200 else r.answer,
                    "response_time": round(r.response_time, 2),
                    "citation_rate": round(r.citation_rate, 2),
                    "retrieval_count": r.retrieval_count,
                    "iterations": r.iterations,
                    "judge_score": r.judge_score,
                }
                for r in self.results
            ],
        }


class RAGEvaluator:
    """RAG 系统评估器"""

    def __init__(self, agent: Any, retriever: Any):
        """
        Args:
            agent: AgenticRAG 实例
            retriever: HybridRetriever 实例
        """
        self.agent = agent
        self.retriever = retriever

    def evaluate_single(self, question: str, chat_history: list[dict] = None) -> EvaluationResult:
        """评估单个问题"""
        import threading

        chat_history = chat_history or []
        stop_event = threading.Event()

        # 记录步骤信息
        steps_info: list[Any] = []

        def on_step(step: Any) -> None:
            steps_info.append(step)

        # 执行问答并计时
        start_time = time.time()
        response = self.agent.run(
            question=question,
            chat_history=chat_history,
            stop_event=stop_event,
            on_step=on_step,
        )
        elapsed = time.time() - start_time

        # 计算引用率
        sources = response.sources if hasattr(response, "sources") else []
        # 简单统计回答中出现的 [N] 引用标记数量
        citations_in_answer = len(re.findall(r"\[\d+\]", response.final_answer or ""))
        retrieval_count = len(sources) if sources else 0
        citation_rate = citations_in_answer / max(retrieval_count, 1)

        # 获取裁判评分（从steps中提取）
        judge_score = None
        for step in steps_info:
            if hasattr(step, "step_type") and "judge" in str(getattr(step, "step_type", "")).lower():
                meta = getattr(step, "metadata", {}) or {}
                judge_score = meta.get("score")

        return EvaluationResult(
            question=question,
            answer=response.final_answer or "",
            sources=[s for s in (sources or [])],
            response_time=elapsed,
            citation_rate=min(citation_rate, 1.0),
            retrieval_count=retrieval_count,
            iterations=response.total_iterations if hasattr(response, "total_iterations") else 1,
            judge_score=judge_score,
        )

    def evaluate_batch(self, questions: list[str]) -> BatchEvaluationReport:
        """批量评估多个问题"""
        results: list[EvaluationResult] = []
        for q in questions:
            try:
                result = self.evaluate_single(q)
                results.append(result)
                log.info(f"Evaluated: '{q[:50]}...' -> {result.response_time:.1f}s")
            except Exception as e:
                log.error(f"Evaluation failed for '{q}': {e}")

        if not results:
            return BatchEvaluationReport(
                total_questions=len(questions),
                avg_response_time=0,
                avg_citation_rate=0,
                avg_iterations=0,
                avg_judge_score=None,
                results=[],
            )

        judge_scores = [r.judge_score for r in results if r.judge_score is not None]

        return BatchEvaluationReport(
            total_questions=len(questions),
            avg_response_time=sum(r.response_time for r in results) / len(results),
            avg_citation_rate=sum(r.citation_rate for r in results) / len(results),
            avg_iterations=sum(r.iterations for r in results) / len(results),
            avg_judge_score=sum(judge_scores) / len(judge_scores) if judge_scores else None,
            results=results,
        )
