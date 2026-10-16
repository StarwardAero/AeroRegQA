"""Pydantic 请求/响应模型定义"""
from typing import Optional
from pydantic import BaseModel, Field


# ===== Chat =====

class ChatRequest(BaseModel):
    question: str = Field(..., description="用户问题")
    conversation_id: Optional[str] = Field(None, description="对话ID，为空则自动创建新对话")


class ChatSyncResponse(BaseModel):
    answer: str
    sources: list[str]
    conversation_id: str
    iterations: int


# ===== Conversation =====

class ConversationCreate(BaseModel):
    model_name: Optional[str] = Field("default", description="模型名称")


class MessageResponse(BaseModel):
    role: str
    content: str
    timestamp: str
    metadata: dict = {}


class ConversationResponse(BaseModel):
    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class ConversationDetailResponse(BaseModel):
    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[MessageResponse]


# ===== Knowledge =====

class KnowledgeSourceResponse(BaseModel):
    sources: list[str]
    total_count: int


class UploadResponse(BaseModel):
    filename: str
    chunks_count: int
    status: str


# ===== Health =====

class HealthResponse(BaseModel):
    status: str
    version: str
    knowledge_base_stats: dict


# ===== Evaluate =====

class EvaluateRequest(BaseModel):
    questions: list[str] = Field(..., description="待评估的问题列表")


class EvaluateResultItem(BaseModel):
    question: str
    answer_preview: str
    response_time: float
    citation_rate: float
    retrieval_count: int
    iterations: int
    judge_score: Optional[float] = None


class EvaluateResponse(BaseModel):
    total_questions: int
    avg_response_time: float
    avg_citation_rate: float
    avg_iterations: float
    avg_judge_score: Optional[float] = None
    results: list[EvaluateResultItem] = []
