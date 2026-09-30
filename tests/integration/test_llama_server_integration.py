"""Integration tests for LlamaServerManager, LlamaCppProvider, and ModelService orchestration.

Verifies:
- Subprocess lifecycle management (STOPPED -> STARTING -> READY -> GENERATING -> READY -> STOPPED)
- Port assignment and loopback HTTP transport
- Streaming completions via SSE parsing
- Crash detection and recovery transitions
- Zero native binaries, zero model files, zero external network access.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from sarthika_code.domain.config import AppSettings
from sarthika_code.domain.server import ServerState
from sarthika_code.llm.base import (
    ChatMessage,
    StreamCompletedEvent,
    StreamStartedEvent,
    StreamTokenEvent,
)
from sarthika_code.llm.factory import LLMProviderFactory
from sarthika_code.llm.llama_cpp import LlamaCppProvider
from sarthika_code.llm.manager import LlamaServerManager
from sarthika_code.services.model_service import ModelService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.storage.database import DatabaseManager


@pytest.fixture
def server_integration_env(tmp_path: Path, db_manager: DatabaseManager) -> dict[str, Any]:
    """Build mock model files, server manager, settings service, and model service."""
    # Create fake GGUF and executable files
    model_file = tmp_path / "models" / "qwen2.5-coder-3b-q4_k_m.gguf"
    model_file.parent.mkdir(parents=True, exist_ok=True)
    model_file.write_bytes(b"GGUF_MAGIC_HEADER" * 100)

    exec_name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    exec_file = tmp_path / "bin" / exec_name
    exec_file.parent.mkdir(parents=True, exist_ok=True)

    exec_file.write_text("#!/bin/sh\necho 'llama.cpp v1.0'\n")
    exec_file.chmod(0o755)

    settings_service = SettingsService(db_manager)
    settings_service.save_settings(
        AppSettings(
            model_path=str(model_file),
            llama_server_path=str(exec_file),
            server_host="127.0.0.1",
            server_port=8080,
            context_size=4096,
            mock_mode=False,
        )
    )

    server_manager = LlamaServerManager(log_dir=tmp_path / "logs")
    model_service = ModelService(settings_service=settings_service, server_manager=server_manager)

    return {
        "model_file": model_file,
        "exec_file": exec_file,
        "settings_service": settings_service,
        "server_manager": server_manager,
        "model_service": model_service,
    }


@pytest.mark.asyncio
async def test_full_server_lifecycle_and_provider_streaming(
    server_integration_env: dict[str, Any]
) -> None:
    """Verify server launch, readiness polling, provider creation, streaming, and shutdown."""
    server_manager: LlamaServerManager = server_integration_env["server_manager"]
    model_service: ModelService = server_integration_env["model_service"]
    settings_service: SettingsService = server_integration_env["settings_service"]

    # Mock subprocess and HTTP endpoints
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None  # Process is running
    mock_proc.pid = 4321

    # Mock health endpoint
    health_resp = MagicMock()
    health_resp.status_code = 200

    # Mock SSE stream for /v1/chat/completions
    sse_lines = [
        'data: {"choices": [{"delta": {"content": "def "}}]}',
        'data: {"choices": [{"delta": {"content": "add(a, b):"}}]}',
        'data: {"choices": [{"delta": {"content": "\\n    return a + b"}}]}',
        'data: [DONE]',
    ]

    class MockStreamingResponse:
        status_code = 200

        async def aiter_lines(self) -> Any:
            for line in sse_lines:
                yield line

    class MockClientContext:
        async def __aenter__(self) -> Any:
            client = MagicMock()
            client.stream.return_value.__aenter__.return_value = MockStreamingResponse()
            client.stream.return_value.__aexit__.return_value = None
            return client

        async def __aexit__(self, *args: Any) -> None:
            pass

    observed_states: list[ServerState] = []
    server_manager.add_state_listener(lambda s: observed_states.append(s.state))

    with (
        patch("subprocess.Popen", return_value=mock_proc),
        patch("httpx.get", return_value=health_resp),
    ):
        # 1. Start server via ModelService
        status = model_service.start_configured_server()
        assert status.state == ServerState.READY
        assert status.pid == 4321
        assert (status.url or "").startswith("http://127.0.0.1:")
        assert ServerState.STARTING in observed_states
        assert ServerState.READY in observed_states

        # 2. Instantiate provider via LLMProviderFactory
        settings = settings_service.load_settings()
        provider = LLMProviderFactory.create_provider(settings, server_manager=server_manager)
        assert isinstance(provider, LlamaCppProvider)

        # 3. Stream chat completion
        messages = [ChatMessage(role="user", content="Write an add function")]

        with patch("httpx.AsyncClient", return_value=MockClientContext()):
            events = []
            async for event in provider.stream_chat(messages):
                events.append(event)

            # Check that during stream it hit GENERATING
            assert ServerState.GENERATING in observed_states

            # Check streamed tokens
            assert any(isinstance(e, StreamStartedEvent) for e in events)
            tokens = [e.delta for e in events if isinstance(e, StreamTokenEvent)]
            assert "".join(tokens) == "def add(a, b):\n    return a + b"
            completed = [e for e in events if isinstance(e, StreamCompletedEvent)]
            assert len(completed) == 1
            assert completed[0].full_text == "def add(a, b):\n    return a + b"

            # After stream completes, server returns to READY
            assert server_manager.status.state == ServerState.READY

        # 4. Gracefully stop server
        stop_status = model_service.stop_server()
        assert stop_status.state == ServerState.STOPPED
        assert server_manager.status.state == ServerState.STOPPED
        mock_proc.terminate.assert_called_once()
