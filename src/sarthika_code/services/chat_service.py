"""Chat application service for Sarthika Code.

Coordinates conversation lifecycle, message persistence, title derivation,
streaming generation via LLMProvider, and safe Markdown/Plaintext export.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from sarthika_code.domain.chat import Chat, Message, derive_chat_title
from sarthika_code.domain.config import GenerationSettings
from sarthika_code.domain.errors import PersistenceError
from sarthika_code.llm.base import (
    CancellationToken,
    ChatMessage,
    LLMProvider,
    StreamCompletedEvent,
    StreamErrorEvent,
    StreamEvent,
    StreamStartedEvent,
    StreamTokenEvent,
)
from sarthika_code.storage.database import DatabaseManager
from sarthika_code.storage.models import ChatModel, MessageModel
from sarthika_code.storage.repositories import ChatRepository, MessageRepository
from sarthika_code.utils.logging import get_logger

logger = get_logger("ChatService")

DEFAULT_SYSTEM_PROMPT = (
    "You are Sarthika Code, a private, local-first AI coding assistant running entirely on the user's computer. "
    "Provide clear, accurate, and concise code explanations, debugging advice, and implementations. "
    "Never claim to execute code, run terminal commands, or modify files directly."
)


class ChatService:
    """Service governing chat sessions, message histories, streaming, and exports."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        chat_repo: ChatRepository | None = None,
        message_repo: MessageRepository | None = None,
    ) -> None:
        self.db_manager = db_manager
        self.chat_repo = chat_repo or ChatRepository()
        self.message_repo = message_repo or MessageRepository()

    # --------------------------------------------------------------------------
    # Chat Lifecycle
    # --------------------------------------------------------------------------

    def create_chat(
        self,
        title: str = "New Chat",
        workflow: str = "general_chat",
        model_name: str = "",
        model_path: str = "",
    ) -> Chat:
        """Create a new chat conversation session."""
        chat_id = str(uuid.uuid4())
        try:
            with self.db_manager.session() as session:
                chat_model = self.chat_repo.create(
                    session=session,
                    chat_id=chat_id,
                    title=title,
                    workflow=workflow,
                    model_name=model_name,
                    model_path=model_path,
                )
                logger.info("Created new chat '%s' (ID: %s)", title, chat_id)
                return self._to_domain_chat(chat_model, load_messages=False)
        except Exception as e:
            logger.error("Failed to create chat: %s", e)
            raise PersistenceError(
                f"Could not create chat session: {e}",
                user_guidance="Check local database file permissions.",
            ) from e

    def get_chat(self, chat_id: str) -> Chat | None:
        """Load an existing chat and all its chronological messages."""
        try:
            with self.db_manager.session() as session:
                chat_model = self.chat_repo.get(session, chat_id)
                if chat_model is None:
                    return None
                return self._to_domain_chat(chat_model, load_messages=True)
        except Exception as e:
            logger.error("Failed to load chat %s: %s", chat_id, e)
            raise PersistenceError(f"Could not retrieve chat: {e}") from e

    def list_chats(self) -> list[Chat]:
        """List all chats ordered by most recently updated."""
        try:
            with self.db_manager.session() as session:
                models = self.chat_repo.list_chats(session)
                return [self._to_domain_chat(m, load_messages=False) for m in models]
        except Exception as e:
            logger.error("Failed to list chats: %s", e)
            raise PersistenceError(f"Could not load conversation history: {e}") from e

    def rename_chat(self, chat_id: str, new_title: str) -> bool:
        """Rename an existing conversation."""
        clean_title = new_title.strip() or "Untitled Chat"
        try:
            with self.db_manager.session() as session:
                success = self.chat_repo.update_title(session, chat_id, clean_title)
                if success:
                    logger.info("Renamed chat %s to '%s'", chat_id, clean_title)
                return success
        except Exception as e:
            logger.error("Failed to rename chat %s: %s", chat_id, e)
            raise PersistenceError(f"Could not rename chat: {e}") from e

    def delete_chat(self, chat_id: str) -> bool:
        """Permanently delete a conversation and its messages/contexts."""
        try:
            with self.db_manager.session() as session:
                success = self.chat_repo.delete(session, chat_id)
                if success:
                    logger.info("Deleted chat %s and associated records.", chat_id)
                return success
        except Exception as e:
            logger.error("Failed to delete chat %s: %s", chat_id, e)
            raise PersistenceError(f"Could not delete conversation: {e}") from e

    # --------------------------------------------------------------------------
    # Message Persistence
    # --------------------------------------------------------------------------

    def add_user_message(self, chat_id: str, content: str) -> Message:
        """Persist a user message and conditionally derive a concise local chat title."""
        msg_id = str(uuid.uuid4())
        try:
            with self.db_manager.session() as session:
                chat = self.chat_repo.get(session, chat_id)
                if chat is None:
                    raise PersistenceError(f"Chat {chat_id} does not exist.")

                # If this chat is titled 'New Chat' or 'New Conversation', derive title locally
                if chat.title in ("New Chat", "New Conversation"):
                    derived = derive_chat_title(content)
                    chat.title = derived
                    logger.info("Auto-derived local chat title: '%s'", derived)

                msg_model = self.message_repo.create(
                    session=session,
                    message_id=msg_id,
                    chat_id=chat_id,
                    role="user",
                    content=content,
                )
                self.chat_repo.touch(session, chat_id)
                return self._to_domain_message(msg_model)
        except PersistenceError:
            raise
        except Exception as e:
            logger.error("Failed to persist user message in %s: %s", chat_id, e)
            raise PersistenceError(f"Could not save user message: {e}") from e

    def create_assistant_placeholder(self, chat_id: str) -> Message:
        """Create an initial empty assistant message placeholder to store streamed output."""
        msg_id = str(uuid.uuid4())
        try:
            with self.db_manager.session() as session:
                chat = self.chat_repo.get(session, chat_id)
                if chat is None:
                    raise PersistenceError(f"Chat {chat_id} does not exist.")

                msg_model = self.message_repo.create(
                    session=session,
                    message_id=msg_id,
                    chat_id=chat_id,
                    role="assistant",
                    content="",
                )
                return self._to_domain_message(msg_model)
        except PersistenceError:
            raise
        except Exception as e:
            logger.error("Failed to create assistant placeholder: %s", e)
            raise PersistenceError(f"Could not initialize assistant message: {e}") from e

    def update_assistant_message(
        self,
        message_id: str,
        content: str,
        token_count: int | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Update content, tokens, and duration of an assistant response."""
        try:
            with self.db_manager.session() as session:
                self.message_repo.update_content(
                    session=session,
                    message_id=message_id,
                    content=content,
                    token_count=token_count,
                    generation_duration_ms=duration_ms,
                )
                msg = self.message_repo.get(session, message_id)
                if msg is not None:
                    self.chat_repo.touch(session, msg.chat_id)
        except Exception as e:
            logger.error("Failed to update assistant message %s: %s", message_id, e)

    def retry_last_message(self, chat_id: str) -> tuple[str, Message] | None:
        """Delete last assistant response and prepare a new assistant turn for the last user prompt."""
        try:
            with self.db_manager.session() as session:
                user_msg = self.message_repo.delete_last_assistant_and_get_user_message(session, chat_id)
                if user_msg is None:
                    return None

                prompt_content = user_msg.content

            # Create new assistant placeholder
            new_assistant_msg = self.create_assistant_placeholder(chat_id)
            return prompt_content, new_assistant_msg
        except Exception as e:
            logger.error("Failed to retry message in chat %s: %s", chat_id, e)
            raise PersistenceError(f"Could not retry prompt: {e}") from e

    # --------------------------------------------------------------------------
    # Streaming Generation Orchestration
    # --------------------------------------------------------------------------

    async def stream_chat_turn(
        self,
        chat_id: str,
        assistant_message_id: str,
        provider: LLMProvider,
        settings: GenerationSettings | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream token events from LLMProvider while safely checkpointing to SQLite.

        Guarantees:
        - Never executes model output or shell commands.
        - Safely updates database on partial tokens, completions, or cancellations.
        - Preserves partial tokens if interrupted or cancelled.
        """
        # Load conversation history up to the current turn
        with self.db_manager.session() as session:
            raw_messages = self.message_repo.list_by_chat(session, chat_id)

        # Filter out current placeholder
        history = [m for m in raw_messages if m.id != assistant_message_id]

        chat_messages: list[ChatMessage] = []
        # Prepend system prompt if not present
        if not history or history[0].role != "system":
            chat_messages.append(ChatMessage(role="system", content=DEFAULT_SYSTEM_PROMPT))

        for m in history:
            chat_messages.append(ChatMessage(role=m.role, content=m.content))

        accumulated_chunks: list[str] = []
        token_count = 0
        last_checkpoint_time = time.monotonic()
        start_time = time.monotonic()

        try:
            async for event in provider.stream_chat(
                messages=chat_messages,
                settings=settings,
                cancellation_token=cancellation_token,
            ):
                if isinstance(event, StreamStartedEvent):
                    yield event

                elif isinstance(event, StreamTokenEvent):
                    accumulated_chunks.append(event.delta)
                    token_count += 1
                    yield event

                    # Checkpoint to SQLite every 2 seconds or 20 tokens to guarantee persistence on crash
                    now = time.monotonic()
                    if token_count % 20 == 0 or (now - last_checkpoint_time) > 2.0:
                        self.update_assistant_message(
                            assistant_message_id,
                            "".join(accumulated_chunks),
                            token_count=token_count,
                            duration_ms=int((now - start_time) * 1000),
                        )
                        last_checkpoint_time = now

                elif isinstance(event, StreamCompletedEvent):
                    full_text = "".join(accumulated_chunks)
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)
                    self.update_assistant_message(
                        assistant_message_id,
                        full_text,
                        token_count=token_count,
                        duration_ms=elapsed_ms,
                    )
                    yield StreamCompletedEvent(
                        full_text=full_text,
                        total_tokens=token_count,
                        duration_ms=elapsed_ms,
                    )

                elif isinstance(event, StreamErrorEvent):
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)
                    partial_text = "".join(accumulated_chunks)
                    if event.is_cancelled:
                        if partial_text:
                            partial_text += "\n\n*[Generation stopped by user]*"
                        else:
                            partial_text = "*[Generation stopped by user]*"

                    self.update_assistant_message(
                        assistant_message_id,
                        partial_text,
                        token_count=token_count,
                        duration_ms=elapsed_ms,
                    )
                    yield event

        except Exception as e:
            logger.error("Error during streaming generation for message %s: %s", assistant_message_id, e)
            partial_text = "".join(accumulated_chunks)
            if not partial_text:
                partial_text = f"*[Generation failed: {e}]*"
            self.update_assistant_message(
                assistant_message_id,
                partial_text,
                token_count=token_count,
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )
            yield StreamErrorEvent(error=str(e), is_cancelled=False)

    # --------------------------------------------------------------------------
    # Export Handling
    # --------------------------------------------------------------------------

    def export_chat_markdown(self, chat_id: str) -> str:
        """Export conversation as safe Markdown, omitting raw logs, DB paths, and secrets."""
        chat = self.get_chat(chat_id)
        if chat is None:
            raise PersistenceError(f"Cannot export non-existent chat {chat_id}")

        export_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        model_name = chat.model_name or "Local Model"

        lines = [
            f"# {chat.title}",
            "",
            f"**Exported:** {export_time}  ",
            f"**Workflow:** {chat.workflow}  ",
            f"**Model:** {model_name}  ",
            "",
            "---",
            "",
        ]

        for msg in chat.messages:
            role_header = "User" if msg.role == "user" else "Assistant"
            if msg.role == "system":
                role_header = "System Instructions"

            time_str = msg.created_at.strftime("%H:%M:%S") if msg.created_at else ""
            lines.append(f"### {role_header} ({time_str})")
            lines.append("")
            lines.append(msg.content.strip())
            lines.append("")

        return "\n".join(lines)

    def export_chat_text(self, chat_id: str) -> str:
        """Export conversation as clean plain text."""
        chat = self.get_chat(chat_id)
        if chat is None:
            raise PersistenceError(f"Cannot export non-existent chat {chat_id}")

        export_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            "=" * 60,
            f"SARTHIKA CODE — CONVERSATION EXPORT: {chat.title}",
            f"Date: {export_time}",
            "=" * 60,
            "",
        ]

        for msg in chat.messages:
            role_header = f"[{msg.role.upper()}]"
            lines.append(f"{role_header}")
            lines.append("-" * 40)
            lines.append(msg.content.strip())
            lines.append("")

        return "\n".join(lines)

    def export_chat_to_file(self, chat_id: str, file_path: Path, file_format: str = "markdown") -> None:
        """Write exported chat content to target file path."""
        if file_format.lower() == "markdown" or file_path.suffix.lower() == ".md":
            content = self.export_chat_markdown(chat_id)
        else:
            content = self.export_chat_text(chat_id)

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        logger.info("Exported chat %s to %s", chat_id, file_path)

    # --------------------------------------------------------------------------
    # Helper Mappers
    # --------------------------------------------------------------------------

    @staticmethod
    def _to_domain_message(m: MessageModel) -> Message:
        return Message(
            id=m.id,
            chat_id=m.chat_id,
            role=m.role,
            content=m.content,
            token_count=m.token_count,
            generation_duration_ms=m.generation_duration_ms,
            created_at=m.created_at,
        )

    def _to_domain_chat(self, c: ChatModel, load_messages: bool = False) -> Chat:
        messages: list[Message] = []
        if load_messages and c.messages:
            messages = [self._to_domain_message(m) for m in c.messages]

        return Chat(
            id=c.id,
            title=c.title,
            workflow=c.workflow,
            model_name=c.model_name,
            model_path=c.model_path,
            created_at=c.created_at,
            updated_at=c.updated_at,
            messages=messages,
        )
