from utils.logger import get_logger
from core.chunker.chunk_models import DocumentChunk
from .chroma_store import ChromaStore

log = get_logger(__name__)

class HybridRetriever:
    def __init__(self, chroma_store: ChromaStore):
        self.chroma_store = chroma_store

    def retrieve(self, query: str, top_k: int = 5) -> list[DocumentChunk]:
        log.info(f"Retrieving top {top_k} chunks for query: '{query}'")
        return self.chroma_store.similarity_search(query, top_k)

    def format_context(self, chunks: list[DocumentChunk]) -> str:
        """格式化带引用编号的上下文"""
        if not chunks:
            return "无相关上下文。"
            
        formatted_parts = []
        for idx, chunk in enumerate(chunks, 1):
            source = chunk.metadata.get("source_file", "Unknown")
            chapter = chunk.metadata.get("header_path", "Global")
            
            part = f"[{idx}] (来源: {source}, 章节: {chapter})\n{chunk.content}"
            formatted_parts.append(part)
            
        return "\n\n".join(formatted_parts)
