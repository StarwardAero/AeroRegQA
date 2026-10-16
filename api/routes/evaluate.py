"""评估接口路由"""
from fastapi import APIRouter
from api.schemas import EvaluateRequest, EvaluateResponse, EvaluateResultItem
from api.dependencies import get_agent, get_retriever

router = APIRouter(prefix="/api", tags=["evaluate"])


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_questions(request: EvaluateRequest):
    """批量评估RAG系统"""
    import asyncio
    from core.rag.evaluator import RAGEvaluator

    agent = get_agent()
    retriever = get_retriever()
    evaluator = RAGEvaluator(agent, retriever)

    # 在线程中运行同步评估
    report = await asyncio.to_thread(evaluator.evaluate_batch, request.questions)

    raw_results = report.to_dict()["results"]
    result_items = [EvaluateResultItem(**r) for r in raw_results]

    return EvaluateResponse(
        total_questions=report.total_questions,
        avg_response_time=report.avg_response_time,
        avg_citation_rate=report.avg_citation_rate,
        avg_iterations=report.avg_iterations,
        avg_judge_score=report.avg_judge_score,
        results=result_items,
    )
