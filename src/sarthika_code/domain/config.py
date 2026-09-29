"""Domain settings, model configuration, and generation settings for Sarthika Code.

Defines typed representations of user preferences, model attributes, and server parameters.
Strictly avoids storing secrets or sensitive credentials.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AppSettings:
    """Core persistent application preferences."""

    theme: str = "dark"  # 'dark', 'light', or 'system'
    model_path: str | None = None  # Absolute path to selected .gguf file
    llama_server_path: str | None = None  # Absolute path to llama-server binary
    server_host: str = "127.0.0.1"  # Localhost loopback only
    server_port: int = 8080  # Default port
    context_size: int = 4096  # Context window in tokens (2048 low-memory, 4096 standard)
    mock_mode: bool = False  # Offline mock/demo mode
    threads: int = 4  # Inference CPU threads

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to a serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppSettings:
        """Create AppSettings safely from dictionary data with sensible fallbacks."""
        return cls(
            theme=str(data.get("theme", "dark")),
            model_path=data.get("model_path"),
            llama_server_path=data.get("llama_server_path"),
            server_host=str(data.get("server_host", "127.0.0.1")),
            server_port=int(data.get("server_port", 8080)),
            context_size=int(data.get("context_size", 4096)),
            mock_mode=bool(data.get("mock_mode", False)),
            threads=int(data.get("threads", 4)),
        )


@dataclass(frozen=True)
class ModelConfiguration:
    """Configuration parameters required to validate and launch a local GGUF model."""

    model_path: str
    model_name: str
    model_size_bytes: int
    executable_path: str
    context_size: int = 4096
    threads: int = 4
    host: str = "127.0.0.1"
    port: int = 8080
    quantization: str = "Unknown"  # Unknown until confirmed by server/model metadata probe


@dataclass(frozen=True)
class GenerationSettings:
    """Parameters passed to the model during token generation."""

    temperature: float = 0.3
    top_p: float = 0.8
    max_tokens: int = 2048
    repeat_penalty: float = 1.1
    stop_tokens: list[str] = field(default_factory=lambda: ["<|im_end|>", "<|endoftext|>"])
