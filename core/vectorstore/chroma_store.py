import chromadb
from pathlib import Path
from utils.logger import get_logger
from core.chunker.chunk_models import DocumentChunk
from .embedder import EmbeddingService

log = get_logger(__name__)

class ChromaStore:
    def __init__(self, persist_dir: Path, embedding_service: EmbeddingService):
        # Windows 兼容：路径必须用 str() 转换
        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.embedding_service = embedding_service
        self.collection_name = "default"
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        log.info(f"ChromaDB initialized at {persist_dir}")

    def add_documents(self, chunks: list[DocumentChunk], collection_name: str = "default") -> int:
        """批量写入向量库"""
        if not chunks:
            return 0
            
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedding_service.embed_texts(texts)
        
        ids = [chunk.chunk_id for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        
        # 考虑到 Chroma 的单次写入限制，这里可以简单分批，但这里假设前面已经切好且不大
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        log.info(f"Added {len(chunks)} chunks to ChromaDB collection '{collection_name}'")
        return len(chunks)

    def delete_by_source(self, source_file: str, collection_name: str = "default") -> int:
        """删除指定来源文件的所有 chunk"""
        results = self.collection.get(where={"source_file": source_file})
        ids_to_delete = results.get("ids", [])
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
            log.info(f"Deleted {len(ids_to_delete)} chunks for source: {source_file}")
        return len(ids_to_delete)

    def similarity_search(self, query: str, top_k: int = 5) -> list[DocumentChunk]:
        """相似度搜索"""
        query_embedding = self.embedding_service.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        chunks = []
        if results and results.get("documents") and len(results["documents"][0]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            ids = results["ids"][0]
            
            for i in range(len(docs)):
                chunk = DocumentChunk(
                    chunk_id=ids[i],
                    content=docs[i],
                    metadata=metas[i]
                )
                chunks.append(chunk)
                
        return chunks

    def get_collection_stats(self, collection_name: str = "default") -> dict:
        count = self.collection.count()
        return {"total_chunks": count}

    def list_sources(self, collection_name: str = "default") -> list[str]:
        results = self.collection.get(include=["metadatas"])
        sources = set()
        for meta in results.get("metadatas", []):
            if "source_file" in meta:
                sources.add(meta["source_file"])
        return list(sources)
