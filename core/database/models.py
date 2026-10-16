"""MySQL ORM 模型 — 对话历史、调用日志、用户反馈、Skill 统计。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Float, Integer, DateTime, Boolean, JSON,
    create_engine, Index,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from utils.logger import get_logger

log = get_logger(__name__)

Base = declarative_base()


# ── 对话历史 ──────────────────────────────────────────────────────────

class ConversationRecord(Base):
    """对话会话记录。"""
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True)
    title = Column(String(255), default="新对话")
    model_name = Column(String(128), default="default")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MessageRecord(Base):
    """对话消息记录。"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False, index=True)
    role = Column(String(16), nullable=False)       # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, default={})         # 存放 sources, skill_name 等
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_conv_timestamp", "conversation_id", "timestamp"),
    )


# ── LLM 调用日志 ─────────────────────────────────────────────────────

class LLMCallLog(Base):
    """LLM 调用日志 — 每次 LLM 调用的 input/output/token 用量/耗时。"""
    __tablename__ = "llm_call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=True, index=True)
    call_type = Column(String(64), nullable=False)    # "rag" | "judge" | "router" | "rewrite"
    model_name = Column(String(128), default="")
    input_text = Column(Text, default="")              # 截断存储（前 2000 字符）
    output_text = Column(Text, default="")             # 截断存储
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)           # 耗时（毫秒）
    success = Column(Boolean, default=True)
    error_message = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_call_type_time", "call_type", "timestamp"),
    )


# ── 用户反馈 ──────────────────────────────────────────────────────────

class UserFeedback(Base):
    """用户对回答质量的反馈。"""
    __tablename__ = "user_feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False)
    message_id = Column(Integer, nullable=True)
    rating = Column(Integer, default=0)                # 1-5 星
    comment = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)


# ── Skill 调用统计 ───────────────────────────────────────────────────

class SkillCallRecord(Base):
    """Skill 调用记录 — 统计各 Skill 的调用频次和效果。"""
    __tablename__ = "skill_call_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=True)
    skill_name = Column(String(64), nullable=False, index=True)
    question_preview = Column(String(500), default="")  # 问题预览（截断）
    confidence = Column(Float, default=0.0)              # Router 的置信度
    routing_method = Column(String(32), default="")      # "keyword" | "llm" | "default"
    duration_ms = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    judge_score = Column(Float, nullable=True)           # Judge 评分（如有）
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_skill_time", "skill_name", "timestamp"),
    )


# ── 数据库客户端 ──────────────────────────────────────────────────────

class MySQLClient:
    """MySQL 数据库客户端 — 负责连接管理和 CRUD 操作。"""

    def __init__(self, database_url: str) -> None:
        """
        Args:
            database_url: SQLAlchemy 连接 URL，示例:
                - "sqlite:///data/app.db"（开发环境）
                - "mysql+pymysql://user:pass@localhost:3306/qa_system"
        """
        self.engine = create_engine(database_url, echo=False, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
        log.info(f"MySQL/SQLite 连接初始化完成: {database_url.split('@')[-1] if '@' in database_url else database_url}")

    def create_tables(self) -> None:
        """创建所有表（如不存在）。"""
        Base.metadata.create_all(self.engine)
        log.info("数据库表已创建/检查完毕")

    def get_session(self):
        """获取数据库 session（用于 with 语句）。"""
        return self.SessionLocal()

    # ── 对话操作 ──────────────────────────────────────────────────────

    def save_conversation(self, conv_id: str, title: str, model_name: str = "default") -> None:
        with self.get_session() as session:
            record = session.get(ConversationRecord, conv_id)
            if record:
                record.title = title
                record.updated_at = datetime.utcnow()
            else:
                record = ConversationRecord(id=conv_id, title=title, model_name=model_name)
                session.add(record)
            session.commit()

    def save_message(
        self, conversation_id: str, role: str, content: str, metadata: dict = None
    ) -> None:
        with self.get_session() as session:
            msg = MessageRecord(
                conversation_id=conversation_id,
                role=role,
                content=content,
                metadata_json=metadata or {},
            )
            session.add(msg)
            session.commit()

    def get_messages(self, conversation_id: str, last_n: int = 20) -> list[dict]:
        with self.get_session() as session:
            msgs = (
                session.query(MessageRecord)
                .filter(MessageRecord.conversation_id == conversation_id)
                .order_by(MessageRecord.timestamp.desc())
                .limit(last_n)
                .all()
            )
            msgs.reverse()
            return [{"role": m.role, "content": m.content, "metadata": m.metadata_json} for m in msgs]

    def list_conversations(self, limit: int = 50) -> list[dict]:
        with self.get_session() as session:
            records = (
                session.query(ConversationRecord)
                .order_by(ConversationRecord.updated_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else "",
                }
                for r in records
            ]

    def delete_conversation(self, conv_id: str) -> None:
        with self.get_session() as session:
            session.query(MessageRecord).filter(MessageRecord.conversation_id == conv_id).delete()
            session.query(ConversationRecord).filter(ConversationRecord.id == conv_id).delete()
            session.commit()

    # ── 调用日志 ──────────────────────────────────────────────────────

    def log_llm_call(
        self,
        call_type: str,
        model_name: str = "",
        input_text: str = "",
        output_text: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        duration_ms: int = 0,
        success: bool = True,
        error_message: str = "",
        conversation_id: str = None,
    ) -> None:
        with self.get_session() as session:
            record = LLMCallLog(
                conversation_id=conversation_id,
                call_type=call_type,
                model_name=model_name,
                input_text=input_text[:2000],
                output_text=output_text[:2000],
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
            )
            session.add(record)
            session.commit()

    # ── Skill 调用记录 ────────────────────────────────────────────────

    def log_skill_call(
        self,
        skill_name: str,
        question_preview: str = "",
        confidence: float = 0.0,
        routing_method: str = "",
        duration_ms: int = 0,
        success: bool = True,
        judge_score: float = None,
        conversation_id: str = None,
    ) -> None:
        with self.get_session() as session:
            record = SkillCallRecord(
                conversation_id=conversation_id,
                skill_name=skill_name,
                question_preview=question_preview[:500],
                confidence=confidence,
                routing_method=routing_method,
                duration_ms=duration_ms,
                success=success,
                judge_score=judge_score,
            )
            session.add(record)
            session.commit()

    # ── 用户反馈 ──────────────────────────────────────────────────────

    def save_feedback(
        self, conversation_id: str, rating: int, comment: str = "", message_id: int = None
    ) -> None:
        with self.get_session() as session:
            fb = UserFeedback(
                conversation_id=conversation_id,
                message_id=message_id,
                rating=rating,
                comment=comment,
            )
            session.add(fb)
            session.commit()
