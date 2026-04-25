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
from core.rag.llm_client import LLMClient
from core.rag.judge import ResponseJudge
from core.rag.query_rewriter import QueryRewriter
from core.rag.agent import AgenticRAG
from core.conversation.storage import ConversationStorage
from core.conversation.title_generator import TitleGenerator
from core.conversation.manager import ConversationManager

# UI 组件
from ui.components import sidebar, chat_area

log = get_logger(__name__)

@st.cache_resource
def get_services() -> dict:
    """初始化并缓存所有后端服务单例，防止每次页面刷新重建连接"""
    log.info("Initializing background services...")
    
    # 1. 向量数据库相关
    embedder = EmbeddingService(
        model_name=settings.EMBEDDING_MODEL_NAME,
        api_key=settings.EMBEDDING_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL
    )
    chroma_store = ChromaStore(persist_dir=settings.CHROMA_DIR, embedding_service=embedder)
    retriever = HybridRetriever(chroma_store)
    
    # 2. LLM 客户端
    main_llm = LLMClient.create_from_settings("main")
    judge_llm = LLMClient.create_from_settings("judge")
    lite_llm = LLMClient.create_from_settings("lite")
    
    # 3. Agent 组件
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
    
    # 4. 对话管理器
    storage = ConversationStorage(settings.CONVERSATION_DIR)
    title_gen = TitleGenerator(llm_client=lite_llm)
    conversation_manager = ConversationManager(storage, title_gen)
    
    return {
        "chroma_store": chroma_store,
        "agent": agent,
        "conversation_manager": conversation_manager
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