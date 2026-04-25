from pathlib import Path
from utils.logger import get_logger
from .models import Conversation, Message, get_current_time_str
from .storage import ConversationStorage
from .title_generator import TitleGenerator

log = get_logger(__name__)

class ConversationManager:
    def __init__(self, storage: ConversationStorage, title_generator: TitleGenerator):
        self.storage = storage
        self.title_generator = title_generator

    def create_conversation(self, model_name: str) -> Conversation:
        conv = Conversation(model_name=model_name)
        self.storage.save(conv)
        log.info(f"Created new conversation: {conv.conversation_id}")
        return conv

    def add_message(self, conversation_id: str, role: str, content: str, metadata: dict = None) -> None:
        conv = self.storage.load(conversation_id)
        if not conv:
            log.error(f"Cannot add message to non-existent conversation: {conversation_id}")
            return
            
        msg = Message(role=role, content=content, metadata=metadata or {})
        conv.messages.append(msg)
        conv.updated_at = get_current_time_str()
        
        self.storage.save(conv)
        log.debug(f"Added {role} message to {conversation_id}")

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self.storage.load(conversation_id)

    def get_chat_history(self, conversation_id: str, last_n: int = 10) -> list[dict]:
        conv = self.storage.load(conversation_id)
        if not conv or not conv.messages:
            return []
            
        history = []
        # 取最后 last_n 条消息
        recent_messages = conv.messages[-last_n:]
        for msg in recent_messages:
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        return history

    def delete_conversation(self, conversation_id: str) -> None:
        self.storage.delete(conversation_id)

    def list_conversations(self) -> list[dict]:
        return self.storage.list_all()

    def auto_generate_title(self, conversation_id: str) -> str:
        """为首轮对话自动生成短标题并保存"""
        conv = self.storage.load(conversation_id)
        if not conv or len(conv.messages) < 2:
            return "新对话"
            
        # 提取第一条用户提问和第一条 AI 回答
        first_question = next((m.content for m in conv.messages if m.role == 'user'), "")
        first_answer = next((m.content for m in conv.messages if m.role == 'assistant'), "")
        
        if not first_question or not first_answer:
            return "新对话"
            
        title = self.title_generator.generate(first_question, first_answer)
        conv.title = title
        conv.updated_at = get_current_time_str()
        self.storage.save(conv)
        
        return title
