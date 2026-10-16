import sys
from pathlib import Path
import streamlit as st

# 将项目根目录添加到 sys.path，解决模块导入问题
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ui.state import AppState
from ui.styles import inject_custom_css
from config.settings import settings
from utils.logger import get_logger

# 核心模块
from core.vectorstore.embedder import EmbeddingService
from core.vectorstore.chroma_store import ChromaStore
from core.vectorstore.retriever import HybridRetriever
from core.vectorstore.reranker import Reranker
from core.rag.llm_client import LLMClient
from core.rag.judge import ResponseJudge
from core.rag.query_rewriter import QueryRewriter
from core.rag.agent import AgenticRAG
from core.rag.citation_checker import CitationChecker
from core.rag.conflict_detector import ConflictDetector
from core.conversation.storage import ConversationStorage
from core.conversation.title_generator import TitleGenerator
from core.conversation.manager import ConversationManager

# Skills & Router
from core.skills.rag_skill import RAGSkill
from core.skills.summary_skill import SummarySkill
from core.skills.definition_skill import DefinitionSkill
from core.skills.compliance_check_skill import ComplianceCheckSkill
from core.skills.chitchat_skill import ChitchatSkill
from core.skills.comparison_skill import ComparisonSkill
from core.router.skill_registry import SkillRegistry
from core.router.intent_router import IntentRouter

# Database
from core.database.redis_client import RedisClient
from core.database.models import MySQLClient

# UI 组件
from ui.components import sidebar, chat_area

log = get_logger(__name__)

@st.cache_resource
def get_services() -> dict:
    """初始化并缓存所有后端服务单例（v2 — Skills + Router + DB）"""
    log.info("Initializing background services (v2)...")

    # 1. 向量数据库相关
    embedder = EmbeddingService(
        model_name=settings.EMBEDDING_MODEL_NAME,
        api_key=settings.EMBEDDING_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL
    )
    chroma_store = ChromaStore(persist_dir=settings.CHROMA_DIR, embedding_service=embedder, seed_path=settings.KNOWLEDGE_SEED_PATH)
    reranker = None
    if settings.USE_RERANKER:
        reranker = Reranker(
            api_key=settings.EMBEDDING_API_KEY,
            base_url=settings.EMBEDDING_BASE_URL,
            model_name=settings.RERANKER_MODEL_NAME,
        )
    retriever = HybridRetriever(chroma_store, reranker=reranker)

    # 2. LLM 客户端
    main_llm = LLMClient.create_from_settings("main")
    judge_llm = LLMClient.create_from_settings("judge")
    lite_llm = LLMClient.create_from_settings("lite")
    router_llm = LLMClient(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model_name=settings.LLM_ROUTER_MODEL_NAME,
        temperature=0.1,
        max_tokens=256,
    )

    # 3. Agent 组件
    citation_checker = CitationChecker()
    judge = ResponseJudge(llm_client=judge_llm, threshold=settings.RAG_JUDGE_THRESHOLD)
    rewriter = QueryRewriter(llm_client=lite_llm)
    agent = AgenticRAG(
        retriever=retriever,
        main_llm=main_llm,
        judge_llm=judge_llm,
        query_rewriter=rewriter,
        judge=judge,
        citation_checker=citation_checker,
        max_iterations=settings.RAG_MAX_ITERATIONS
    )

    # 4. 幻觉抑制组件
    conflict_detector = ConflictDetector(llm_client=lite_llm)

    # 5. Skills 注册
    registry = SkillRegistry()
    registry.register(RAGSkill(agent=agent))
    registry.register(SummarySkill(retriever=retriever, llm=main_llm))
    registry.register(DefinitionSkill(retriever=retriever, llm=main_llm))
    registry.register(ComplianceCheckSkill(retriever=retriever, llm=main_llm))
    registry.register(ComparisonSkill(llm_client=main_llm, retriever=retriever))
    registry.register(ChitchatSkill())

    # 6. Intent Router
    intent_router = IntentRouter(
        llm_client=router_llm,
        registry=registry,
        confidence_threshold=settings.ROUTER_CONFIDENCE_THRESHOLD,
    )

    # 7. 对话管理器
    storage = ConversationStorage(settings.CONVERSATION_DIR)
    title_gen = TitleGenerator(llm_client=lite_llm)
    conversation_manager = ConversationManager(storage, title_gen)

    # 8. Redis 缓存
    redis_client = RedisClient(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
    )

    # 9. MySQL / SQLite
    mysql_client = MySQLClient(database_url=settings.DATABASE_URL)
    mysql_client.create_tables()

    return {
        "chroma_store": chroma_store,
        "reranker": reranker,
        "agent": agent,
        "conversation_manager": conversation_manager,
        "skill_registry": registry,
        "intent_router": intent_router,
        "citation_checker": citation_checker,
        "conflict_detector": conflict_detector,
        "redis_client": redis_client,
        "mysql_client": mysql_client,
    }

def main():
    # 1. 页面基础配置
    st.set_page_config(
        page_title="低空适航与规章问答 AI",
        page_icon="🚁",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 2. 注入自定义 CSS
    inject_custom_css()

    # 3. 初始化全局状态
    AppState.initialize()

    # 4. 获取后台服务
    try:
        with st.spinner("正在加载规章知识库，首次启动需要片刻…"):
            services = get_services()
    except Exception as e:
        st.error(f"⚠️ 初始化后台服务失败。请检查 .env 配置是否正确。错误信息：{e}")
        st.stop()

    conversation_manager = services["conversation_manager"]
    agent = services["agent"]

    # 5. 渲染侧边栏
    with st.sidebar:
        sidebar.render(conversation_manager, services)

    # 6. 渲染主聊天区域
    chat_area.render(conversation_manager, agent, services)

if __name__ == "__main__":
    main()
