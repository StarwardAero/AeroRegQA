import docx
from pathlib import Path
from utils.logger import get_logger
from .base import BaseParser, ParseError

log = get_logger(__name__)

class DocxParser(BaseParser):
    def parse(self, file_path: Path) -> str:
        if not file_path.exists():
            raise ParseError(f"File not found: {file_path}")
            
        try:
            log.info(f"Parsing DOCX: {file_path.name}")
            doc = docx.Document(str(file_path))
            markdown_lines = []
            
            for para in doc.paragraphs:
                style_name = para.style.name.lower()
                text = para.text.strip()
                if not text:
                    continue
                    
                # 简单映射 Heading 1/2/3 为 Markdown
                if style_name.startswith('heading'):
                    try:
                        level = int(style_name.replace('heading ', '').strip())
                        level = min(level, 6) # 最大 h6
                        markdown_lines.append(f"{'#' * level} {text}")
                    except ValueError:
                        markdown_lines.append(text)
                else:
                    markdown_lines.append(text)
                    
            return "\n\n".join(markdown_lines)
            
        except Exception as e:
            log.error(f"Docx parsing failed: {e}")
            raise ParseError(f"Failed to parse Docx {file_path.name}: {e}")

    def supported_extensions(self) -> list[str]:
        return ['.docx']
