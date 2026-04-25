import time
from typing import List
import openai
from langchain_core.embeddings import Embeddings
from utils.logger import get_logger

log = get_logger(__name__)

class EmbeddingService:
    def __init__(self, model_name: str, api_key: str, base_url: str):
        self.model_name = model_name
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        
    def embed_texts(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        """批量调用 Embedding API (含分批+重试)"""
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            log.debug(f"Embedding batch {i//batch_size + 1}, size: {len(batch)}")
            
            retries = 3
            for attempt in range(retries):
                try:
                    response = self.client.embeddings.create(
                        model=self.model_name,
                        input=batch
                    )
                    # 确保顺序对应
                    batch_embeddings = [data.embedding for data in sorted(response.data, key=lambda x: x.index)]
                    all_embeddings.extend(batch_embeddings)
                    break
                except Exception as e:
                    if attempt < retries - 1:
                        sleep_time = 2 ** attempt
                        log.warning(f"Embedding API failed: {e}. Retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                    else:
                        log.error(f"Embedding API failed after {retries} attempts.")
                        raise e
        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        """单条调用"""
        return self.embed_texts([query])[0]

    def get_langchain_embeddings(self) -> Embeddings:
        """返回 LangChain 兼容对象"""
        class LangchainEmbeddingWrapper(Embeddings):
            def __init__(self, service):
                self.service = service
            def embed_documents(self, texts: List[str]) -> List[List[float]]:
                return self.service.embed_texts(texts)
            def embed_query(self, text: str) -> List[float]:
                return self.service.embed_query(text)
                
        return LangchainEmbeddingWrapper(self)
