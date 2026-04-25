from utils.logger import get_logger
from core.rag.llm_client import LLMClient
from config.prompts import format_title_prompt

log = get_logger(__name__)

class TitleGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def generate(self, first_question: str, first_answer: str) -> str:
        """根据首轮对话生成不超过6个字的标题"""
        prompt = format_title_prompt(first_question, first_answer)
        messages = [{"role": "user", "content": prompt}]
        
        try:
            title = self.llm.chat(messages, stream=False)
            title = title.strip().strip('"\'')
            # 严格截断至 6 个字符以内
            if len(title) > 6:
                title = title[:6]
                
            log.info(f"Generated title: '{title}'")
            return title
        except Exception as e:
            log.error(f"Title generation failed: {e}")
            # 兜底截取问题前 6 个字
            return first_question[:6]
