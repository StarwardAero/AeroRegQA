from pathlib import Path
from utils.logger import get_logger
from utils.file_utils import detect_encoding
from .base import BaseParser, ParseError

log = get_logger(__name__)

class TxtParser(BaseParser):
    def parse(self, file_path: Path) -> str:
        if not file_path.exists():
            raise ParseError(f"File not found: {file_path}")
            
        try:
            log.info(f"Parsing TXT: {file_path.name}")
            encoding = detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                return f.read()
        except Exception as e:
            log.error(f"Txt parsing failed: {e}")
            raise ParseError(f"Failed to parse TXT {file_path.name}: {e}")

    def supported_extensions(self) -> list[str]:
        return ['.txt', '.md', '.csv']
