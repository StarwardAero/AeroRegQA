from abc import ABC, abstractmethod
from pathlib import Path

class ParseError(Exception):
    """文档解析异常基类"""
    pass

class BaseParser(ABC):
    """文档解析器抽象基类"""
    
    @abstractmethod
    def parse(self, file_path: Path) -> str:
        """
        解析文件并返回 Markdown 格式的文本
        
        Args:
            file_path: 文件绝对路径
            
        Returns:
            str: 提取的文本（尽量保留 Markdown 结构和 LaTeX 公式）
            
        Raises:
            ParseError: 解析失败时抛出
        """
        pass
    
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名列表，如 ['.pdf']"""
        pass
