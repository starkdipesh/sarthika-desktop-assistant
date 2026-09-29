"""Unit tests for safe structured local logging."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sarthika_code.utils.logging import (
    HumanReadableFormatter,
    _sanitize_path,
    get_logger,
    setup_logging,
)


def test_sanitize_path_redacts_home(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that user home directory is redacted to ~."""
    home = Path.home()
    test_str = f"Reading file from {home}/projects/secret.py"
    sanitized = _sanitize_path(test_str)
    assert str(home) not in sanitized
    assert "~/projects/secret.py" in sanitized


def test_structured_logging_output(tmp_path: Path) -> None:
    """Verify that structured logging writes valid JSON lines with expected fields."""
    log_file = tmp_path / "test.log"
    logger = setup_logging(log_file_path=log_file, enable_console=False)

    component_logger = get_logger("TestComponent")
    component_logger.info("Application started successfully.")

    # Flush handlers
    for handler in logger.handlers:
        handler.flush()

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8").strip()
    assert content

    # Parse JSON
    log_entry = json.loads(content.splitlines()[-1])
    assert log_entry["level"] == "INFO"
    assert log_entry["component"] == "TestComponent"
    assert "Application started successfully." in log_entry["message"]
    assert "timestamp" in log_entry


def test_human_readable_formatter() -> None:
    """Verify human readable formatter layout."""
    import logging

    formatter = HumanReadableFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.WARNING,
        pathname="test.py",
        lineno=10,
        msg="Warning message",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "WARNING" in formatted
    assert "Warning message" in formatted
