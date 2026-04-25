import time
from dataclasses import dataclass, field
from typing import Callable, Any
from utils.logger import get_logger
from .llm_client import LLMClient
from .judge import ResponseJudge
from .query_rewriter import QueryRewriter
from core.vectorstore.retriever import HybridRetriever
from config.prompts import RAG_SYSTEM_PROMPT, format_rag_prompt

log = get_logger(__name__)

@dataclass
class AgentStep:
    step_type: str
    input_data: str
    output_data: str
    duration_ms: int
    metadata: dict = field(default_factory=dict)

@dataclass
class AgentResponse:
    final_answer: str
    steps: list[AgentStep]
    total_iterations: int
    was_interrupted: bool
    sources: list[str]

class AgenticRAG:
    def __init__(self, retriever: HybridRetriever, main_llm: LLMClient, judge_llm: LLMClient, query_rewriter: QueryRewriter, judge: ResponseJudge, max_iterations: int = 3):
        self.retriever = retriever
        self.main_llm = main_llm
        self.judge = judge
        self.query_rewriter = query_rewriter
        self.max_iterations = max_iterations

    def run(self, question: str, chat_history: list[dict], stop_event: Any, on_step: Callable = None, on_token: Callable = None) -> AgentResponse:
        """核心控制循环：检索 -> 草稿 -> 裁判 -> 重写/流式输出"""
        start_time = time.time()
        iteration = 0
        steps = []
        was_interrupted = False
        sources = []

        # 1. 意图重写
        step_start = time.time()
        rewritten_query = self.query_rewriter.rewrite(question, chat_history)
        steps.append(AgentStep("rewrite", question, rewritten_query, int((time.time() - step_start)*1000)))
        if on_step: on_step(steps[-1])

        # 构建历史字符串用于最终 Prompt
        history_str = ""
        for msg in chat_history[-6:]:
            role = "用户" if msg.get("role") == "user" else "助手"
            history_str += f"【{role}】: {msg.get('content')}\n"

        is_final_round = False
        final_answer = ""
        context = ""

        # 控制循环
        while iteration < self.max_iterations and not (stop_event and stop_event.is_set()):
            iteration += 1
            log.info(f"Starting iteration {iteration}/{self.max_iterations}")

            # 2. 检索阶段
            step_start = time.time()
            chunks = self.retriever.retrieve(rewritten_query, top_k=5)
            context = self.retriever.format_context(chunks)
            sources = list(set([c.metadata.get("source_file", "Unknown") for c in chunks]))
            
            steps.append(AgentStep("retrieve", rewritten_query, f"Retrieved {len(chunks)} chunks.", int((time.time() - step_start)*1000), {"sources": sources}))
            if on_step: on_step(steps[-1])

            # 组装完整的对话 Messages
            prompt = format_rag_prompt(context, question, history_str)
            messages = [
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]

            # 检查是否最后一次循环
            is_final_round = (iteration == self.max_iterations)

            if not is_final_round:
                # 非流式生成草稿
                step_start = time.time()
                draft_answer = self.main_llm.chat(messages, stream=False)
                steps.append(AgentStep("generate", prompt, draft_answer, int((time.time() - step_start)*1000)))
                if on_step: on_step(steps[-1])

                # 裁判评估
                step_start = time.time()
                judge_result = self.judge.evaluate(question, context, draft_answer)
                steps.append(AgentStep("judge", draft_answer, f"Score: {judge_result.score}. Acceptable: {judge_result.is_acceptable}", int((time.time() - step_start)*1000)))
                if on_step: on_step(steps[-1])

                if judge_result.is_acceptable:
                    log.info("Draft accepted by judge. Early stopping and generating stream.")
                    is_final_round = True
                    # 标记后会在下方 if is_final_round 块里进行最终流式输出
                else:
                    log.info("Draft rejected. Refining query based on suggestions.")
                    # 将裁判的建议拼接进重写请求
                    suggestions_str = " ".join(judge_result.suggestions)
                    rewritten_query = self.query_rewriter.rewrite(f"{question} (提示: {suggestions_str})", chat_history)
                    steps.append(AgentStep("rewrite", suggestions_str, rewritten_query, int((time.time() - step_start)*1000)))
                    if on_step: on_step(steps[-1])
                    continue # 进入下一轮循环

            if is_final_round:
                # 流式输出最终回答
                log.info(f"Generating final streaming answer at iteration {iteration}")
                step_start = time.time()
                
                final_answer = self.main_llm.chat_with_callback(messages, on_token, stop_event)
                
                was_interrupted = stop_event and stop_event.is_set()
                steps.append(AgentStep("generate_final", prompt, final_answer, int((time.time() - step_start)*1000)))
                if on_step: on_step(steps[-1])
                break # 结束循环

        return AgentResponse(
            final_answer=final_answer,
            steps=steps,
            total_iterations=iteration,
            was_interrupted=was_interrupted,
            sources=sources
        )
