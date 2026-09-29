"""Unit tests for domain and application error types."""

from __future__ import annotations

from sarthika_code.domain.errors import (
    ConfigurationError,
    ContextLimitError,
    ModelValidationError,
    PersistenceError,
    ProviderError,
    SarthikaError,
    SensitiveFileError,
    ServerError,
)


def test_base_sarthika_error_formatting() -> None:
    """Verify that SarthikaError formats clean user-facing guidance."""
    err = SarthikaError(
        message="An unexpected issue occurred.",
        user_guidance="Restart the application.",
        details="Internal socket reset",
    )
    user_msg = err.format_for_user()
    assert "An unexpected issue occurred." in user_msg
    assert "How to fix:" in user_msg
    assert "• Restart the application." in user_msg
    # Raw details should not be in the primary user message
    assert "Internal socket reset" not in user_msg


def test_configuration_error() -> None:
    """Verify ConfigurationError properties."""
    err = ConfigurationError("Port 80 is restricted.")
    assert "Port 80 is restricted." in err.format_for_user()
    assert "Settings" in err.user_guidance


def test_model_validation_error() -> None:
    """Verify ModelValidationError properties."""
    err = ModelValidationError("File is not a valid GGUF binary.")
    assert ".gguf" in err.user_guidance


def test_server_error() -> None:
    """Verify ServerError properties."""
    err = ServerError("llama-server failed to bind to port 8080.")
    assert "Diagnostics" in err.user_guidance


def test_provider_error() -> None:
    """Verify ProviderError properties."""
    err = ProviderError("Connection refused at 127.0.0.1:8080.")
    assert "127.0.0.1" in err.user_guidance


def test_persistence_error() -> None:
    """Verify PersistenceError properties."""
    err = PersistenceError("Disk I/O error on database write.")
    assert "database directory" in err.user_guidance


def test_sensitive_file_error() -> None:
    """Verify SensitiveFileError properties."""
    err = SensitiveFileError("File '.env' is blocked.")
    assert ".env" in err.user_guidance


def test_context_limit_error() -> None:
    """Verify ContextLimitError properties."""
    err = ContextLimitError("Total prompt characters exceeds 16,000.")
    assert "Reduce the number of selected files" in err.user_guidance
