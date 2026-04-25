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

    # DeepSeek LLM
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL_NAME: str = "deepseek-chat"
    LLM_JUDGE_MODEL_NAME: str = "deepseek-chat"
    LLM_LITE_MODEL_NAME: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096

    # Embedding (硅基流动 API)
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = "https://api.siliconflow.cn/v1"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024

    # RAG 参数
    RAG_TOP_K: int = 5
    RAG_MAX_ITERATIONS: int = 3
    RAG_JUDGE_THRESHOLD: float = 0.7
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 200

    class Config:
        env_file = ".env"
        extra = "ignore"

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()
        instance = cls()
        
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
