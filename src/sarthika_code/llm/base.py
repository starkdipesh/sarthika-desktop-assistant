"""LLMProvider protocol and typed event/request models for Sarthika Code.

Provides a clean provider abstraction decoupling domain logic and UI from
concrete inference implementations (LlamaCppProvider, MockLLMProvider).
"""

from __future__ import annotations

import threading
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from sarthika_code.domain.config import GenerationSettings


@dataclass(frozen=True)
class ChatMessage:
    """Represents a message turn passed into the model."""

    role: str  # 'system', 'user', or 'assistant'
    content: str


class CancellationToken:
    """Thread-safe cancellation token to signal early termination of generation."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        """Signal cancellation."""
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Return True if cancellation was requested."""
        return self._event.is_set()

    def reset(self) -> None:
        """Reset the cancellation token."""
        self._event.clear()


@dataclass(frozen=True)
class StreamEvent:
    """Base class for all streaming events emitted during token generation."""
    pass


@dataclass(frozen=True)
class StreamStartedEvent(StreamEvent):
    """Emitted when stream connection is established."""

    model_name: str | None = None


@dataclass(frozen=True)
class StreamTokenEvent(StreamEvent):
    """Emitted for each generated token fragment."""

    delta: str
    token_index: int = 0


@dataclass(frozen=True)
class StreamCompletedEvent(StreamEvent):
    """Emitted when generation concludes successfully."""

    full_text: str
    total_tokens: int | None = None
    duration_ms: int | None = None


@dataclass(frozen=True)
class StreamErrorEvent(StreamEvent):
    """Emitted when generation encounters an error or is cancelled."""

    error: str
    is_cancelled: bool = False


@dataclass(frozen=True)
class GenerationResult:
    """Result of a non-streaming or completed generation request."""

    text: str
    total_tokens: int | None = None
    duration_ms: int | None = None
    cancelled: bool = False


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol that all LLM inference providers must implement."""

    async def health_check(self) -> bool:
        """Verify provider availability and server readiness."""
        ...

    def stream_chat(
        self,
        messages: list[ChatMessage],
        settings: GenerationSettings | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream token events asynchronously."""
        ...

    async def generate(
        self,
        messages: list[ChatMessage],
        settings: GenerationSettings | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> GenerationResult:
        """Generate a complete text response asynchronously."""
        ...

    def cancel(self) -> None:
        """Signal cancellation of any active in-flight request."""
        ...

    def provider_metadata(self) -> dict[str, Any]:
        """Return provider operational metadata (name, host, is_mock, etc.)."""
        ...
