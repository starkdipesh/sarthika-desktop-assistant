"""Deterministic offline MockLLMProvider for Sarthika Code.

Enables testing of UI, streaming, cancellation, and error handling
without requiring GGUF model weights, native compilers, or network calls.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from sarthika_code.domain.config import GenerationSettings
from sarthika_code.domain.errors import ProviderError
from sarthika_code.llm.base import (
    CancellationToken,
    ChatMessage,
    GenerationResult,
    LLMProvider,
    StreamCompletedEvent,
    StreamErrorEvent,
    StreamEvent,
    StreamStartedEvent,
    StreamTokenEvent,
)


class MockLLMProvider:
    """Offline mock provider yielding deterministic token streams."""

    DEFAULT_CANNED_RESPONSE = (
        "Hello! I am running in **Offline Mock / Demo Mode**.\n\n"
        "Here is a sample Python snippet demonstrating local-first code analysis:\n\n"
        "```python\n"
        "def analyze_source_code(file_path: str) -> dict:\n"
        "    \"\"\"Analyze a local code file without cloud inference.\"\"\"\n"
        "    return {\n"
        "        'status': 'offline',\n"
        "        'file': file_path,\n"
        "        'verified': True,\n"
        "    }\n"
        "```\n\n"
        "You can test response streaming, markdown formatting, and generation cancellation safely."
    )

    def __init__(
        self,
        token_delay: float = 0.02,
        canned_response: str | None = None,
        simulate_unavailable: bool = False,
        simulate_stream_interruption: bool = False,
        interruption_after_tokens: int = 5,
    ) -> None:
        self.token_delay = token_delay
        self.canned_response = canned_response or self.DEFAULT_CANNED_RESPONSE
        self.simulate_unavailable = simulate_unavailable
        self.simulate_stream_interruption = simulate_stream_interruption
        self.interruption_after_tokens = interruption_after_tokens
        self._current_cancel_token: CancellationToken | None = None

    async def health_check(self) -> bool:
        """Simulate health check without network calls."""
        return not self.simulate_unavailable

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        settings: GenerationSettings | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream canned tokens incrementally with realistic delays."""
        if self.simulate_unavailable:
            raise ProviderError(
                "Mock server simulation: server is unavailable.",
                user_guidance="Disable 'simulate_unavailable' or switch to real server mode in Settings.",
            )

        self._current_cancel_token = cancellation_token or CancellationToken()
        token = self._current_cancel_token

        start_time = time.monotonic()
        yield StreamStartedEvent(model_name="mock-offline-model-v0.1")

        # Split response into individual words/whitespace tokens
        words = self.canned_response.split(" ")
        accumulated: list[str] = []
        token_count = 0

        for i, word in enumerate(words):
            if token.is_cancelled:
                yield StreamErrorEvent(error="Generation cancelled by user.", is_cancelled=True)
                return

            if self.simulate_stream_interruption and i >= self.interruption_after_tokens:
                yield StreamErrorEvent(
                    error="Simulated network stream interruption.",
                    is_cancelled=False,
                )
                return

            # Append whitespace for all but the last word
            token_text = word if i == len(words) - 1 else word + " "
            accumulated.append(token_text)
            token_count += 1

            yield StreamTokenEvent(delta=token_text, token_index=token_count)

            if self.token_delay > 0:
                await asyncio.sleep(self.token_delay)

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        yield StreamCompletedEvent(
            full_text="".join(accumulated),
            total_tokens=token_count,
            duration_ms=elapsed_ms,
        )

    async def generate(
        self,
        messages: list[ChatMessage],
        settings: GenerationSettings | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> GenerationResult:
        """Accumulate tokens and return a complete GenerationResult."""
        accumulated: list[str] = []
        tokens = 0
        cancelled = False
        start = time.monotonic()

        async for event in self.stream_chat(messages, settings, cancellation_token):
            if isinstance(event, StreamTokenEvent):
                accumulated.append(event.delta)
                tokens += 1
            elif isinstance(event, StreamErrorEvent) and event.is_cancelled:
                cancelled = True
                break

        duration_ms = int((time.monotonic() - start) * 1000)
        return GenerationResult(
            text="".join(accumulated),
            total_tokens=tokens,
            duration_ms=duration_ms,
            cancelled=cancelled,
        )

    def cancel(self) -> None:
        """Signal cancellation to active streaming request."""
        if self._current_cancel_token is not None:
            self._current_cancel_token.cancel()

    def provider_metadata(self) -> dict[str, Any]:
        """Return metadata confirming offline mock mode."""
        return {
            "name": "MockLLMProvider",
            "is_mock": True,
            "host": "offline (no network)",
            "model": "mock-qwen-coder-3b",
            "status": "Ready (Offline Demo)",
        }


# Verify protocol conformance at module load time
assert isinstance(MockLLMProvider(), LLMProvider)
