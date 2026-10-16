"""重建向量索引脚本 — 读取 data/uploads/ 下所有文档，解析分块后写入 ChromaDB。"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings
from core.parser.parser_factory import ParserFactory
from core.chunker.semantic_chunker import SemanticChunker
from core.vectorstore.embedder import EmbeddingService
from core.vectorstore.chroma_store import ChromaStore
from utils.logger import get_logger

log = get_logger(__name__)


def main():
    settings = Settings()

    log.info("=" * 60)
    log.info("开始重建向量索引")
    log.info("=" * 60)

    # 初始化服务
    embedder = EmbeddingService(
        api_key=settings.EMBEDDING_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL,
        model_name=settings.EMBEDDING_MODEL_NAME,
    )
    chroma_store = ChromaStore(
        persist_dir=settings.CHROMA_DIR,
        embedding_service=embedder,
    )
    chunker = SemanticChunker(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )

    # 扫描 uploads 目录
    upload_dir = settings.UPLOAD_DIR
    supported_exts = {".pdf", ".docx", ".txt", ".md", ".csv"}
    files = [f for f in upload_dir.iterdir() if f.suffix.lower() in supported_exts]

    log.info(f"发现 {len(files)} 个文档待处理")

    total_chunks = 0
    for idx, file_path in enumerate(files, 1):
        log.info(f"[{idx}/{len(files)}] 处理: {file_path.name}")

        try:
            # 解析
            markdown_text = ParserFactory.parse_file(file_path)
            log.info(f"  解析完成，文本长度: {len(markdown_text)} 字符")

            # 分块
            chunks = chunker.chunk_document(markdown_text, source_file=file_path.name)
            log.info(f"  分块完成，生成 {len(chunks)} 个 chunks")

            # 写入向量库
            added = chroma_store.add_documents(chunks)
            total_chunks += added
            log.info(f"  入库完成，写入 {added} 个 chunks")

        except Exception as e:
            log.error(f"  处理失败: {e}")
            continue

    # 统计
    stats = chroma_store.get_collection_stats()
    log.info("=" * 60)
    log.info(f"索引重建完成！")
    log.info(f"  处理文件数: {len(files)}")
    log.info(f"  总 chunks 数: {stats['total_chunks']}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
