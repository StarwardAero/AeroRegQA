import re

def clean_markdown(text: str) -> str:
    """去除垃圾字符"""
    text = text.replace('\x00', '')
    return text.strip()

def normalize_latex(text: str) -> str:
    """标准化 LaTeX 格式"""
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text)
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    return text

def truncate_text(text: str, max_chars: int) -> str:
    """安全截断文本"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."
