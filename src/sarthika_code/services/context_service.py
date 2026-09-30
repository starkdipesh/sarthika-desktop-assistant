"""Project context service managing explicitly attached user files and context budgets.

Enforces strict read-only access, security filtering, and deterministic prompt formatting.
Zero automatic scanning, recursive inclusion, or file modifications.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from sarthika_code.domain.context import ContextBudget, SelectedFileContext
from sarthika_code.domain.errors import PersistenceError, SensitiveFileError
from sarthika_code.prompts.context_builder import (
    build_file_context_prompt,
    calculate_context_budget,
    estimate_tokens,
)
from sarthika_code.security.file_filter import SensitiveFileFilter, detect_language
from sarthika_code.storage.database import DatabaseManager
from sarthika_code.storage.models import SelectedFileContextModel
from sarthika_code.storage.repositories import SelectedFileContextRepository
from sarthika_code.utils.logging import get_logger

logger = get_logger("ProjectContextService")


class ProjectContextService:
    """Service governing explicit user file selection, read-only inspection, and context budgeting."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        context_repo: SelectedFileContextRepository | None = None,
    ) -> None:
        self.db_manager = db_manager
        self.context_repo = context_repo or SelectedFileContextRepository()

    def add_file(self, chat_id: str, file_path: Path) -> SelectedFileContext:
        """Inspect and attach an explicitly selected local text file as read-only context.

        Args:
            chat_id: Conversation ID to associate with the attached file.
            file_path: Absolute path to the user-selected file.

        Returns:
            Domain representation of the attached file context.

        Raises:
            SensitiveFileError: If the file is blacklisted, binary, or too large.
            PersistenceError: If the database write fails.
        """
        # 1. Run strict security evaluation
        filter_result = SensitiveFileFilter.evaluate_file(file_path)
        if not filter_result.is_safe:
            logger.warning("Rejected sensitive or unsafe file: %s (reason: %s)", file_path, filter_result.reason)
            raise SensitiveFileError(
                message=f"File '{file_path.name}' was blocked: {filter_result.reason}",
                user_guidance="Attach only safe, text-based project source files.",
            )

        # 2. Read file contents safely in read-only mode
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.error("Failed to read file %s: %s", file_path, e)
            raise SensitiveFileError(
                message=f"Could not read '{file_path.name}': {e}",
                user_guidance="Verify the file is a readable text document.",
            ) from e

        byte_size = file_path.stat().st_size
        language = detect_language(file_path)
        lines = content.splitlines()
        line_count = len(lines)
        tokens = estimate_tokens(content)

        # Truncate overly long path for display
        display_name = file_path.name
        context_id = str(uuid.uuid4())

        # 3. Persist record in SQLite
        try:
            with self.db_manager.session() as session:
                model = self.context_repo.create(
                    session=session,
                    context_id=context_id,
                    chat_id=chat_id,
                    file_path=str(file_path.resolve()),
                    display_name=display_name,
                    language=language,
                    content=content,
                    byte_size=byte_size,
                    line_start=1 if line_count > 0 else None,
                    line_end=line_count if line_count > 0 else None,
                )
                logger.info("Attached safe context file '%s' (ID: %s, tokens: ~%d)", display_name, context_id, tokens)
                return self._to_domain_context(model)
        except Exception as e:
            logger.error("Failed to persist file context for chat %s: %s", chat_id, e)
            raise PersistenceError(f"Could not persist attached file context: {e}") from e

    def list_files(self, chat_id: str) -> list[SelectedFileContext]:
        """List all explicitly attached files for a given conversation."""
        try:
            with self.db_manager.session() as session:
                models = self.context_repo.list_by_chat(session, chat_id)
                return [self._to_domain_context(m) for m in models]
        except Exception as e:
            logger.error("Failed to list file contexts for chat %s: %s", chat_id, e)
            raise PersistenceError(f"Could not retrieve attached file contexts: {e}") from e

    def remove_file(self, context_id: str) -> bool:
        """Remove a single attached file context by its ID."""
        try:
            with self.db_manager.session() as session:
                success = self.context_repo.delete(session, context_id)
                if success:
                    logger.info("Removed file context %s", context_id)
                return success
        except Exception as e:
            logger.error("Failed to remove file context %s: %s", context_id, e)
            raise PersistenceError(f"Could not remove file context: {e}") from e

    def clear_files(self, chat_id: str) -> int:
        """Remove all attached files for a conversation."""
        try:
            with self.db_manager.session() as session:
                count = self.context_repo.delete_by_chat(session, chat_id)
                logger.info("Cleared %d file contexts for chat %s", count, chat_id)
                return count
        except Exception as e:
            logger.error("Failed to clear file contexts for chat %s: %s", chat_id, e)
            raise PersistenceError(f"Could not clear file contexts: {e}") from e

    def get_budget(self, chat_id: str, context_limit: int = 4096) -> ContextBudget:
        """Calculate the current context budget metrics for attached files."""
        files = self.list_files(chat_id)
        return calculate_context_budget(files, context_limit=context_limit)

    def build_context_prompt(self, chat_id: str) -> str:
        """Construct the delimited, line-numbered untrusted context string for all attached files."""
        files = self.list_files(chat_id)
        return build_file_context_prompt(files)

    @staticmethod
    def _to_domain_context(m: SelectedFileContextModel) -> SelectedFileContext:
        line_count = len(m.content.splitlines())
        tokens = estimate_tokens(m.content)
        return SelectedFileContext(
            id=m.id,
            chat_id=m.chat_id,
            file_path=m.file_path,
            display_name=m.display_name,
            language=m.language,
            content=m.content,
            byte_size=m.byte_size,
            line_count=line_count,
            estimated_tokens=tokens,
            line_start=m.line_start,
            line_end=m.line_end,
            created_at=m.created_at,
        )
