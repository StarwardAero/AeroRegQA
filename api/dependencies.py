"""依赖注入：创建并缓存服务单例（含 Skills + Router + Database 层）"""
from functools import lru_cache
from utils.logger import get_logger
from config.settings import settings
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
from core.chunker.semantic_chunker import SemanticChunker
from core.parser.parser_factory import ParserFactory

# Skills & Router
from core.skills.rag_skill import RAGSkill
from core.skills.summary_skill import SummarySkill
from core.skills.definition_skill import DefinitionSkill
from core.skills.compliance_check_skill import ComplianceCheckSkill
from core.skills.chitchat_skill import ChitchatSkill
from core.skills.calculation_skill import CalculationSkill
from core.skills.comparison_skill import ComparisonSkill
from core.skills.timeline_skill import TimelineSkill
from core.skills.export_skill import ExportSkill
from core.router.skill_registry import SkillRegistry
from core.router.intent_router import IntentRouter

# Database
from core.database.redis_client import RedisClient
from core.database.models import MySQLClient

log = get_logger(__name__)


@lru_cache(maxsize=1)
def get_services() -> dict:
    """初始化并缓存所有后端服务单例"""
    log.info("Initializing API background services (v2 — Skills + Router + DB)...")

    # ── 1. 向量数据库相关 ────────────────────────────────────────────
    embedder = EmbeddingService(
        model_name=settings.EMBEDDING_MODEL_NAME,
        api_key=settings.EMBEDDING_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL,
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

    # ── 2. LLM 客户端 ────────────────────────────────────────────────
    main_llm = LLMClient.create_from_settings("main")
    judge_llm = LLMClient.create_from_settings("judge")
    lite_llm = LLMClient.create_from_settings("lite")
    router_llm = LLMClient(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model_name=settings.LLM_ROUTER_MODEL_NAME,
        temperature=0.1,      # Router 需要低温度以保证一致性
        max_tokens=256,        # Router 输出很短
    )

    # ── 3. Agent 组件 ─────────────────────────────────────────────────
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
        max_iterations=settings.RAG_MAX_ITERATIONS,
    )

    # ── 4. 幻觉抑制组件 ──────────────────────────────────────────────
    conflict_detector = ConflictDetector(llm_client=lite_llm)

    # ── 5. Skills 注册 ────────────────────────────────────────────────
    registry = SkillRegistry()
    registry.register(RAGSkill(agent=agent))
    registry.register(SummarySkill(retriever=retriever, llm=main_llm))
    registry.register(DefinitionSkill(retriever=retriever, llm=main_llm))
    registry.register(ComplianceCheckSkill(retriever=retriever, llm=main_llm))
    registry.register(ChitchatSkill())
    registry.register(CalculationSkill(llm_client=main_llm, retriever=retriever))
    registry.register(ComparisonSkill(llm_client=main_llm, retriever=retriever))
    registry.register(TimelineSkill(llm_client=main_llm, retriever=retriever))
    registry.register(ExportSkill(llm_client=main_llm, retriever=retriever))

    log.info(f"Registered {len(registry)} Skills: {registry.list_names()}")

    # ── 6. Intent Router ──────────────────────────────────────────────
    intent_router = IntentRouter(
        llm_client=router_llm,
        registry=registry,
        confidence_threshold=settings.ROUTER_CONFIDENCE_THRESHOLD,
    )

    # ── 7. 对话管理器 ─────────────────────────────────────────────────
    storage = ConversationStorage(settings.CONVERSATION_DIR)
    title_gen = TitleGenerator(llm_client=lite_llm)
    conversation_manager = ConversationManager(storage, title_gen)

    # ── 8. 文档处理 ───────────────────────────────────────────────────
    chunker = SemanticChunker(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )

    # ── 9. Redis 缓存 ────────────────────────────────────────────────
    redis_client = RedisClient(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        default_ttl=settings.REDIS_DEFAULT_TTL,
    )

    # ── 10. MySQL / SQLite 持久化 ─────────────────────────────────────
    mysql_client = MySQLClient(database_url=settings.DATABASE_URL)
    mysql_client.create_tables()

    return {
        # 向量存储
        "chroma_store": chroma_store,
        "embedder": embedder,
        "retriever": retriever,
        "reranker": reranker,
        # Agent 原始组件（保持向后兼容）
        "agent": agent,
        # Skills 系统
        "skill_registry": registry,
        "intent_router": intent_router,
        # 幻觉抑制
        "citation_checker": citation_checker,
        "conflict_detector": conflict_detector,
        # 对话管理
        "conversation_manager": conversation_manager,
        # 文档处理
        "chunker": chunker,
        "parser_factory": ParserFactory,
        # 数据库
        "redis_client": redis_client,
        "mysql_client": mysql_client,
    }


# ── 便捷访问器 ────────────────────────────────────────────────────────

def get_agent() -> AgenticRAG:
    return get_services()["agent"]

def get_conversation_manager() -> ConversationManager:
    return get_services()["conversation_manager"]

def get_chroma_store() -> ChromaStore:
    return get_services()["chroma_store"]

def get_retriever() -> HybridRetriever:
    return get_services()["retriever"]

def get_chunker() -> SemanticChunker:
    return get_services()["chunker"]

def get_intent_router() -> IntentRouter:
    return get_services()["intent_router"]

def get_redis_client() -> RedisClient:
    return get_services()["redis_client"]

def get_mysql_client() -> MySQLClient:
    return get_services()["mysql_client"]
