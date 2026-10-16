"""知识库管理接口"""
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from api.schemas import UploadResponse, KnowledgeSourceResponse
from api.dependencies import get_services
from config.settings import settings
from core.parser.parser_factory import ParserFactory
from utils.file_utils import resolve_safe_upload_path

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge"])


def _supported_extensions() -> set[str]:
    return {
        ext.strip().lower()
        for ext in settings.SUPPORTED_UPLOAD_EXTENSIONS.split(",")
        if ext.strip()
    }


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """上传文档到知识库：解析 → 分块 → 向量化 → 入库"""
    services = get_services()
    chroma_store = services["chroma_store"]
    chunker = services["chunker"]

    # 检查文件扩展名
    original_filename = file.filename or "unknown"
    filename, save_path = resolve_safe_upload_path(original_filename, settings.UPLOAD_DIR)
    suffix = Path(filename).suffix.lower()
    supported = _supported_extensions()
    if suffix not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {suffix}。支持: {', '.join(supported)}",
        )

    # 保存文件到 uploads 目录
    try:
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        content = await file.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"文件超过大小限制: {settings.MAX_UPLOAD_SIZE_MB}MB",
            )
        with open(save_path, "wb") as f:
            f.write(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {e}")

    # 解析文档
    try:
        markdown_text = ParserFactory.parse_file(save_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件解析失败: {e}")

    # 分块
    chunks = chunker.chunk_document(markdown_text, source_file=filename)

    # 入库
    chroma_store.delete_by_source(filename)
    added_count = chroma_store.add_documents(chunks)

    return UploadResponse(
        filename=filename,
        chunks_count=added_count,
        status="success",
    )


@router.get("/sources", response_model=KnowledgeSourceResponse)
async def list_sources():
    """列出知识库中所有已入库的文件"""
    services = get_services()
    chroma_store = services["chroma_store"]
    sources = chroma_store.list_sources()
    return KnowledgeSourceResponse(sources=sources, total_count=len(sources))


@router.delete("/{source}")
async def delete_source(source: str):
    """删除指定来源文件的所有向量"""
    services = get_services()
    chroma_store = services["chroma_store"]
    deleted_count = chroma_store.delete_by_source(source)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"未找到来源文件: {source}")
    return {"message": f"已删除 {deleted_count} 个文档块", "source": source}
