"""Domain models for conversations, messages, and title derivation in Sarthika Code.

Provides clean representations decoupled from database ORM models and UI widgets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """Domain representation of a chat message turn."""

    id: str
    chat_id: str
    role: str  # 'system', 'user', 'assistant'
    content: str
    token_count: int | None = None
    generation_duration_ms: int | None = None
    created_at: datetime | None = None
    is_streaming: bool = False
    is_cancelled: bool = False


@dataclass
class Chat:
    """Domain representation of a conversation session."""

    id: str
    title: str = "New Chat"
    workflow: str = "general_chat"
    model_name: str = ""
    model_path: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    messages: list[Message] = field(default_factory=list)


def derive_chat_title(first_prompt: str, max_words: int = 6, max_chars: int = 40) -> str:
    """Derive a short, clean local title from the user's first prompt without LLM calls.

    Strict rules:
    - Never calls external APIs or local models.
    - Strips markdown formatting, excess whitespace, and punctuation.
    - Limits to max_words and max_chars.
    - Fallbacks to 'New Chat' if prompt is empty or pure punctuation.
    """
    if not first_prompt or not first_prompt.strip():
        return "New Chat"

    # Iterate lines to find the first line containing non-fence text
    candidate_line = ""
    for line in first_prompt.strip().splitlines():
        line_stripped = line.strip()
        # Skip pure code block fences like ``` or ```python
        if line_stripped.startswith("```"):
            rest = line_stripped.lstrip("`").strip()
            common_langs = (
                "python", "py", "javascript", "js", "typescript", "ts",
                "html", "css", "c", "cpp", "bash", "sh", "json", "sql", "rust", "go", "java",
            )
            if not rest or rest.lower() in common_langs:
                continue
            line_stripped = rest

        cleaned = re.sub(r"[`#*_\-\"\']", "", line_stripped)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            candidate_line = cleaned
            break

    if not candidate_line:
        return "New Chat"

    words = candidate_line.split(" ")
    chosen_words: list[str] = []
    current_len = 0

    for word in words:
        if len(chosen_words) >= max_words:
            break
        added_len = len(word) if not chosen_words else len(word) + 1
        if current_len + added_len > max_chars:
            break
        chosen_words.append(word)
        current_len += added_len

    title = words[0][:max_chars] if not chosen_words else " ".join(chosen_words)

    title = title.rstrip(".,;:-!? ")

    if not title:
        return "New Chat"

    # Capitalize first letter
    return title[0].upper() + title[1:]
