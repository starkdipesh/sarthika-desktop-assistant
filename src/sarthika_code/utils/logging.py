"""Safe, structured local logging for Sarthika Code.

This module provides rotating local file logging and formatted console output.
It strictly redacts user home directories and prevents recording complete source files,
conversations, or private credentials.
"""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# Maximum log file size: 5 MB per file, 3 backups (15 MB maximum storage)
MAX_LOG_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3


def _sanitize_path(text: str) -> str:
    """Redact user's home directory from file paths to protect user privacy."""
    try:
        home_str = str(Path.home())
        if home_str in text:
            return text.replace(home_str, "~")
    except Exception:
        pass
    return text


class StructuredFormatter(logging.Formatter):
    """Format log records into structured JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        # Extract structured extra fields if present
        component = getattr(record, "component", record.name)
        event = getattr(record, "event", "GENERAL")

        message = _sanitize_path(record.getMessage())

        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "component": component,
            "event": event,
            "message": message,
        }

        if record.exc_info:
            # Only record exception class and sanitized message, not arbitrary variables
            exc_type, exc_val, _ = record.exc_info
            if exc_type is not None and exc_val is not None:
                log_data["exception"] = f"{exc_type.__name__}: {_sanitize_path(str(exc_val))}"

        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """Format log records into clear human-readable strings for console output."""

    def format(self, record: logging.LogRecord) -> str:
        component = getattr(record, "component", record.name)
        event = getattr(record, "event", "")
        event_str = f" [{event}]" if event else ""
        msg = _sanitize_path(record.getMessage())
        return f"{self.formatTime(record)} | {record.levelname:<7} | {component}{event_str}: {msg}"


def setup_logging(
    log_file_path: Path | None = None,
    level: int = logging.INFO,
    enable_console: bool = True,
) -> logging.Logger:
    """Initialize structured rotating file logging and console handlers."""
    root_logger = logging.getLogger("sarthika_code")
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(
            HumanReadableFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        )
        root_logger.addHandler(console_handler)

    # Rotating file handler
    if log_file_path is not None:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=str(log_file_path),
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(
            StructuredFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z")
        )
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(component_name: str) -> logging.LoggerAdapter:
    """Get a component-scoped logger adapter."""
    base_logger = logging.getLogger(f"sarthika_code.{component_name}")
    return logging.LoggerAdapter(base_logger, {"component": component_name})
