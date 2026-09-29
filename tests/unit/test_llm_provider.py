"""Unit tests for Milestone 3 — LLM Provider abstraction, local streaming, and mock mode."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sarthika_code.domain.config import AppSettings, GenerationSettings
from sarthika_code.domain.errors import ConfigurationError, ProviderError
from sarthika_code.llm.base import (
    CancellationToken,
    ChatMessage,
    LLMProvider,
    StreamCompletedEvent,
    StreamErrorEvent,
    StreamStartedEvent,
    StreamTokenEvent,
)
from sarthika_code.llm.factory import LLMProviderFactory
from sarthika_code.llm.llama_cpp import LlamaCppProvider
from sarthika_code.llm.mock import MockLLMProvider
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.ui.dialogs.provider_test_dialog import ProviderTestDialog
from sarthika_code.ui.main_window import MainWindow

# --------------------------------------------------------------------------
# MockLLMProvider Tests
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_provider_implements_protocol() -> None:
    """Verify MockLLMProvider implements the LLMProvider protocol."""
    provider = MockLLMProvider()
    assert isinstance(provider, LLMProvider)
    assert await provider.health_check() is True


@pytest.mark.asyncio
async def test_mock_provider_streaming_success() -> None:
    """Verify MockLLMProvider yields correct events and accumulates all tokens."""
    canned = "print('Hello world!')"
    provider = MockLLMProvider(token_delay=0.001, canned_response=canned)

    messages = [ChatMessage(role="user", content="Write code")]
    events = []

    async for event in provider.stream_chat(messages):
        events.append(event)

    assert len(events) >= 3
    assert isinstance(events[0], StreamStartedEvent)
    assert events[0].model_name == "mock-offline-model-v0.1"

    token_events = [e for e in events if isinstance(e, StreamTokenEvent)]
    assert len(token_events) > 0

    last_event = events[-1]
    assert isinstance(last_event, StreamCompletedEvent)
    assert last_event.full_text == canned
    assert last_event.total_tokens == len(token_events)


@pytest.mark.asyncio
async def test_mock_provider_generate() -> None:
    """Verify MockLLMProvider.generate produces a complete GenerationResult."""
    canned = "result text"
    provider = MockLLMProvider(token_delay=0.001, canned_response=canned)
    messages = [ChatMessage(role="user", content="hello")]

    result = await provider.generate(messages)
    assert result.text == canned
    assert result.cancelled is False
    assert result.total_tokens is not None and result.total_tokens > 0


@pytest.mark.asyncio
async def test_mock_provider_cancellation() -> None:
    """Verify MockLLMProvider gracefully aborts when CancellationToken is triggered."""
    canned = "one two three four five six seven eight nine ten eleven twelve"
    provider = MockLLMProvider(token_delay=0.02, canned_response=canned)
    cancel_token = CancellationToken()
    messages = [ChatMessage(role="user", content="count")]

    events = []

    async def cancel_soon() -> None:
        await asyncio.sleep(0.05)
        cancel_token.cancel()

    cancel_task = asyncio.create_task(cancel_soon())

    async for event in provider.stream_chat(messages, cancellation_token=cancel_token):
        events.append(event)

    await cancel_task

    last_event = events[-1]
    assert isinstance(last_event, StreamErrorEvent)
    assert last_event.is_cancelled is True
    assert "cancelled" in last_event.error.lower()


@pytest.mark.asyncio
async def test_mock_provider_simulate_unavailable() -> None:
    """Verify MockLLMProvider simulates server unavailability."""
    provider = MockLLMProvider(simulate_unavailable=True)

    assert await provider.health_check() is False

    with pytest.raises(ProviderError) as exc_info:
        messages = [ChatMessage(role="user", content="hi")]
        async for _ in provider.stream_chat(messages):
            pass

    assert "unavailable" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_mock_provider_simulate_interruption() -> None:
    """Verify MockLLMProvider simulates stream interruption mid-generation."""
    canned = "word1 word2 word3 word4 word5 word6 word7 word8"
    provider = MockLLMProvider(
        token_delay=0.001,
        canned_response=canned,
        simulate_stream_interruption=True,
        interruption_after_tokens=3,
    )
    messages = [ChatMessage(role="user", content="test")]
    events = []

    async for event in provider.stream_chat(messages):
        events.append(event)

    last_event = events[-1]
    assert isinstance(last_event, StreamErrorEvent)
    assert last_event.is_cancelled is False
    assert "interruption" in last_event.error.lower()


# --------------------------------------------------------------------------
# LlamaCppProvider Tests
# --------------------------------------------------------------------------


def test_llama_cpp_enforces_loopback() -> None:
    """Verify LlamaCppProvider strictly rejects non-loopback endpoints."""
    # Valid endpoints
    p1 = LlamaCppProvider("http://127.0.0.1:8080")
    assert p1.base_url == "http://127.0.0.1:8080"

    p2 = LlamaCppProvider("http://localhost:8082/")
    assert p2.base_url == "http://localhost:8082"

    # Invalid non-loopback endpoints must raise ConfigurationError
    with pytest.raises(ConfigurationError):
        LlamaCppProvider("http://192.168.1.50:8080")

    with pytest.raises(ConfigurationError):
        LlamaCppProvider("https://api.openai.com/v1")

    with pytest.raises(ConfigurationError):
        LlamaCppProvider("http://remote-server.internal:8080")


def test_llama_cpp_build_request_payload() -> None:
    """Verify request payload format conforms to llama-server OpenAI completions spec."""
    provider = LlamaCppProvider(base_url="http://127.0.0.1:8080", model_name="test-model")
    messages = [
        ChatMessage(role="system", content="You are a helper."),
        ChatMessage(role="user", content="Write a function."),
    ]
    settings = GenerationSettings(
        temperature=0.3,
        top_p=0.9,
        max_tokens=150,
        repeat_penalty=1.15,
        stop_tokens=["<|im_end|>"],
    )

    payload = provider._build_request_payload(messages, settings)

    assert payload["model"] == "test-model"
    assert payload["stream"] is True
    assert payload["temperature"] == 0.3
    assert payload["top_p"] == 0.9
    assert payload["max_tokens"] == 150
    assert payload["repeat_penalty"] == 1.15
    assert payload["stop"] == ["<|im_end|>"]
    assert len(payload["messages"]) == 2
    assert payload["messages"][0] == {"role": "system", "content": "You are a helper."}
    assert payload["messages"][1] == {"role": "user", "content": "Write a function."}


@pytest.mark.asyncio
async def test_llama_cpp_health_check() -> None:
    """Verify LlamaCppProvider health_check queries /health endpoint."""
    provider = LlamaCppProvider("http://127.0.0.1:8080")

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        result = await provider.health_check()
        assert result is True
        mock_get.assert_called_once_with("http://127.0.0.1:8080/health")


@pytest.mark.asyncio
async def test_llama_cpp_stream_chat_success() -> None:
    """Verify LlamaCppProvider parses SSE chunks into StreamTokenEvents."""
    provider = LlamaCppProvider("http://127.0.0.1:8080", model_name="my-gguf-model")
    messages = [ChatMessage(role="user", content="code")]

    sse_lines = [
        "",
        'data: {"choices":[{"delta":{"content":"def "}}]}',
        'data: {"choices":[{"delta":{"content":"add(a, b):"}}]}',
        'data: {"choices":[{"delta":{"content":" return a + b"}}]}',
        "data: [DONE]",
    ]

    async def fake_aiter_lines() -> Any:
        for line in sse_lines:
            yield line

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = fake_aiter_lines

    class FakeStreamContext:
        async def __aenter__(self) -> Any:
            return mock_response

        async def __aexit__(self, *args: Any) -> None:
            pass

    mock_client = MagicMock()
    mock_client.stream.return_value = FakeStreamContext()

    class FakeClientContext:
        async def __aenter__(self) -> Any:
            return mock_client

        async def __aexit__(self, *args: Any) -> None:
            pass

    with patch("httpx.AsyncClient", return_value=FakeClientContext()):
        events = []
        async for event in provider.stream_chat(messages):
            events.append(event)

        assert isinstance(events[0], StreamStartedEvent)
        token_deltas = [e.delta for e in events if isinstance(e, StreamTokenEvent)]
        assert token_deltas == ["def ", "add(a, b):", " return a + b"]

        last = events[-1]
        assert isinstance(last, StreamCompletedEvent)
        assert last.full_text == "def add(a, b): return a + b"
        assert last.total_tokens == 3


@pytest.mark.asyncio
async def test_llama_cpp_stream_chat_cancellation() -> None:
    """Verify cancellation token stops SSE stream consumption early."""
    provider = LlamaCppProvider("http://127.0.0.1:8080")
    cancel_token = CancellationToken()
    messages = [ChatMessage(role="user", content="infinite loop")]

    async def infinite_lines() -> Any:
        yield 'data: {"choices":[{"delta":{"content":"token1"}}]}'
        cancel_token.cancel()
        yield 'data: {"choices":[{"delta":{"content":"token2"}}]}'

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = infinite_lines

    class FakeStreamContext:
        async def __aenter__(self) -> Any:
            return mock_response

        async def __aexit__(self, *args: Any) -> None:
            pass

    mock_client = MagicMock()
    mock_client.stream.return_value = FakeStreamContext()

    class FakeClientContext:
        async def __aenter__(self) -> Any:
            return mock_client

        async def __aexit__(self, *args: Any) -> None:
            pass

    with patch("httpx.AsyncClient", return_value=FakeClientContext()):
        events = []
        async for event in provider.stream_chat(messages, cancellation_token=cancel_token):
            events.append(event)

        last = events[-1]
        assert isinstance(last, StreamErrorEvent)
        assert last.is_cancelled is True


@pytest.mark.asyncio
async def test_llama_cpp_stream_connection_error() -> None:
    """Verify LlamaCppProvider handles ConnectError safely without raising uncaught exception."""
    provider = LlamaCppProvider("http://127.0.0.1:8080")
    messages = [ChatMessage(role="user", content="hi")]

    class FailingClientContext:
        async def __aenter__(self) -> Any:
            raise httpx.ConnectError("Connection refused")

        async def __aexit__(self, *args: Any) -> None:
            pass

    with patch("httpx.AsyncClient", return_value=FailingClientContext()):
        events = []
        async for event in provider.stream_chat(messages):
            events.append(event)

        last = events[-1]
        assert isinstance(last, StreamErrorEvent)
        assert last.is_cancelled is False
        assert "could not connect" in last.error.lower()


# --------------------------------------------------------------------------
# LLMProviderFactory Tests
# --------------------------------------------------------------------------


def test_provider_factory_mock_mode() -> None:
    """Verify LLMProviderFactory returns MockLLMProvider when mock_mode is enabled."""
    settings = AppSettings(mock_mode=True)
    provider = LLMProviderFactory.create_provider(settings)

    assert isinstance(provider, MockLLMProvider)
    assert provider.provider_metadata()["is_mock"] is True


def test_provider_factory_real_mode() -> None:
    """Verify LLMProviderFactory returns LlamaCppProvider when mock_mode is disabled."""
    settings = AppSettings(
        mock_mode=False,
        server_host="127.0.0.1",
        server_port=8082,
        model_path="/path/to/my-model.gguf",
    )
    provider = LLMProviderFactory.create_provider(settings)

    assert isinstance(provider, LlamaCppProvider)
    assert provider.base_url == "http://127.0.0.1:8082"
    assert provider.model_name == "my-model.gguf"


# --------------------------------------------------------------------------
# UI Provider Test Dialog Tests
# --------------------------------------------------------------------------


def test_provider_test_dialog_ui(qapp: Any, settings_service: SettingsService) -> None:
    """Verify ProviderTestDialog initializes controls and switches providers cleanly."""
    dialog = ProviderTestDialog(settings_service=settings_service)

    assert dialog.windowTitle() == "LLM Provider Streaming Test — Sarthika Code"
    assert dialog.cmb_provider.count() == 2
    assert dialog.btn_send.isEnabled() is True
    assert dialog.btn_cancel.isEnabled() is False

    # Switch provider in combo
    dialog.cmb_provider.setCurrentIndex(0)
    assert dialog.cmb_provider.currentData() == "mock"

    dialog.cmb_provider.setCurrentIndex(1)
    assert dialog.cmb_provider.currentData() == "local"

    dialog.close()


def test_main_window_has_streaming_test_action(
    qapp: Any,
    temp_paths: Any,
    settings_service: SettingsService,
) -> None:
    """Verify MainWindow contains streaming test action and button."""
    window = MainWindow(
        paths=temp_paths,
        settings_service=settings_service,
        model_service=None,
        diagnostics_service=None,
    )

    # Check button presence
    assert hasattr(window, "btn_test_streaming")
    assert window.btn_test_streaming.text() == "Test Provider Streaming"

    # Check tools menu action presence
    tools_actions = [a.text() for a in window.menuBar().actions() if "Tools" in a.text()]
    assert len(tools_actions) > 0

    window.close()
