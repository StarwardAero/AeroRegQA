import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

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

    # ── DeepSeek LLM 三级模型路由（V4 + R1） ─────────────────────
    # 模型分层策略（DeepSeek V4 为主力模型）：
    #   - lite:     DeepSeek V4（简单任务：闲聊、路由分类、搜索摘要）
    #   - main:     DeepSeek V4（常规任务：RAG问答、对比分析）
    #   - reasoner: DeepSeek R1（复杂任务：Judge评估、多文档综合、深度推理）
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL_NAME: str = "deepseek-chat"            # 主模型 — DeepSeek V4
    LLM_JUDGE_MODEL_NAME: str = ""
    LLM_LITE_MODEL_NAME: str = ""
    LLM_REASONER_MODEL_NAME: str = ""
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096

    # ── 模型成本估算（元/百万token，用于Dashboard成本展示） ──────
    MODEL_COST_PER_1M_INPUT: dict = {
        "deepseek-chat": 2.0,       # DeepSeek V4 输入约 2元/百万token
        "deepseek-reasoner": 4.0,   # DeepSeek R1 输入约 4元/百万token
    }
    MODEL_COST_PER_1M_OUTPUT: dict = {
        "deepseek-chat": 8.0,       # DeepSeek V4 输出约 8元/百万token
        "deepseek-reasoner": 16.0,  # DeepSeek R1 输出约 16元/百万token
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
        instance = cls()
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
