"""Unit tests for Milestone 4 ChatService, ChatRepository, and MessageRepository."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from sarthika_code.domain.chat import derive_chat_title
from sarthika_code.llm.base import (
    CancellationToken,
    StreamCompletedEvent,
    StreamErrorEvent,
    StreamStartedEvent,
    StreamTokenEvent,
)
from sarthika_code.llm.mock import MockLLMProvider
from sarthika_code.services.chat_service import ChatService
from sarthika_code.storage.database import DatabaseManager


@pytest.fixture
def chat_service(db_manager: DatabaseManager) -> ChatService:
    """Provide a ChatService wired to an isolated test database."""
    return ChatService(db_manager=db_manager)


def test_derive_chat_title() -> None:
    """Verify local short title derivation without external APIs."""
    assert derive_chat_title("") == "New Chat"
    assert derive_chat_title("   ") == "New Chat"
    assert derive_chat_title("How do I sort a list in Python?") == "How do I sort a list"
    assert derive_chat_title("```python\ndef test(): pass\n```") == "Def test(): pass"
    assert derive_chat_title("Write a simple HTTP server using Python asyncio") == "Write a simple HTTP server using"


def test_chat_creation_and_listing(chat_service: ChatService) -> None:
    """Verify chat creation, default values, and ordering by recent update."""
    chat1 = chat_service.create_chat(title="Chat 1")
    assert chat1.id is not None
    assert chat1.title == "Chat 1"

    chat2 = chat_service.create_chat(title="Chat 2")

    chats = chat_service.list_chats()
    assert len(chats) >= 2
    # chat2 was created last, so it should appear first
    assert chats[0].id == chat2.id


def test_rename_and_delete_chat(chat_service: ChatService) -> None:
    """Verify chat renaming and safe cascade deletion."""
    chat = chat_service.create_chat(title="Initial Title")
    assert chat_service.rename_chat(chat.id, "Refactored Title") is True

    updated = chat_service.get_chat(chat.id)
    assert updated is not None
    assert updated.title == "Refactored Title"

    # Add message
    chat_service.add_user_message(chat.id, "Hello")

    # Delete
    assert chat_service.delete_chat(chat.id) is True
    assert chat_service.get_chat(chat.id) is None


def test_add_user_message_auto_derives_title(chat_service: ChatService) -> None:
    """Verify first user prompt updates 'New Chat' title automatically."""
    chat = chat_service.create_chat(title="New Chat")

    msg = chat_service.add_user_message(chat.id, "Explain Python list comprehensions in detail")
    assert msg.content == "Explain Python list comprehensions in detail"
    assert msg.role == "user"

    updated_chat = chat_service.get_chat(chat.id)
    assert updated_chat is not None
    assert updated_chat.title == "Explain Python list comprehensions in"


def test_retry_last_message(chat_service: ChatService) -> None:
    """Verify retry removes the assistant response and prepares a new turn."""
    chat = chat_service.create_chat(title="Coding Chat")
    chat_service.add_user_message(chat.id, "How to reverse a string?")
    asst_placeholder = chat_service.create_assistant_placeholder(chat.id)
    chat_service.update_assistant_message(asst_placeholder.id, "Use s[::-1]", token_count=5)

    loaded = chat_service.get_chat(chat.id)
    assert loaded is not None
    assert len(loaded.messages) == 2

    # Retry
    retry_result = chat_service.retry_last_message(chat.id)
    assert retry_result is not None
    prompt, new_asst = retry_result
    assert prompt == "How to reverse a string?"
    assert new_asst.id != asst_placeholder.id

    # The old assistant message was removed, new placeholder exists
    reloaded = chat_service.get_chat(chat.id)
    assert reloaded is not None
    assert len(reloaded.messages) == 2
    assert reloaded.messages[-1].id == new_asst.id
    assert reloaded.messages[-1].content == ""


@pytest.mark.asyncio
async def test_stream_chat_turn_success(chat_service: ChatService) -> None:
    """Verify end-to-end streaming through ChatService and persistent checkpointing."""
    chat = chat_service.create_chat(title="Streaming Test")
    chat_service.add_user_message(chat.id, "Write hello")
    asst_msg = chat_service.create_assistant_placeholder(chat.id)

    canned = "def hello():\n    return 'world'"
    provider = MockLLMProvider(token_delay=0.001, canned_response=canned)

    events = []
    async for event in chat_service.stream_chat_turn(
        chat_id=chat.id,
        assistant_message_id=asst_msg.id,
        provider=provider,
    ):
        events.append(event)

    assert any(isinstance(e, StreamStartedEvent) for e in events)
    assert any(isinstance(e, StreamTokenEvent) for e in events)
    completed = [e for e in events if isinstance(e, StreamCompletedEvent)]
    assert len(completed) == 1
    assert completed[0].full_text == canned

    # Verify message in database is populated
    reloaded = chat_service.get_chat(chat.id)
    assert reloaded is not None
    last_msg = reloaded.messages[-1]
    assert last_msg.content == canned
    assert last_msg.token_count is not None and last_msg.token_count > 0


@pytest.mark.asyncio
async def test_stream_chat_turn_cancellation(chat_service: ChatService) -> None:
    """Verify mid-stream cancellation preserves partial tokens and marks generation stopped."""
    chat = chat_service.create_chat(title="Cancel Test")
    chat_service.add_user_message(chat.id, "Count to fifty")
    asst_msg = chat_service.create_assistant_placeholder(chat.id)

    canned = "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20"
    provider = MockLLMProvider(token_delay=0.02, canned_response=canned)
    cancel_token = CancellationToken()

    async def cancel_after() -> None:
        await asyncio.sleep(0.05)
        cancel_token.cancel()

    cancel_task = asyncio.create_task(cancel_after())

    events = []
    async for event in chat_service.stream_chat_turn(
        chat_id=chat.id,
        assistant_message_id=asst_msg.id,
        provider=provider,
        cancellation_token=cancel_token,
    ):
        events.append(event)

    await cancel_task

    errors = [e for e in events if isinstance(e, StreamErrorEvent) and e.is_cancelled]
    assert len(errors) == 1

    # Database must retain partial output with notice
    reloaded = chat_service.get_chat(chat.id)
    assert reloaded is not None
    last_msg = reloaded.messages[-1]
    assert "stopped by user" in last_msg.content


def test_export_chat_markdown_and_text(chat_service: ChatService, tmp_path: Path) -> None:
    """Verify Markdown and Plaintext export formats omit internal DB metadata and logs."""
    chat = chat_service.create_chat(title="Export Test Chat")
    chat_service.add_user_message(chat.id, "What is SQLite?")
    asst = chat_service.create_assistant_placeholder(chat.id)
    chat_service.update_assistant_message(asst.id, "SQLite is a C-language library.")

    # Export to Markdown string
    md_content = chat_service.export_chat_markdown(chat.id)
    assert "# Export Test Chat" in md_content
    assert "What is SQLite?" in md_content
    assert "SQLite is a C-language library." in md_content
    # Strictly ensure sensitive/internal data is NOT included
    assert "database_file" not in md_content
    assert ".sqlite" not in md_content
    assert "traceback" not in md_content
    assert "llama_server_path" not in md_content

    # Export to text file
    txt_file = tmp_path / "chat_export.txt"
    chat_service.export_chat_to_file(chat.id, txt_file, file_format="txt")
    assert txt_file.exists()
    txt_content = txt_file.read_text(encoding="utf-8")
    assert "SARTHIKA CODE — CONVERSATION EXPORT" in txt_content
    assert "What is SQLite?" in txt_content
    assert "database_file" not in txt_content


def test_export_chat_invalid_location(chat_service: ChatService, tmp_path: Path) -> None:
    """Verify export_chat_to_file raises PersistenceError on unwritable or invalid file location."""
    from unittest.mock import patch

    from sarthika_code.domain.errors import PersistenceError

    chat = chat_service.create_chat(title="Export Fail")
    chat_service.add_user_message(chat.id, "Hello")

    # Target an invalid path that cannot be written
    invalid_dest = tmp_path / "protected" / "chat.md"

    with (
        patch.object(Path, "write_text", side_effect=OSError("Read-only filesystem")),
        pytest.raises(PersistenceError) as exc_info,
    ):
        chat_service.export_chat_to_file(chat.id, invalid_dest)

    assert "Failed to export chat" in str(exc_info.value)
    assert "write permissions" in exc_info.value.format_for_user()


def test_export_nonexistent_chat_raises_persistence_error(chat_service: ChatService) -> None:
    """Verify exporting a nonexistent chat raises PersistenceError."""
    from sarthika_code.domain.errors import PersistenceError

    with pytest.raises(PersistenceError) as exc:
        chat_service.export_chat_markdown("non-existent-id")
    assert "non-existent" in str(exc.value).lower()


def test_database_write_failure_raises_persistence_error(chat_service: ChatService) -> None:
    """Verify database write failure during message creation raises PersistenceError."""
    from unittest.mock import patch

    from sarthika_code.domain.errors import PersistenceError

    chat = chat_service.create_chat(title="DB Error Chat")

    with (
        patch.object(chat_service.message_repo, "create", side_effect=RuntimeError("disk full")),
        pytest.raises(PersistenceError) as exc_info,
    ):
        chat_service.add_user_message(chat.id, "Test prompt")

    assert "disk full" in str(exc_info.value)
    assert isinstance(exc_info.value, PersistenceError)


def test_rename_and_delete_nonexistent_chat(chat_service: ChatService) -> None:
    """Verify renaming or deleting a missing chat ID returns False cleanly without crashing."""
    assert chat_service.rename_chat("missing-id-1234", "New Title") is False
    assert chat_service.delete_chat("missing-id-1234") is False

