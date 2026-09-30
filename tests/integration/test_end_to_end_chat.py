"""End-to-end integration tests for multi-turn chat workflow, context attachments, and export.

Uses:
- Temporary isolated SQLite database
- Isolated AppPaths
- ProjectContextService
- ChatService
- MockLLMProvider
- Zero cloud, zero model weights, zero native binaries.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sarthika_code.app.paths import AppPaths
from sarthika_code.domain.config import GenerationSettings
from sarthika_code.llm.base import (
    StreamCompletedEvent,
    StreamStartedEvent,
    StreamTokenEvent,
)
from sarthika_code.llm.mock import MockLLMProvider
from sarthika_code.services.chat_service import ChatService
from sarthika_code.services.context_service import ProjectContextService
from sarthika_code.storage.database import DatabaseManager


@pytest.fixture
def chat_integration_env(temp_paths: AppPaths, db_manager: DatabaseManager) -> dict[str, object]:
    """Assemble all services against an isolated temporary environment."""
    context_service = ProjectContextService(db_manager)
    chat_service = ChatService(db_manager)

    return {
        "paths": temp_paths,
        "db": db_manager,
        "context_service": context_service,
        "chat_service": chat_service,
    }


@pytest.mark.asyncio
async def test_end_to_end_chat_workflow_with_context(
    chat_integration_env: dict[str, object], tmp_path: Path
) -> None:
    """Verify complete end-to-end conversational turn:

    1. Create chat with specific workflow
    2. Attach safe source files
    3. Verify context prompt and budget metrics
    4. Stream assistant turn with token persistence
    5. Export conversation to Markdown and verify contents
    6. Cascade delete conversation and verify database cleanup
    """
    chat_service: ChatService = chat_integration_env["chat_service"]  # type: ignore[assignment]
    context_service: ProjectContextService = chat_integration_env["context_service"]  # type: ignore[assignment]

    # Step 1: Create a chat session with the 'refactor_code' workflow
    chat = chat_service.create_chat(title="New Chat", workflow="refactor_code")
    assert chat.id is not None
    assert chat.workflow == "refactor_code"

    # Step 2: Attach safe local files as read-only context
    src_file1 = tmp_path / "algorithm.py"
    src_file1.write_text(
        "def bubble_sort(arr):\n"
        "    n = len(arr)\n"
        "    for i in range(n):\n"
        "        for j in range(0, n - i - 1):\n"
        "            if arr[j] > arr[j + 1]:\n"
        "                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n"
        "    return arr\n",
        encoding="utf-8",
    )
    context_service.add_file(chat.id, src_file1)

    attached = context_service.list_files(chat.id)
    assert len(attached) == 1
    assert attached[0].display_name == "algorithm.py"
    assert attached[0].language == "python"

    # Step 3: Verify context budget calculation
    budget = context_service.get_budget(chat.id, context_limit=4096)
    assert budget.status == "safe"
    assert not budget.is_exceeded
    assert budget.total_files == 1
    assert budget.total_tokens > 0

    # Build context prompt
    ctx_prompt = context_service.build_context_prompt(chat.id)
    assert "BEGIN UNTRUSTED ATTACHED FILE CONTEXT" in ctx_prompt
    assert "def bubble_sort(arr):" in ctx_prompt

    # Step 4: Add user prompt and stream assistant response turn
    user_prompt = "Refactor this bubble sort into a more efficient quicksort implementation."
    chat_service.add_user_message(chat.id, user_prompt)

    # Title should have been auto-derived
    updated_chat = chat_service.get_chat(chat.id)
    assert updated_chat is not None
    assert updated_chat.title.startswith("Refactor this bubble sort")

    asst_placeholder = chat_service.create_assistant_placeholder(chat.id)
    assert asst_placeholder.id is not None

    canned_answer = (
        "Here is the optimized quicksort implementation:\n\n"
        "```python\n"
        "def quicksort(arr):\n"
        "    if len(arr) <= 1:\n"
        "        return arr\n"
        "    pivot = arr[len(arr) // 2]\n"
        "    left = [x for x in arr if x < pivot]\n"
        "    middle = [x for x in arr if x == pivot]\n"
        "    right = [x for x in arr if x > pivot]\n"
        "    return quicksort(left) + middle + quicksort(right)\n"
        "```"
    )
    provider = MockLLMProvider(token_delay=0.001, canned_response=canned_answer)

    events = []
    async for event in chat_service.stream_chat_turn(
        chat_id=chat.id,
        assistant_message_id=asst_placeholder.id,
        provider=provider,
        settings=GenerationSettings(temperature=0.2, max_tokens=1024),
        file_context_prompt=ctx_prompt,
    ):
        events.append(event)

    # Verify stream events
    assert any(isinstance(e, StreamStartedEvent) for e in events)
    tokens = [e for e in events if isinstance(e, StreamTokenEvent)]
    assert len(tokens) > 0
    completed = [e for e in events if isinstance(e, StreamCompletedEvent)]
    assert len(completed) == 1
    assert completed[0].full_text == canned_answer

    # Step 5: Check database persistence of turn
    loaded_chat = chat_service.get_chat(chat.id)
    assert loaded_chat is not None
    assert len(loaded_chat.messages) == 2
    assert loaded_chat.messages[0].role == "user"
    assert loaded_chat.messages[0].content == user_prompt
    assert loaded_chat.messages[1].role == "assistant"
    assert loaded_chat.messages[1].content == canned_answer
    assert loaded_chat.messages[1].token_count is not None and loaded_chat.messages[1].token_count > 0

    # Step 6: Export conversation to Markdown
    export_file = tmp_path / "exports" / "chat_export.md"
    chat_service.export_chat_to_file(chat.id, export_file, file_format="markdown")
    assert export_file.exists()

    md_text = export_file.read_text(encoding="utf-8")
    assert user_prompt in md_text
    assert "quicksort" in md_text
    # Ensure no internal metadata leaked into export
    assert "llama_server" not in md_text
    assert ".sqlite" not in md_text

    # Step 7: Delete conversation and verify cleanup
    assert chat_service.delete_chat(chat.id) is True
    assert chat_service.get_chat(chat.id) is None
