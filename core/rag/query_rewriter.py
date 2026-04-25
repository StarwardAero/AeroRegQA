from utils.logger import get_logger
from .llm_client import LLMClient
from config.prompts import format_rewrite_prompt

log = get_logger(__name__)

class QueryRewriter:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def rewrite(self, original_query: str, chat_history: list[dict] | None = None) -> str:
        """消解多轮对话指代，重写检索查询"""
        # 首轮无历史或历史极短，无需重写
        if not chat_history or len(chat_history) < 2:
            log.debug("No chat history, returning original query.")
            return original_query

        # 取最近 3 轮（6条消息）构建历史上下文字符串
        recent_history = chat_history[-6:]
        history_str = ""
        for msg in recent_history:
            role = "用户" if msg.get("role") == "user" else "助手"
            history_str += f"【{role}】: {msg.get('content')}\n"

        prompt = format_rewrite_prompt(original_query, history_str)
        messages = [{"role": "user", "content": prompt}]
        
        try:
            rewritten_query = self.llm.chat(messages, stream=False)
            rewritten_query = rewritten_query.strip().strip('"\'')
            log.info(f"Original query: '{original_query}' -> Rewritten: '{rewritten_query}'")
            return rewritten_query
        except Exception as e:
            log.error(f"Query rewrite failed: {e}. Falling back to original.")
            return original_query
