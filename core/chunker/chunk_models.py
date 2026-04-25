from dataclasses import dataclass, field
import uuid

@dataclass
class DocumentChunk:
    """表示知识库中的一个文本块"""
    content: str
    metadata: dict = field(default_factory=dict)
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
