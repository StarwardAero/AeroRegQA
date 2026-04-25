import re
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.logger import get_logger
from .chunk_models import DocumentChunk

log = get_logger(__name__)

class SemanticChunker:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # 使用 LangChain 的分块器处理过长文本
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", ". ", " "]
        )

    def chunk_document(self, markdown_text: str, source_file: str) -> list[DocumentChunk]:
        """将 Markdown 文本按标题语义切分，并添加 overlap"""
        log.info(f"Starting chunking for {source_file}")
        
        # 1. 尝试按标题分割
        sections = self._split_by_headers(markdown_text)
        
        chunks = []
        chunk_index = 0
        
        # 2. 对每一个 section 检查长度，如果超长就二次切分
        for section in sections:
            header_path = section.get('header_path', 'Global')
            content = section.get('content', '').strip()
            
            if not content:
                continue
                
            # 二次切分
            split_texts = self.text_splitter.split_text(content)
            for st in split_texts:
                metadata = {
                    "source_file": source_file,
                    "header_path": header_path,
                    "chunk_index": chunk_index,
                    "char_count": len(st)
                }
                # 生成带标题前缀的内容，增强检索上下文
                enriched_content = f"{header_path}\n{st}"
                chunks.append(DocumentChunk(content=enriched_content, metadata=metadata))
                chunk_index += 1
                
        log.info(f"Finished chunking {source_file}. Generated {len(chunks)} chunks.")
        return chunks

    def _split_by_headers(self, text: str) -> list[dict]:
        """正则匹配 H1/H2/H3 标题切分文档"""
        # 匹配以 1-3 个 '#' 开头的行
        header_pattern = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
        
        matches = list(header_pattern.finditer(text))
        
        if not matches:
            # 如果没有标题，整体作为一个 Section
            return [{"header_path": "Global", "content": text}]
            
        sections = []
        last_end = 0
        current_header_path = []
        
        # 提取第一个匹配前的内容（可能是没有标题的引言）
        if matches[0].start() > 0:
            pre_content = text[0:matches[0].start()].strip()
            if pre_content:
                sections.append({"header_path": "Global", "content": pre_content})
        
        for i, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            
            # 更新层级路径 (例如: 1 Introduction > 1.1 Background)
            current_header_path = current_header_path[:level-1]
            current_header_path.append(title)
            path_str = " > ".join(current_header_path)
            
            start_pos = match.end()
            end_pos = matches[i+1].start() if i + 1 < len(matches) else len(text)
            
            content = text[start_pos:end_pos].strip()
            sections.append({
                "header_path": path_str,
                "content": content
            })
            
        return sections
