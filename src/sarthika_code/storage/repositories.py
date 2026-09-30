"""Data access repositories for Sarthika Code using SQLAlchemy 2.0.

Provides transactional persistence primitives for settings, chats, and messages.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from sarthika_code.storage.models import (
    ChatModel,
    MessageModel,
    SelectedFileContextModel,
    SettingModel,
)


class SettingsRepository:
    """Repository handling key-value settings persistence in SQLite."""

    def get(self, session: Session, key: str) -> str | None:
        """Retrieve the raw string value of a setting by its key."""
        stmt = select(SettingModel.value).where(SettingModel.key == key)
        return session.execute(stmt).scalar_one_or_none()

    def set(self, session: Session, key: str, value: str) -> None:
        """Store or update a setting key-value pair."""
        setting = session.get(SettingModel, key)
        if setting is None:
            setting = SettingModel(key=key, value=value)
            session.add(setting)
        else:
            setting.value = value

    def get_all(self, session: Session) -> dict[str, str]:
        """Retrieve all stored settings as a dictionary."""
        stmt = select(SettingModel)
        results = session.execute(stmt).scalars().all()
        return {item.key: item.value for item in results}

    def delete(self, session: Session, key: str) -> bool:
        """Remove a setting by key. Returns True if deleted, False if not found."""
        setting = session.get(SettingModel, key)
        if setting is not None:
            session.delete(setting)
            return True
        return False


class ChatRepository:
    """Repository handling conversation session lifecycle in SQLite."""

    def create(
        self,
        session: Session,
        chat_id: str,
        title: str = "New Chat",
        workflow: str = "general_chat",
        model_name: str = "",
        model_path: str = "",
    ) -> ChatModel:
        """Create and persist a new Chat record."""
        now = datetime.now(UTC)
        chat = ChatModel(
            id=chat_id,
            title=title,
            workflow=workflow,
            model_name=model_name,
            model_path=model_path,
            created_at=now,
            updated_at=now,
        )
        session.add(chat)
        return chat

    def get(self, session: Session, chat_id: str) -> ChatModel | None:
        """Retrieve a Chat by its ID, returning None if not found."""
        return session.get(ChatModel, chat_id)

    def list_chats(self, session: Session) -> list[ChatModel]:
        """Retrieve all chats ordered by most recently updated."""
        stmt = select(ChatModel).order_by(ChatModel.updated_at.desc())
        return list(session.execute(stmt).scalars().all())

    def update_title(self, session: Session, chat_id: str, title: str) -> bool:
        """Update the title and updated_at timestamp of a chat."""
        chat = session.get(ChatModel, chat_id)
        if chat is None:
            return False
        chat.title = title
        chat.updated_at = datetime.now(UTC)
        return True

    def update_workflow(self, session: Session, chat_id: str, workflow: str) -> bool:
        """Update the workflow identifier of a conversation."""
        chat = session.get(ChatModel, chat_id)
        if chat is None:
            return False
        chat.workflow = workflow
        chat.updated_at = datetime.now(UTC)
        return True

    def touch(self, session: Session, chat_id: str) -> None:
        """Bump the updated_at timestamp to move the chat to top of list."""
        chat = session.get(ChatModel, chat_id)
        if chat is not None:
            chat.updated_at = datetime.now(UTC)

    def delete(self, session: Session, chat_id: str) -> bool:
        """Delete a chat and cascade-delete its messages and context records."""
        chat = session.get(ChatModel, chat_id)
        if chat is None:
            return False
        session.delete(chat)
        return True

    def delete_all(self, session: Session) -> int:
        """Delete all chats, cascading to messages and file context records. Returns count."""
        chats = list(session.execute(select(ChatModel)).scalars().all())
        count = len(chats)
        for chat in chats:
            session.delete(chat)
        return count


class MessageRepository:
    """Repository handling individual message turn persistence in SQLite."""

    def create(
        self,
        session: Session,
        message_id: str,
        chat_id: str,
        role: str,
        content: str,
        token_count: int | None = None,
        generation_duration_ms: int | None = None,
    ) -> MessageModel:
        """Create and persist a new message in a chat."""
        msg = MessageModel(
            id=message_id,
            chat_id=chat_id,
            role=role,
            content=content,
            token_count=token_count,
            generation_duration_ms=generation_duration_ms,
            created_at=datetime.now(UTC),
        )
        session.add(msg)
        return msg

    def get(self, session: Session, message_id: str) -> MessageModel | None:
        """Retrieve a message by its ID."""
        return session.get(MessageModel, message_id)

    def list_by_chat(self, session: Session, chat_id: str) -> list[MessageModel]:
        """Retrieve all messages for a given chat, ordered chronologically."""
        stmt = (
            select(MessageModel)
            .where(MessageModel.chat_id == chat_id)
            .order_by(MessageModel.created_at.asc())
        )
        return list(session.execute(stmt).scalars().all())

    def update_content(
        self,
        session: Session,
        message_id: str,
        content: str,
        token_count: int | None = None,
        generation_duration_ms: int | None = None,
    ) -> bool:
        """Update content, tokens, and duration of an existing message."""
        msg = session.get(MessageModel, message_id)
        if msg is None:
            return False
        msg.content = content
        if token_count is not None:
            msg.token_count = token_count
        if generation_duration_ms is not None:
            msg.generation_duration_ms = generation_duration_ms
        return True

    def delete(self, session: Session, message_id: str) -> bool:
        """Delete a specific message."""
        msg = session.get(MessageModel, message_id)
        if msg is None:
            return False
        session.delete(msg)
        return True

    def delete_last_assistant_and_get_user_message(
        self,
        session: Session,
        chat_id: str,
    ) -> MessageModel | None:
        """Find and delete the last assistant message (if present), returning the preceding user message."""
        messages = self.list_by_chat(session, chat_id)
        if not messages:
            return None

        last_msg = messages[-1]
        if last_msg.role == "assistant":
            session.delete(last_msg)
            # Find the last user message
            for msg in reversed(messages[:-1]):
                if msg.role == "user":
                    return msg
            return None
        elif last_msg.role == "user":
            return last_msg

        return None


class SelectedFileContextRepository:
    """Repository handling persistence of user-selected file contexts."""

    def create(
        self,
        session: Session,
        context_id: str,
        chat_id: str,
        file_path: str,
        display_name: str,
        language: str,
        content: str,
        byte_size: int,
        line_start: int | None = None,
        line_end: int | None = None,
    ) -> SelectedFileContextModel:
        """Persist a new selected file context record."""
        record = SelectedFileContextModel(
            id=context_id,
            chat_id=chat_id,
            file_path=file_path,
            display_name=display_name,
            language=language,
            content=content,
            byte_size=byte_size,
            line_start=line_start,
            line_end=line_end,
            created_at=datetime.now(UTC),
        )
        session.add(record)
        return record

    def list_by_chat(self, session: Session, chat_id: str) -> list[SelectedFileContextModel]:
        """Retrieve all selected file contexts for a given chat."""
        stmt = (
            select(SelectedFileContextModel)
            .where(SelectedFileContextModel.chat_id == chat_id)
            .order_by(SelectedFileContextModel.created_at.asc())
        )
        return list(session.execute(stmt).scalars().all())

    def delete(self, session: Session, context_id: str) -> bool:
        """Delete an attached file context record by its ID."""
        record = session.get(SelectedFileContextModel, context_id)
        if record is None:
            return False
        session.delete(record)
        return True

    def delete_by_chat(self, session: Session, chat_id: str) -> int:
        """Delete all attached file contexts for a conversation."""
        records = self.list_by_chat(session, chat_id)
        for r in records:
            session.delete(r)
        return len(records)
