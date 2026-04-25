import fitz  # PyMuPDF
from pathlib import Path
from utils.logger import get_logger
from .base import BaseParser, ParseError

log = get_logger(__name__)

class PDFParser(BaseParser):
    def __init__(self, use_marker: bool = True):
        self.use_marker = use_marker
        self._marker_available = False
        if use_marker:
            try:
                # 尝试导入 marker-pdf，如果没装或者报错则降级
                import marker
                self._marker_available = True
                log.info("Marker-PDF is available.")
            except ImportError:
                log.warning("Marker-PDF not found. Will fallback to PyMuPDF.")
                self._marker_available = False

    def parse(self, file_path: Path) -> str:
        if not file_path.exists():
            raise ParseError(f"File not found: {file_path}")
            
        # 尝试使用 Marker
        if self.use_marker and self._marker_available:
            try:
                log.info(f"Attempting to parse PDF with Marker: {file_path.name}")
                return self._parse_with_marker(file_path)
            except Exception as e:
                log.warning(f"Marker parsing failed: {e}. Falling back to PyMuPDF.")
                
        # 降级使用 PyMuPDF
        try:
            log.info(f"Parsing PDF with PyMuPDF: {file_path.name}")
            return self._parse_with_pymupdf(file_path)
        except Exception as e:
            log.error(f"PyMuPDF parsing failed: {e}")
            raise ParseError(f"Failed to parse PDF {file_path.name}: {e}")

    def _parse_with_marker(self, file_path: Path) -> str:
        # 注意：Marker API 随版本变化可能不同，这里提供一种兼容调用的假设方式
        # 若实际使用中 API 不符，会触发异常并安全降级到 PyMuPDF
        from marker.convert import convert_single_pdf
        from marker.models import load_all_models
        
        models = load_all_models()
        full_text, images, out_meta = convert_single_pdf(str(file_path), models)
        return full_text

    def _parse_with_pymupdf(self, file_path: Path) -> str:
        doc = fitz.open(str(file_path))
        text_blocks = []
        for page in doc:
            text_blocks.append(page.get_text())
        return "\n\n".join(text_blocks)

    def supported_extensions(self) -> list[str]:
        return ['.pdf']
