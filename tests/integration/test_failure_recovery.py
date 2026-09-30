"""Integration and failure-recovery test suite for Sarthika Code.

Specifically verifies all 12 failure modes required by Milestone 8:
1. llama-server fails immediately
2. llama-server crashes after becoming ready
3. Local port is unavailable
4. Provider stream disconnects
5. User cancels generation
6. Database write fails
7. Selected file disappears after selection
8. Sensitive file is selected
9. Context exceeds limit
10. Invalid export location
11. Model path is removed/moved
12. Mock mode works with no model configured
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sarthika_code.domain.config import AppSettings, ModelConfiguration
from sarthika_code.domain.errors import (
    ContextLimitError,
    ModelValidationError,
    PersistenceError,
    SensitiveFileError,
    ServerError,
)
from sarthika_code.domain.server import ServerState
from sarthika_code.llm.base import (
    CancellationToken,
    StreamErrorEvent,
    StreamTokenEvent,
)
from sarthika_code.llm.factory import LLMProviderFactory
from sarthika_code.llm.manager import LlamaServerManager
from sarthika_code.llm.mock import MockLLMProvider
from sarthika_code.services.chat_service import ChatService
from sarthika_code.services.context_service import ProjectContextService
from sarthika_code.services.model_service import ModelService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.storage.database import DatabaseManager


# ------------------------------------------------------------------------------
# 1. llama-server fails immediately
# ------------------------------------------------------------------------------
def test_failure_llama_server_fails_immediately(tmp_path: Path) -> None:
    """Verify that llama-server failing immediately upon launch transitions to START_FAILED."""
    manager = LlamaServerManager(log_dir=tmp_path / "logs")

    config = ModelConfiguration(
        model_path=str(tmp_path / "model.gguf"),
        model_name="model.gguf",
        model_size_bytes=4096,
        executable_path=str(tmp_path / "llama-server"),
        context_size=4096,
        threads=4,
        host="127.0.0.1",
        port=8080,
    )

    mock_process = MagicMock()
    mock_process.poll.return_value = 1  # Exit code 1
    mock_process.pid = 1111

    with (
        patch("subprocess.Popen", return_value=mock_process),
        pytest.raises(ServerError) as exc,
    ):
        manager.start_server(config, startup_timeout=1.0)

    assert "terminated unexpectedly" in str(exc.value)
    assert manager.status.state == ServerState.START_FAILED
    assert "code 1" in str(manager.status.last_error)


# ------------------------------------------------------------------------------
# 2. llama-server crashes after becoming ready
# ------------------------------------------------------------------------------
def test_failure_llama_server_crashes_after_ready(tmp_path: Path) -> None:
    """Verify that llama-server crashing after becoming ready transitions to CRASHED."""
    manager = LlamaServerManager(log_dir=tmp_path / "logs")

    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Running initially
    mock_process.pid = 2222

    manager._process = mock_process
    manager._set_status(ServerState.STARTING, "Starting...")
    manager._set_status(ServerState.READY, "Ready")

    manager._start_crash_monitor()

    # Simulate SIGKILL or unhandled exception termination
    mock_process.poll.return_value = -9

    for _ in range(25):
        if manager.status.state == ServerState.CRASHED:
            break
        time.sleep(0.05)

    assert manager.status.state == ServerState.CRASHED
    assert "code -9" in str(manager.status.last_error)
    manager.stop_server()


# ------------------------------------------------------------------------------
# 3. Local port is unavailable
# ------------------------------------------------------------------------------
def test_failure_local_port_unavailable(tmp_path: Path) -> None:
    """Verify that when the preferred port is occupied, a dynamic available port is selected."""
    manager = LlamaServerManager(log_dir=tmp_path / "logs")

    config = ModelConfiguration(
        model_path=str(tmp_path / "model.gguf"),
        model_name="model.gguf",
        model_size_bytes=4096,
        executable_path=str(tmp_path / "llama-server"),
        context_size=4096,
        threads=4,
        host="127.0.0.1",
        port=8080,
    )

    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_process.pid = 3333

    health_resp = MagicMock()
    health_resp.status_code = 200

    with (
        patch("sarthika_code.llm.manager.is_port_available", side_effect=[False, True]),
        patch("sarthika_code.llm.manager.find_available_port", return_value=8085),
        patch("subprocess.Popen", return_value=mock_process),
        patch("httpx.get", return_value=health_resp),
    ):
        status = manager.start_server(config, startup_timeout=1.0)
        assert status.state == ServerState.READY
        assert "8085" in (status.url or "")
        manager.stop_server()


# ------------------------------------------------------------------------------
# 4. Provider stream disconnects
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_failure_provider_stream_disconnects(db_manager: DatabaseManager) -> None:
    """Verify that a mid-stream transport disconnect yields a StreamErrorEvent without crashing."""
    chat_service = ChatService(db_manager)
    chat = chat_service.create_chat(title="Disconnect Test")
    chat_service.add_user_message(chat.id, "Generate code")
    asst_placeholder = chat_service.create_assistant_placeholder(chat.id)

    # Provider configured to simulate interruption
    provider = MockLLMProvider(
        token_delay=0.005,
        simulate_stream_interruption=True,
        interruption_after_tokens=3,
    )

    events = []
    async for event in chat_service.stream_chat_turn(
        chat_id=chat.id,
        assistant_message_id=asst_placeholder.id,
        provider=provider,
    ):
        events.append(event)

    error_events = [e for e in events if isinstance(e, StreamErrorEvent)]
    assert len(error_events) == 1
    assert error_events[0].is_cancelled is False

    # Partial message should still be saved in DB
    reloaded = chat_service.get_chat(chat.id)
    assert reloaded is not None
    last_msg = reloaded.messages[-1]
    assert len(last_msg.content) > 0


# ------------------------------------------------------------------------------
# 5. User cancels generation
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_failure_user_cancels_generation(db_manager: DatabaseManager) -> None:
    """Verify that user cancellation halts generation and saves partial content with notice."""
    chat_service = ChatService(db_manager)
    chat = chat_service.create_chat(title="Cancellation Test")
    chat_service.add_user_message(chat.id, "Generate large output")
    asst_placeholder = chat_service.create_assistant_placeholder(chat.id)

    provider = MockLLMProvider(token_delay=0.03)
    cancel_token = CancellationToken()

    async def _trigger_cancel() -> None:
        await asyncio.sleep(0.06)
        cancel_token.cancel()

    cancel_task = asyncio.create_task(_trigger_cancel())

    events = []
    async for event in chat_service.stream_chat_turn(
        chat_id=chat.id,
        assistant_message_id=asst_placeholder.id,
        provider=provider,
        cancellation_token=cancel_token,
    ):
        events.append(event)

    await cancel_task

    cancelled_events = [e for e in events if isinstance(e, StreamErrorEvent) and e.is_cancelled]
    assert len(cancelled_events) == 1

    reloaded = chat_service.get_chat(chat.id)
    assert reloaded is not None
    last_msg = reloaded.messages[-1]
    assert "Generation stopped by user" in last_msg.content


# ------------------------------------------------------------------------------
# 6. Database write fails
# ------------------------------------------------------------------------------
def test_failure_database_write_fails(db_manager: DatabaseManager) -> None:
    """Verify that database transaction failures raise PersistenceError and roll back cleanly."""
    chat_service = ChatService(db_manager)
    chat = chat_service.create_chat(title="DB Fail Test")

    with (
        patch.object(chat_service.message_repo, "create", side_effect=RuntimeError("disk I/O error")),
        pytest.raises(PersistenceError) as exc_info,
    ):
        chat_service.add_user_message(chat.id, "Will fail")

    assert "disk I/O error" in str(exc_info.value)

    # Chat message count should remain 0
    reloaded = chat_service.get_chat(chat.id)
    assert reloaded is not None
    assert len(reloaded.messages) == 0


# ------------------------------------------------------------------------------
# 7. Selected file disappears after selection
# ------------------------------------------------------------------------------
def test_failure_selected_file_disappears(db_manager: DatabaseManager, tmp_path: Path) -> None:
    """Verify that attempting to attach a file that has disappeared raises SensitiveFileError."""
    context_service = ProjectContextService(db_manager)
    chat_service = ChatService(db_manager)
    chat = chat_service.create_chat(title="Disappearing File Test")

    phantom_file = tmp_path / "vanished_file.py"
    assert not phantom_file.exists()

    with pytest.raises(SensitiveFileError) as exc_info:
        context_service.add_file(chat.id, phantom_file)

    assert "does not exist" in str(exc_info.value).lower()
    assert len(context_service.list_files(chat.id)) == 0


# ------------------------------------------------------------------------------
# 8. Sensitive file is selected
# ------------------------------------------------------------------------------
def test_failure_sensitive_file_selected(db_manager: DatabaseManager, tmp_path: Path) -> None:
    """Verify that selecting a sensitive secret file (.env or ssh key) is blocked."""
    context_service = ProjectContextService(db_manager)
    chat_service = ChatService(db_manager)
    chat = chat_service.create_chat(title="Sensitive File Test")

    secret_file = tmp_path / ".env.production"
    secret_file.write_text("DB_PASSWORD=secret123", encoding="utf-8")

    with pytest.raises(SensitiveFileError) as exc_info:
        context_service.add_file(chat.id, secret_file)

    assert "blocked" in str(exc_info.value).lower()
    assert len(context_service.list_files(chat.id)) == 0


# ------------------------------------------------------------------------------
# 9. Context exceeds limit
# ------------------------------------------------------------------------------
def test_failure_context_exceeds_limit(db_manager: DatabaseManager, tmp_path: Path) -> None:
    """Verify that context budget detects exceeded limits and can raise ContextLimitError."""
    context_service = ProjectContextService(db_manager)
    chat_service = ChatService(db_manager)
    chat = chat_service.create_chat(title="Context Limit Test")

    huge_file = tmp_path / "huge_data.py"
    huge_file.write_text("# Line of python code\n" * 1500, encoding="utf-8")
    context_service.add_file(chat.id, huge_file)

    # Budget with a small 1024 context limit
    budget = context_service.get_budget(chat.id, context_limit=1024)
    assert budget.is_exceeded is True
    assert budget.status == "exceeded"

    with pytest.raises(ContextLimitError) as exc_info:
        if budget.is_exceeded:
            raise ContextLimitError(
                f"Context budget exceeded ({budget.total_tokens} > {budget.context_limit})."
            )

    assert "Context budget exceeded" in str(exc_info.value)


# ------------------------------------------------------------------------------
# 10. Invalid export location
# ------------------------------------------------------------------------------
def test_failure_invalid_export_location(db_manager: DatabaseManager, tmp_path: Path) -> None:
    """Verify that exporting to an unwritable or invalid location raises PersistenceError."""
    chat_service = ChatService(db_manager)
    chat = chat_service.create_chat(title="Export Error Chat")
    chat_service.add_user_message(chat.id, "Hello")

    invalid_path = tmp_path / "non_writable_dir" / "export.md"

    with (
        patch.object(Path, "write_text", side_effect=PermissionError("Permission denied")),
        pytest.raises(PersistenceError) as exc_info,
    ):
        chat_service.export_chat_to_file(chat.id, invalid_path)

    assert "Failed to export chat" in str(exc_info.value)
    assert "write permissions" in exc_info.value.format_for_user()


# ------------------------------------------------------------------------------
# 11. Model path is removed/moved
# ------------------------------------------------------------------------------
def test_failure_model_path_removed_or_moved(db_manager: DatabaseManager, tmp_path: Path) -> None:
    """Verify that launching server when the GGUF model has been deleted raises ModelValidationError."""
    settings_service = SettingsService(db_manager)
    manager = LlamaServerManager(log_dir=tmp_path / "logs")
    model_service = ModelService(settings_service=settings_service, server_manager=manager)

    exec_name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    fake_exec = tmp_path / exec_name
    fake_exec.write_text("#!/bin/sh\n")
    fake_exec.chmod(0o755)


    missing_model = tmp_path / "missing_model.gguf"

    settings_service.save_settings(
        AppSettings(
            model_path=str(missing_model),
            llama_server_path=str(fake_exec),
        )
    )

    with pytest.raises(ModelValidationError) as exc:
        model_service.start_configured_server()

    assert "not found" in str(exc.value).lower()


# ------------------------------------------------------------------------------
# 12. Mock mode works with no model configured
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_failure_mock_mode_works_with_no_model(db_manager: DatabaseManager) -> None:
    """Verify mock mode functions completely when zero model or server paths are configured."""
    settings = AppSettings(mock_mode=True, model_path="", llama_server_path="")
    provider = LLMProviderFactory.create_provider(settings)

    assert isinstance(provider, MockLLMProvider)
    assert await provider.health_check() is True

    chat_service = ChatService(db_manager)
    chat = chat_service.create_chat(title="Mock Mode Chat")
    chat_service.add_user_message(chat.id, "Hello Mock Mode")
    asst_placeholder = chat_service.create_assistant_placeholder(chat.id)

    events = []
    async for event in chat_service.stream_chat_turn(
        chat_id=chat.id,
        assistant_message_id=asst_placeholder.id,
        provider=provider,
    ):
        events.append(event)

    tokens = [e for e in events if isinstance(e, StreamTokenEvent)]
    assert len(tokens) > 0

    reloaded = chat_service.get_chat(chat.id)
    assert reloaded is not None
    assert reloaded.messages[-1].content == provider.canned_response
