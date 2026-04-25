import os
from pathlib import Path
from config.settings import settings
from utils.logger import get_logger
from core.parser.parser_factory import ParserFactory
from core.chunker.semantic_chunker import SemanticChunker
from core.vectorstore.embedder import EmbeddingService
from core.vectorstore.chroma_store import ChromaStore
from core.vectorstore.retriever import HybridRetriever

log = get_logger("test_phase1")

def create_dummy_file():
    fixture_dir = Path("tests/fixtures")
    fixture_dir.mkdir(parents=True, exist_ok=True)
    sample_file = fixture_dir / "sample.txt"
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write("# Introduction\nThis is a test document.\n## Details\nIt contains some details about MAPF algorithms.\n")
    return sample_file

def main():
    log.info("Testing Phase 1 (Data Pipeline)...")
    
    # 1. 准备测试文件
    sample_file = create_dummy_file()
    
    # 2. 解析文件
    log.info("--- Step 1: Parsing ---")
    markdown_text = ParserFactory.parse_file(sample_file)
    print(f"Parsed text length: {len(markdown_text)}")
    
    # 3. 分块
    log.info("--- Step 2: Chunking ---")
    chunker = SemanticChunker(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
    chunks = chunker.chunk_document(markdown_text, sample_file.name)
    print(f"Generated {len(chunks)} chunks.")
    for i, c in enumerate(chunks):
        print(f"Chunk {i+1} metadata: {c.metadata['header_path']}")
        
    # 4. 初始化服务
    log.info("--- Step 3: Embedding & VectorStore ---")
    embedder = EmbeddingService(
        model_name=settings.EMBEDDING_MODEL_NAME,
        api_key=settings.EMBEDDING_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL
    )
    
    # 注意：运行这个测试前，需要确保 .env 中配置了真实的 EMBEDDING_API_KEY
    if not settings.EMBEDDING_API_KEY or "your-siliconflow-key" in settings.EMBEDDING_API_KEY:
        log.warning("EMBEDDING_API_KEY is not set or is dummy. Skipping actual API call and DB insertion.")
        print("Please configure your actual EMBEDDING_API_KEY in .env to test embedding and ChromaDB.")
        return
        
    chroma_store = ChromaStore(persist_dir=settings.CHROMA_DIR, embedding_service=embedder)
    
    # 清理旧数据
    chroma_store.delete_by_source(sample_file.name)
    
    # 写入
    chroma_store.add_documents(chunks)
    print(f"Chroma Stats: {chroma_store.get_collection_stats()}")
    
    # 5. 检索
    log.info("--- Step 4: Retrieval ---")
    retriever = HybridRetriever(chroma_store)
    results = retriever.retrieve("MAPF algorithms details", top_k=1)
    context = retriever.format_context(results)
    
    print("\n--- Retrieved Context ---")
    print(context)
    
    log.info("Phase 1 Test Completed successfully!")

if __name__ == "__main__":
    main()