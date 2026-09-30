"""Domain models for user-selected file contexts and context budget calculations.

Completely decoupled from database ORM and GUI components.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SelectedFileContext:
    """Domain representation of an explicitly user-selected source file."""

    id: str
    chat_id: str
    file_path: str
    display_name: str
    language: str
    content: str
    byte_size: int
    line_count: int
    estimated_tokens: int
    line_start: int | None = None
    line_end: int | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class ContextBudget:
    """Calculated token budget and capacity metrics for attached project files."""

    total_files: int
    total_characters: int
    total_tokens: int
    context_limit: int
    usage_percentage: float
    status: str  # 'safe', 'warning', 'critical', 'exceeded'
    warning_message: str | None = None

    @property
    def is_safe(self) -> bool:
        """Return True if total tokens are within safe operating limits (<80%)."""
        return self.status in ("safe", "warning")

    @property
    def is_exceeded(self) -> bool:
        """Return True if total tokens exceed 100% of the target context limit."""
        return self.status == "exceeded"
