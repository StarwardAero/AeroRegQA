from pathlib import Path
from utils.logger import get_logger
from .base import BaseParser, ParseError
from .pdf_parser import PDFParser
from .docx_parser import DocxParser
from .txt_parser import TxtParser

log = get_logger(__name__)

class ParserFactory:
    _parsers: dict[str, type[BaseParser]] = {
        '.pdf': PDFParser,
        '.docx': DocxParser,
        '.txt': TxtParser,
        '.md': TxtParser,
        '.csv': TxtParser
    }

    @staticmethod
    def get_parser(file_path: Path) -> BaseParser:
        ext = file_path.suffix.lower()
        parser_cls = ParserFactory._parsers.get(ext)
        if not parser_cls:
            raise ParseError(f"Unsupported file extension: {ext}")
        return parser_cls()

    @staticmethod
    def parse_file(file_path: Path) -> str:
        """
        便捷方法：直接解析文件
        """
        parser = ParserFactory.get_parser(file_path)
        return parser.parse(file_path)
