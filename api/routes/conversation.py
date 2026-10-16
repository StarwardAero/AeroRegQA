"""对话管理接口"""
from fastapi import APIRouter, HTTPException

from api.schemas import (
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse,
    MessageResponse,
)
from api.dependencies import get_services

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


@router.post("", response_model=ConversationResponse)
async def create_conversation(body: ConversationCreate):
    """创建新对话"""
    services = get_services()
    cm = services["conversation_manager"]
    conv = cm.create_conversation(model_name=body.model_name or "default")
    return ConversationResponse(
        conversation_id=conv.conversation_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=len(conv.messages),
    )


@router.get("", response_model=list[ConversationResponse])
async def list_conversations():
    """获取对话列表"""
    services = get_services()
    cm = services["conversation_manager"]
    conversations = cm.list_conversations()
    result = []
    for c in conversations:
        result.append(ConversationResponse(
            conversation_id=c.get("conversation_id", ""),
            title=c.get("title", "新对话"),
            created_at=c.get("created_at", ""),
            updated_at=c.get("updated_at", ""),
            message_count=c.get("message_count", 0),
        ))
    return result


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: str):
    """获取对话详情（含消息列表）"""
    services = get_services()
    cm = services["conversation_manager"]
    conv = cm.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return ConversationDetailResponse(
        conversation_id=conv.conversation_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[
            MessageResponse(
                role=m.role,
                content=m.content,
                timestamp=m.timestamp,
                metadata=m.metadata,
            )
            for m in conv.messages
        ],
    )


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话"""
    services = get_services()
    cm = services["conversation_manager"]
    conv = cm.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    cm.delete_conversation(conversation_id)
    return {"message": "对话已删除", "conversation_id": conversation_id}
