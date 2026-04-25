from dataclasses import dataclass, field, asdict
from datetime import datetime
import uuid

def get_current_time_str() -> str:
    return datetime.now().isoformat()

@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str = field(default_factory=get_current_time_str)
    metadata: dict = field(default_factory=dict)  # 存放 sources, agent_steps 等

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(**data)

@dataclass
class Conversation:
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "新对话"
    messages: list[Message] = field(default_factory=list)
    created_at: str = field(default_factory=get_current_time_str)
    updated_at: str = field(default_factory=get_current_time_str)
    model_name: str = "default"

    def to_dict(self) -> dict:
        # 特殊处理 messages 列表
        d = asdict(self)
        d['messages'] = [m.to_dict() for m in self.messages]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        messages_data = data.pop('messages', [])
        messages = [Message.from_dict(m) for m in messages_data]
        return cls(messages=messages, **data)
