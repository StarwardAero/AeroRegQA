import threading
from config.settings import settings
from utils.logger import get_logger
from core.vectorstore.embedder import EmbeddingService
from core.vectorstore.chroma_store import ChromaStore
from core.vectorstore.retriever import HybridRetriever
from core.rag.llm_client import LLMClient
from core.rag.judge import ResponseJudge
from core.rag.query_rewriter import QueryRewriter
from core.rag.agent import AgenticRAG

log = get_logger("test_phase2")

def main():
    log.info("Testing Phase 2 (RAG Engine)...")
    
    # 1. 初始化假数据的检索器 (复用之前建立的 ChromaDB 库)
    embedder = EmbeddingService(
        model_name=settings.EMBEDDING_MODEL_NAME,
        api_key=settings.EMBEDDING_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL
    )
    chroma_store = ChromaStore(persist_dir=settings.CHROMA_DIR, embedding_service=embedder)
    retriever = HybridRetriever(chroma_store)
    
    # 2. 初始化 LLM 和组件
    main_llm = LLMClient.create_from_settings("main")
    judge_llm = LLMClient.create_from_settings("judge")
    lite_llm = LLMClient.create_from_settings("lite")
    
    judge = ResponseJudge(llm_client=judge_llm, threshold=settings.RAG_JUDGE_THRESHOLD)
    rewriter = QueryRewriter(llm_client=lite_llm)
    
    agent = AgenticRAG(
        retriever=retriever,
        main_llm=main_llm,
        judge_llm=judge_llm,
        query_rewriter=rewriter,
        judge=judge,
        max_iterations=settings.RAG_MAX_ITERATIONS
    )
    
    # 3. 准备测试数据
    question = "什么是 MAPF algorithms？详细解释一下。"
    chat_history = [{"role": "user", "content": "你好，我想了解路径规划。"}]
    stop_event = threading.Event()
    
    # 模拟流式输出回调和步骤回调
    def on_step(step):
        log.info(f"[Agent Step] {step.step_type}: {step.output_data[:50]}...")
        
    def on_token(token):
        print(token, end="", flush=True)

    # 4. 运行 Agent
    print("\n--- Start Agent Run ---")
    response = agent.run(question, chat_history, stop_event, on_step, on_token)
    print("\n--- End Agent Run ---")
    
    # 5. 验证结果
    log.info(f"Total Iterations: {response.total_iterations}")
    log.info(f"Was Interrupted: {response.was_interrupted}")
    log.info(f"Sources: {response.sources}")
    
    print(f"\nFinal Answer Length: {len(response.final_answer)}")
    log.info("Phase 2 Test Completed successfully!")

if __name__ == "__main__":
    main()