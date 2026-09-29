"""Domain and application error hierarchy for Sarthika Code.

Provides structured, user-friendly error objects with clear guidance
and actionable remedies, avoiding the display of raw Python stack traces in UI views.
"""

from __future__ import annotations


class SarthikaError(Exception):
    """Base domain exception for all Sarthika Code errors."""

    def __init__(
        self,
        message: str,
        user_guidance: str = "",
        details: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.user_guidance = user_guidance
        self.details = details

    def format_for_user(self) -> str:
        """Format a clear, friendly error string suitable for UI dialogs and notices."""
        parts = [self.message]
        if self.user_guidance:
            parts.append(f"\nHow to fix:\n• {self.user_guidance}")
        return "\n".join(parts)


class ConfigurationError(SarthikaError):
    """Raised when an application or service configuration is missing or invalid."""

    def __init__(
        self,
        message: str,
        user_guidance: str = "Check application Settings and ensure required paths are configured.",
        details: str | None = None,
    ) -> None:
        super().__init__(message, user_guidance, details)


class ModelValidationError(SarthikaError):
    """Raised when a selected GGUF model path or file is missing, invalid, or corrupted."""

    def __init__(
        self,
        message: str,
        user_guidance: str = "Select a valid, readable .gguf model file (e.g. Qwen2.5-Coder 3B Instruct Q4_K_M).",
        details: str | None = None,
    ) -> None:
        super().__init__(message, user_guidance, details)


class ServerError(SarthikaError):
    """Raised when the local llama-server fails to start, crashes, or times out."""

    def __init__(
        self,
        message: str,
        user_guidance: str = "Check that the llama-server executable exists and the local port is not in use. See Diagnostics for log details.",
        details: str | None = None,
    ) -> None:
        super().__init__(message, user_guidance, details)


class ProviderError(SarthikaError):
    """Raised when communication with an LLM provider encounters a transport or protocol error."""

    def __init__(
        self,
        message: str,
        user_guidance: str = "Verify that the local model server is healthy and running at http://127.0.0.1:<port>.",
        details: str | None = None,
    ) -> None:
        super().__init__(message, user_guidance, details)


class PersistenceError(SarthikaError):
    """Raised when a database query, transaction, or migration fails."""

    def __init__(
        self,
        message: str,
        user_guidance: str = "Ensure the database directory is writable. Check Diagnostics for database file status.",
        details: str | None = None,
    ) -> None:
        super().__init__(message, user_guidance, details)


class SensitiveFileError(SarthikaError):
    """Raised when a user attempts to attach a restricted file (e.g. .env, key, credentials)."""

    def __init__(
        self,
        message: str,
        user_guidance: str = "Sensitive files (.env, keys, credentials, node_modules) are blocked by the security policy to protect privacy.",
        details: str | None = None,
    ) -> None:
        super().__init__(message, user_guidance, details)


class ContextLimitError(SarthikaError):
    """Raised when selected file contexts exceed memory or token thresholds."""

    def __init__(
        self,
        message: str,
        user_guidance: str = "Reduce the number of selected files or choose smaller file subsets to prevent memory pressure.",
        details: str | None = None,
    ) -> None:
        super().__init__(message, user_guidance, details)
