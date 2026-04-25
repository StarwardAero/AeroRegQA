import json
from pathlib import Path
from utils.logger import get_logger
from .models import Conversation

log = get_logger(__name__)

class ConversationStorage:
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, conversation: Conversation) -> None:
        file_path = self.storage_dir / f"{conversation.conversation_id}.json"
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation.to_dict(), f, ensure_ascii=False, indent=2)
            log.debug(f"Saved conversation {conversation.conversation_id}")
        except Exception as e:
            log.error(f"Failed to save conversation {conversation.conversation_id}: {e}")

    def load(self, conversation_id: str) -> Conversation | None:
        file_path = self.storage_dir / f"{conversation_id}.json"
        if not file_path.exists():
            log.warning(f"Conversation {conversation_id} not found.")
            return None
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return Conversation.from_dict(data)
        except Exception as e:
            log.error(f"Failed to load conversation {conversation_id}: {e}")
            return None

    def delete(self, conversation_id: str) -> None:
        file_path = self.storage_dir / f"{conversation_id}.json"
        try:
            if file_path.exists():
                file_path.unlink()
                log.info(f"Deleted conversation {conversation_id}")
        except Exception as e:
            log.error(f"Failed to delete conversation {conversation_id}: {e}")

    def list_all(self) -> list[dict]:
        """返回所有对话的摘要信息，按更新时间降序"""
        summaries = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    summaries.append({
                        "id": data.get("conversation_id"),
                        "title": data.get("title", "未知标题"),
                        "updated_at": data.get("updated_at")
                    })
            except Exception as e:
                log.warning(f"Failed to read {file_path}: {e}")
                
        # 降序排序
        summaries.sort(key=lambda x: x["updated_at"], reverse=True)
        return summaries
