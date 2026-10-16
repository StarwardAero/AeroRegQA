"""FastAPI 应用入口"""
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import HealthResponse
from api.dependencies import get_services
from api.routes import chat, knowledge, conversation, evaluate
from config.settings import settings


def _parse_origins(origins: str) -> list[str]:
    """解析逗号分隔的 CORS 白名单。"""
    return [origin.strip() for origin in origins.split(",") if origin.strip()]

app = FastAPI(
    title="低空适航与规章问答 AI API",
    description="基于RAG的低空适航与规章智能问答系统 REST API",
    version="1.0.0",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(settings.CORS_ALLOW_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(conversation.router)
app.include_router(evaluate.router)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化服务"""
    get_services()


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """健康检查端点"""
    services = get_services()
    chroma_store = services["chroma_store"]
    stats = chroma_store.get_collection_stats()
    sources = chroma_store.list_sources()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        knowledge_base_stats={
            "total_chunks": stats.get("total_chunks", 0),
            "total_sources": len(sources),
            "sources": sources,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
