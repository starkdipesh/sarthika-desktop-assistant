"""Real local llama-server LLMProvider implementation using httpx.

Communicates strictly over localhost loopback (127.0.0.1) with async SSE streaming,
cancellation support, and user-friendly error translation.
"""

from __future__ import annotations

import contextlib
import json
import time
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse

import httpx

from sarthika_code.domain.config import GenerationSettings
from sarthika_code.domain.errors import ConfigurationError, ProviderError
from sarthika_code.domain.server import ServerState
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
from sarthika_code.llm.manager import LlamaServerManager
from sarthika_code.utils.logging import get_logger

logger = get_logger("LlamaCppProvider")

# Timeouts configured for slow CPU token generation
DEFAULT_CONNECT_TIMEOUT = 5.0
DEFAULT_READ_TIMEOUT = 180.0


class LlamaCppProvider:
    """LLMProvider communicating with a local llama-server via HTTP Server-Sent Events."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        server_manager: LlamaServerManager | None = None,
        model_name: str = "qwen2.5-coder-3b",
    ) -> None:
        self.base_url = self._validate_and_normalize_url(base_url)
        self.server_manager = server_manager
        self.model_name = model_name
        self._current_cancel_token: CancellationToken | None = None
        self._active_stream: httpx.Response | None = None

    @staticmethod
    def _validate_and_normalize_url(url: str) -> str:
        """Enforce strict local loopback binding policy."""
        clean_url = url.rstrip("/")
        parsed = urlparse(clean_url)
        hostname = (parsed.hostname or "").lower()

        if hostname not in ("127.0.0.1", "localhost"):
            raise ConfigurationError(
                f"Forbidden endpoint '{url}'. Sarthika Code strictly prohibits connecting to non-loopback addresses.",
                user_guidance="Only local servers on 127.0.0.1 or localhost are allowed to preserve privacy.",
            )
        return clean_url

    async def health_check(self) -> bool:
        """Query llama-server /health endpoint."""
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_CONNECT_TIMEOUT) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception as e:
            logger.debug("Health check failed on %s: %s", self.base_url, e)
            return False

    def _build_request_payload(
        self,
        messages: list[ChatMessage],
        settings: GenerationSettings | None,
    ) -> dict[str, Any]:
        """Construct an OpenAI-compatible payload tailored for llama-server."""
        gen_settings = settings or GenerationSettings()

        formatted_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        return {
            "model": self.model_name,
            "messages": formatted_messages,
            "temperature": gen_settings.temperature,
            "top_p": gen_settings.top_p,
            "max_tokens": gen_settings.max_tokens,
            "repeat_penalty": gen_settings.repeat_penalty,
            "stop": gen_settings.stop_tokens,
            "stream": True,
            "cache_prompt": True,
        }

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        settings: GenerationSettings | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream chat completions from localhost llama-server via SSE."""
        self._current_cancel_token = cancellation_token or CancellationToken()
        token = self._current_cancel_token
        payload = self._build_request_payload(messages, settings)

        # Notify server manager of generating state if managed
        if self.server_manager is not None and self.server_manager.status.state == ServerState.READY:
            with contextlib.suppress(Exception):
                self.server_manager._set_status(ServerState.GENERATING, "Generating response...")

        start_time = time.monotonic()
        yield StreamStartedEvent(model_name=self.model_name)

        endpoint = f"{self.base_url}/v1/chat/completions"
        accumulated: list[str] = []
        token_count = 0

        timeout = httpx.Timeout(
            connect=DEFAULT_CONNECT_TIMEOUT,
            read=DEFAULT_READ_TIMEOUT,
            write=10.0,
            pool=10.0,
        )

        try:
            async with (
                httpx.AsyncClient(timeout=timeout) as client,
                client.stream("POST", endpoint, json=payload) as response,
            ):
                self._active_stream = response

                if response.status_code != 200:
                    error_body = await response.aread()
                    error_text = error_body.decode("utf-8", errors="replace")
                    raise ProviderError(
                        f"llama-server returned HTTP {response.status_code}: {error_text}",
                        user_guidance="Check server context size limits or Diagnostics for details.",
                    )

                async for line in response.aiter_lines():
                    if token.is_cancelled:
                        logger.info("Generation cancellation detected during SSE stream.")
                        yield StreamErrorEvent(error="Generation cancelled by user.", is_cancelled=True)
                        return

                    line_str = line.strip()
                    if not line_str or not line_str.startswith("data:"):
                        continue

                    data_content = line_str[len("data:") :].strip()
                    if data_content == "[DONE]":
                        break

                    try:
                        parsed_chunk = json.loads(data_content)
                        choices = parsed_chunk.get("choices", [])
                        if not choices:
                            continue

                        delta = choices[0].get("delta", {})
                        content_piece = delta.get("content", "")

                        if content_piece:
                            token_count += 1
                            accumulated.append(content_piece)
                            yield StreamTokenEvent(delta=content_piece, token_index=token_count)

                    except json.JSONDecodeError:
                        continue

        except httpx.ConnectError as e:
            logger.error("Connection failed to llama-server at %s: %s", self.base_url, e)
            yield StreamErrorEvent(
                error=f"Could not connect to local model server at {self.base_url}.",
                is_cancelled=False,
            )
            return

        except httpx.TimeoutException as e:
            logger.error("Timeout during stream from llama-server: %s", e)
            yield StreamErrorEvent(
                error="llama-server timed out while generating tokens.",
                is_cancelled=False,
            )
            return

        except Exception as e:
            logger.error("Unexpected error during stream: %s", e)
            yield StreamErrorEvent(
                error=f"Stream error: {e}",
                is_cancelled=False,
            )
            return

        finally:
            self._active_stream = None
            # Return server state back to READY
            if self.server_manager is not None and self.server_manager.status.state == ServerState.GENERATING:
                with contextlib.suppress(Exception):
                    self.server_manager._set_status(ServerState.READY, f"Model Ready ({self.model_name})")

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
        """Accumulate streamed tokens and return a GenerationResult."""
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
        """Signal immediate cancellation of active in-flight generation."""
        if self._current_cancel_token is not None:
            self._current_cancel_token.cancel()

        if self._active_stream is not None:
            with contextlib.suppress(Exception):
                # Force close active response stream
                self._active_stream.close()

    def provider_metadata(self) -> dict[str, Any]:
        """Return provider operational metadata."""
        return {
            "name": "LlamaCppProvider",
            "is_mock": False,
            "host": self.base_url,
            "model": self.model_name,
            "status": "Online (Localhost)",
        }


# Verify protocol conformance at module load time
assert isinstance(LlamaCppProvider(), LLMProvider)
