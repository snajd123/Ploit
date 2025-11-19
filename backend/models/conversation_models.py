"""
SQLAlchemy models for Claude AI conversation history.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base


class ClaudeConversation(Base):
    """Claude AI conversation session"""
    __tablename__ = 'claude_conversations'

    conversation_id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to messages
    messages = relationship("ClaudeMessage", back_populates="conversation", cascade="all, delete-orphan")


class ClaudeMessage(Base):
    """Individual message in a Claude AI conversation"""
    __tablename__ = 'claude_messages'

    message_id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('claude_conversations.conversation_id', ondelete='CASCADE'), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    tool_calls = Column(JSONB, nullable=True)
    usage = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship to conversation
    conversation = relationship("ClaudeConversation", back_populates="messages")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name='check_role'),
    )
