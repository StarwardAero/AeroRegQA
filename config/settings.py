import os
import sys
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv
from pydantic_settings import BaseSettings


def _cloud_llm_overrides() -> dict:
    """Read the optional LLM section without replacing other Cloud secrets."""
    streamlit = sys.modules.get("streamlit")
    if streamlit is None:
        return {}
    from streamlit.errors import StreamlitSecretNotFoundError
    try:
        section = streamlit.secrets.get("aeroregqa_llm", {})
    except StreamlitSecretNotFoundError:
        return {}
    allowed = {
        "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_NAME",
        "LLM_JUDGE_MODEL_NAME", "LLM_LITE_MODEL_NAME",
        "LLM_REASONER_MODEL_NAME", "LLM_ROUTER_MODEL_NAME",
        "LLM_THINKING_MODE",
    }
    return {key: value for key, value in section.items() if key in allowed}

class Settings(BaseSettings):
    """从 .env 加载的全局配置，模块级单例"""

    # 路径配置
    BASE_DIR: Path = Path(__file__).parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    PARSED_DIR: Path = BASE_DIR / "data" / "parsed"
    CHROMA_DIR: Path = BASE_DIR / "data" / "chroma_db"
    CONVERSATION_DIR: Path = BASE_DIR / "data" / "conversations"
    LOGS_DIR: Path = BASE_DIR / "data" / "logs"
    KNOWLEDGE_SEED_PATH: Path = BASE_DIR / "knowledge" / "seed.zip"

    # 各用途默认复用主模型，也可分别指定服务商支持的模型名。
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL_NAME: str = "deepseek-v4-pro"
    # 官方 V4 默认开启深度思考；演示问答显式关闭，避免每个路由/检索步骤长时间等待。
    LLM_THINKING_MODE: Literal["enabled", "disabled"] = "disabled"
    LLM_JUDGE_MODEL_NAME: str = ""
    LLM_LITE_MODEL_NAME: str = ""
    LLM_REASONER_MODEL_NAME: str = ""
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096

    # ── 模型成本估算（元/百万token，用于Dashboard成本展示） ──────
    MODEL_COST_PER_1M_INPUT: dict = {
        "deepseek-chat": 2.0,       # 历史模型估算单价，非实时账单
        "deepseek-reasoner": 4.0,
    }
    MODEL_COST_PER_1M_OUTPUT: dict = {
        "deepseek-chat": 8.0,
        "deepseek-reasoner": 16.0,
    }

    # Embedding (硅基流动 API)
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = "https://api.siliconflow.cn/v1"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024

    # Reranker (硅基流动 API，与 Embedding 共用密钥)
    RERANKER_MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"

    # API / 上传安全配置
    CORS_ALLOW_ORIGINS: str = "http://localhost:8501,http://127.0.0.1:8501"
    MAX_UPLOAD_SIZE_MB: int = 50
    SUPPORTED_UPLOAD_EXTENSIONS: str = ".pdf,.docx,.txt,.md,.csv"

    # RAG 参数
    RAG_TOP_K: int = 5
    RAG_MAX_ITERATIONS: int = 3
    RAG_JUDGE_THRESHOLD: float = 0.7
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 200
    USE_HYBRID_SEARCH: bool = True
    USE_RERANKER: bool = True

    # Router 参数
    ROUTER_CONFIDENCE_THRESHOLD: float = 0.7
    LLM_ROUTER_MODEL_NAME: str = ""  # 未配置时复用主模型

    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_DEFAULT_TTL: int = 3600

    # MySQL / SQLite 配置
    DATABASE_URL: str = "sqlite:///data/app.db"  # 默认 SQLite，生产用 mysql+pymysql://user:pass@host:3306/db

    class Config:
        env_file = ".env"
        extra = "ignore"

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        instance = cls(**_cloud_llm_overrides())
        for field in ["LLM_JUDGE_MODEL_NAME", "LLM_LITE_MODEL_NAME", "LLM_REASONER_MODEL_NAME", "LLM_ROUTER_MODEL_NAME"]:
            if not getattr(instance, field):
                setattr(instance, field, instance.LLM_MODEL_NAME)

        # 自动创建必要目录
        for dir_path in [
            instance.UPLOAD_DIR,
            instance.PARSED_DIR,
            instance.CHROMA_DIR,
            instance.CONVERSATION_DIR,
            instance.LOGS_DIR
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

        return instance

# 模块级单例导出
settings = Settings.load()
