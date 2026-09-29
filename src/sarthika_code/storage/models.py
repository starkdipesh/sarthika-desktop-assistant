"""SQLAlchemy 2.0 declarative database models for Sarthika Code.

Defines persistence tables for Chat, Message, Setting, and SelectedFileContext
with strict foreign keys, cascade deletion, and indexing.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy entities in Sarthika Code."""
    pass


class ChatModel(Base):
    """Represents a conversation session."""

    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Conversation")
    workflow: Mapped[str] = mapped_column(String(64), nullable=False, default="explain_code")
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    model_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False, index=True
    )

    messages: Mapped[list[MessageModel]] = relationship(
        "MessageModel",
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at",
    )
    file_contexts: Mapped[list[SelectedFileContextModel]] = relationship(
        "SelectedFileContextModel",
        back_populates="chat",
        cascade="all, delete-orphan",
    )


class MessageModel(Base):
    """Represents an individual message turn in a conversation."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chat_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # 'system', 'user', 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    chat: Mapped[ChatModel] = relationship("ChatModel", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_chat_id_created_at", "chat_id", "created_at"),
    )


class SelectedFileContextModel(Base):
    """Represents a user-selected source file attached as read-only context."""

    __tablename__ = "selected_file_contexts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chat_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    chat: Mapped[ChatModel] = relationship("ChatModel", back_populates="file_contexts")


class SettingModel(Base):
    """Represents a persistent key-value configuration setting."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded value
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
