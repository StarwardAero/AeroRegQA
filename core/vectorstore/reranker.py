import requests
from utils.logger import get_logger
from core.chunker.chunk_models import DocumentChunk

log = get_logger(__name__)


class Reranker:
    """使用硅基流动 BGE-Reranker API 对检索结果重排序"""

    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    def rerank(
        self,
        query: str,
        chunks: list[DocumentChunk],
        top_n: int = 5,
    ) -> list[DocumentChunk]:
        """
        调用 Rerank API 对候选 chunks 重排序。

        Args:
            query: 用户查询
            chunks: 待排序的文档块列表
            top_n: 返回前 N 个结果

        Returns:
            按相关性降序排列的 top_n 个 DocumentChunk
        """
        if not chunks:
            return []

        documents = [chunk.content for chunk in chunks]

        try:
            response = requests.post(
                f"{self.base_url}/rerank",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "query": query,
                    "documents": documents,
                    "top_n": top_n,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            # API 返回格式: {"results": [{"index": 0, "relevance_score": 0.95}, ...]}
            ranked_results = sorted(
                data["results"], key=lambda x: x["relevance_score"], reverse=True
            )

            reranked_chunks = []
            for item in ranked_results[:top_n]:
                idx = item["index"]
                if idx < len(chunks):
                    reranked_chunks.append(chunks[idx])

            log.info(
                f"Rerank completed: {len(chunks)} candidates -> {len(reranked_chunks)} results"
            )
            return reranked_chunks

        except Exception as e:
            log.warning(f"Rerank API failed: {e}. Falling back to original order.")
            return chunks[:top_n]
