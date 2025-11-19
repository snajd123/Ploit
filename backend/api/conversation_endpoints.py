"""
API endpoints for Claude conversation history management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.models.conversation_models import ClaudeConversation, ClaudeMessage

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


# Response models
class MessageResponse(BaseModel):
    message_id: int
    role: str
    content: str
    tool_calls: Optional[dict] = None
    usage: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    conversation_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    conversation_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse]

    class Config:
        from_attributes = True


class CreateConversationRequest(BaseModel):
    title: str


class UpdateConversationRequest(BaseModel):
    title: str


# Endpoints
@router.get("/", response_model=List[ConversationListItem])
async def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get list of all conversations, most recent first."""
    conversations = db.query(ClaudeConversation).order_by(
        desc(ClaudeConversation.updated_at)
    ).limit(limit).all()

    result = []
    for conv in conversations:
        result.append(ConversationListItem(
            conversation_id=conv.conversation_id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=len(conv.messages)
        ))

    return result


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific conversation with all its messages."""
    conversation = db.query(ClaudeConversation).filter(
        ClaudeConversation.conversation_id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationDetail(
        conversation_id=conversation.conversation_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageResponse(
            message_id=msg.message_id,
            role=msg.role,
            content=msg.content,
            tool_calls=msg.tool_calls,
            usage=msg.usage,
            created_at=msg.created_at
        ) for msg in sorted(conversation.messages, key=lambda m: m.created_at)]
    )


@router.post("/", response_model=ConversationDetail)
async def create_conversation(
    request: CreateConversationRequest,
    db: Session = Depends(get_db)
):
    """Create a new conversation."""
    conversation = ClaudeConversation(title=request.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return ConversationDetail(
        conversation_id=conversation.conversation_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[]
    )


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: int,
    request: UpdateConversationRequest,
    db: Session = Depends(get_db)
):
    """Update conversation title."""
    conversation = db.query(ClaudeConversation).filter(
        ClaudeConversation.conversation_id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.title = request.title
    conversation.updated_at = datetime.utcnow()
    db.commit()

    return {"success": True, "message": "Conversation updated"}


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its messages."""
    conversation = db.query(ClaudeConversation).filter(
        ClaudeConversation.conversation_id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conversation)
    db.commit()

    return {"success": True, "message": "Conversation deleted"}
