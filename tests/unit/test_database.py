"""Unit tests for SQLite database setup, models, and transactions."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import inspect

from sarthika_code.domain.errors import PersistenceError
from sarthika_code.storage.database import DatabaseManager
from sarthika_code.storage.models import (
    ChatModel,
    MessageModel,
    SelectedFileContextModel,
)


def test_schema_initialization(db_manager: DatabaseManager) -> None:
    """Verify that all four required tables are created in the database."""
    inspector = inspect(db_manager.engine)
    tables = inspector.get_table_names()

    assert "chats" in tables
    assert "messages" in tables
    assert "selected_file_contexts" in tables
    assert "settings" in tables


def test_chat_and_message_cascade_deletion(db_manager: DatabaseManager) -> None:
    """Verify that deleting a Chat cascades and removes its associated Messages."""
    chat_id = str(uuid.uuid4())
    msg_id = str(uuid.uuid4())

    with db_manager.session() as session:
        chat = ChatModel(
            id=chat_id,
            title="Test Chat",
            workflow="explain_code",
            model_name="Qwen2.5-Coder-3B",
            model_path="/models/qwen.gguf",
        )
        session.add(chat)

        msg = MessageModel(
            id=msg_id,
            chat_id=chat_id,
            role="user",
            content="Can you explain this query?",
        )
        session.add(msg)

    # Verify entities exist
    with db_manager.session() as session:
        queried_chat = session.get(ChatModel, chat_id)
        assert queried_chat is not None
        assert len(queried_chat.messages) == 1
        assert queried_chat.messages[0].id == msg_id

    # Delete parent chat
    with db_manager.session() as session:
        chat_to_delete = session.get(ChatModel, chat_id)
        assert chat_to_delete is not None
        session.delete(chat_to_delete)

    # Verify message was also deleted by cascade
    with db_manager.session() as session:
        assert session.get(ChatModel, chat_id) is None
        assert session.get(MessageModel, msg_id) is None


def test_selected_file_context_persistence(db_manager: DatabaseManager) -> None:
    """Verify storing and querying SelectedFileContext models."""
    chat_id = str(uuid.uuid4())
    file_id = str(uuid.uuid4())

    with db_manager.session() as session:
        chat = ChatModel(id=chat_id, title="File Context Chat")
        session.add(chat)

        file_ctx = SelectedFileContextModel(
            id=file_id,
            chat_id=chat_id,
            file_path="/projects/src/main.py",
            display_name="main.py",
            language="python",
            content="print('hello')",
            byte_size=14,
        )
        session.add(file_ctx)

    with db_manager.session() as session:
        retrieved = session.get(SelectedFileContextModel, file_id)
        assert retrieved is not None
        assert retrieved.display_name == "main.py"
        assert retrieved.content == "print('hello')"


def test_transaction_rollback_on_failure(db_manager: DatabaseManager) -> None:
    """Verify that an exception inside the session context manager rolls back."""
    chat_id = str(uuid.uuid4())

    with pytest.raises(PersistenceError), db_manager.session() as session:
        chat = ChatModel(id=chat_id, title="Will Rollback")
        session.add(chat)
        # Trigger intentional integrity error or exception
        raise RuntimeError("Forced simulation error")

    # Verify chat was not persisted
    with db_manager.session() as session:
        assert session.get(ChatModel, chat_id) is None
