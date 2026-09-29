"""Main chat workspace orchestrating conversation view, streaming worker, and input controls.

Decouples GUI events from async provider generation through a dedicated QThread worker.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.domain.chat import Chat, Message
from sarthika_code.domain.config import GenerationSettings
from sarthika_code.domain.server import ServerState
from sarthika_code.llm.base import (
    CancellationToken,
    LLMProvider,
    StreamCompletedEvent,
    StreamErrorEvent,
    StreamStartedEvent,
    StreamTokenEvent,
)
from sarthika_code.llm.factory import LLMProviderFactory
from sarthika_code.services.chat_service import ChatService
from sarthika_code.services.model_service import ModelService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.ui.chat.chat_input_bar import ChatInputBar
from sarthika_code.ui.chat.message_widget import MessageWidget
from sarthika_code.utils.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger("ChatWorkspace")


class ChatStreamWorker(QObject):
    """Background worker executing async streaming generation off the Qt GUI thread."""

    token_received = Signal(str)
    started = Signal(str)
    completed = Signal(str, int, int)  # full_text, tokens, duration_ms
    cancelled = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        chat_service: ChatService,
        chat_id: str,
        assistant_message_id: str,
        provider: LLMProvider,
        settings: GenerationSettings,
        cancellation_token: CancellationToken,
    ) -> None:
        super().__init__()
        self.chat_service = chat_service
        self.chat_id = chat_id
        self.assistant_message_id = assistant_message_id
        self.provider = provider
        self.settings = settings
        self.cancellation_token = cancellation_token

    def run(self) -> None:
        """Run async streaming loop inside background thread."""
        try:
            asyncio.run(self._run_stream())
        except Exception as e:
            logger.error("Exception in ChatStreamWorker: %s", e)
            self.error_occurred.emit(str(e))

    async def _run_stream(self) -> None:
        try:
            async for event in self.chat_service.stream_chat_turn(
                chat_id=self.chat_id,
                assistant_message_id=self.assistant_message_id,
                provider=self.provider,
                settings=self.settings,
                cancellation_token=self.cancellation_token,
            ):
                if isinstance(event, StreamStartedEvent):
                    self.started.emit(event.model_name or "Local Model")
                elif isinstance(event, StreamTokenEvent):
                    self.token_received.emit(event.delta)
                elif isinstance(event, StreamCompletedEvent):
                    self.completed.emit(
                        event.full_text,
                        event.total_tokens or 0,
                        event.duration_ms or 0,
                    )
                elif isinstance(event, StreamErrorEvent):
                    if event.is_cancelled:
                        self.cancelled.emit()
                    else:
                        self.error_occurred.emit(event.error)
        except Exception as e:
            logger.error("Unexpected error in _run_stream: %s", e)
            self.error_occurred.emit(str(e))


class ChatWorkspace(QWidget):
    """Central conversation workspace displaying message history and active streaming bubble."""

    chat_title_updated = Signal(str, str)  # chat_id, new_title
    export_requested = Signal(str)  # chat_id

    def __init__(
        self,
        chat_service: ChatService,
        settings_service: SettingsService,
        model_service: ModelService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.chat_service = chat_service
        self.settings_service = settings_service
        self.model_service = model_service
        self.active_chat: Chat | None = None

        self._current_cancel_token: CancellationToken | None = None
        self._worker_thread: QThread | None = None
        self._worker: ChatStreamWorker | None = None
        self._active_stream_widget: MessageWidget | None = None
        self._stream_accumulated_text = ""

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet(
            "background-color: #0b1120; border-bottom: 1px solid #1e293b; padding: 6px 16px;"
        )
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(12, 6, 12, 6)

        self.lbl_chat_title = QLabel("Select or start a conversation")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.lbl_chat_title.setFont(title_font)
        self.lbl_chat_title.setStyleSheet("color: #f8fafc;")
        header_layout.addWidget(self.lbl_chat_title)

        header_layout.addStretch()

        self.btn_export = QPushButton("Export Chat...")
        self.btn_export.setStyleSheet(
            "background-color: #1e293b; color: #94a3b8; font-size: 11px; padding: 4px 10px; border-radius: 4px;"
        )
        self.btn_export.clicked.connect(self._on_export_clicked)
        self.btn_export.setEnabled(False)
        header_layout.addWidget(self.btn_export)

        main_layout.addWidget(self.header_frame)

        # Scroll area for messages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: #030712; border: none; }")

        self.message_container = QWidget()
        self.message_container.setStyleSheet("background-color: #030712;")
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setContentsMargins(16, 16, 16, 16)
        self.message_layout.setSpacing(12)
        self.message_layout.addStretch()

        self.scroll_area.setWidget(self.message_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        # Input bar
        self.input_bar = ChatInputBar()
        self.input_bar.submit_requested.connect(self.send_message)
        self.input_bar.cancel_requested.connect(self.cancel_generation)
        self.input_bar.retry_requested.connect(self.retry_last_message)
        main_layout.addWidget(self.input_bar)

    def load_chat(self, chat_id: str) -> None:
        """Load conversation messages into view."""
        self.active_chat = self.chat_service.get_chat(chat_id)
        if self.active_chat is None:
            self.lbl_chat_title.setText("Conversation not found")
            self.btn_export.setEnabled(False)
            return

        self.lbl_chat_title.setText(self.active_chat.title)
        self.btn_export.setEnabled(True)
        self._clear_messages()

        settings = self.settings_service.load_settings()
        for msg in self.active_chat.messages:
            self._add_message_widget(msg, is_mock=settings.mock_mode)

        self._scroll_to_bottom()

    def _clear_messages(self) -> None:
        while self.message_layout.count() > 1:
            item = self.message_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def _add_message_widget(self, message: Message, is_mock: bool = False) -> MessageWidget:
        widget = MessageWidget(message, is_mock_mode=is_mock)
        widget.retry_requested.connect(self.retry_last_message)
        # Insert before final stretch
        self.message_layout.insertWidget(self.message_layout.count() - 1, widget)
        return widget

    def _scroll_to_bottom(self) -> None:
        # Schedule vertical scrollbar update on next GUI tick
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def send_message(self, prompt: str) -> None:
        """Submit a user prompt and initiate background streaming generation."""
        if not self.active_chat:
            # Create a new chat if none is selected
            new_chat = self.chat_service.create_chat()
            self.active_chat = new_chat
            self.chat_title_updated.emit(new_chat.id, new_chat.title)

        chat_id = self.active_chat.id
        settings = self.settings_service.load_settings()

        # Check server readiness if not in mock mode
        if (
            not settings.mock_mode
            and self.model_service is not None
            and self.model_service.get_status().state != ServerState.READY
        ):
            QMessageBox.warning(
                self,
                "Model Server Offline",
                "The local model server is not currently running.\n\n"
                "Please start llama-server from 'Model & Server Setup', "
                "or enable Offline Mock Mode for UI testing.",
            )
            return

        # 1. Persist and render user message
        user_msg = self.chat_service.add_user_message(chat_id, prompt)
        self._add_message_widget(user_msg, is_mock=settings.mock_mode)

        # Update title in header if auto-derived
        reloaded = self.chat_service.get_chat(chat_id)
        if reloaded and reloaded.title != self.lbl_chat_title.text():
            self.lbl_chat_title.setText(reloaded.title)
            self.chat_title_updated.emit(chat_id, reloaded.title)

        # 2. Create assistant message placeholder
        asst_msg = self.chat_service.create_assistant_placeholder(chat_id)
        self._active_stream_widget = self._add_message_widget(asst_msg, is_mock=settings.mock_mode)
        self._stream_accumulated_text = ""
        self._scroll_to_bottom()

        # 3. Resolve LLM provider
        server_mgr = self.model_service.server_manager if self.model_service is not None else None
        provider = LLMProviderFactory.create_provider(settings, server_mgr)

        # 4. Launch background stream worker
        self._current_cancel_token = CancellationToken()
        self.input_bar.set_generating(True)

        self._worker_thread = QThread(self)
        self._worker = ChatStreamWorker(
            chat_service=self.chat_service,
            chat_id=chat_id,
            assistant_message_id=asst_msg.id,
            provider=provider,
            settings=GenerationSettings(),
            cancellation_token=self._current_cancel_token,
        )
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.token_received.connect(self._on_token_received)
        self._worker.completed.connect(self._on_generation_completed)
        self._worker.cancelled.connect(self._on_generation_cancelled)
        self._worker.error_occurred.connect(self._on_generation_error)

        self._worker_thread.start()

    def cancel_generation(self) -> None:
        """Trigger cancellation of the active generation turn."""
        if self._current_cancel_token is not None:
            logger.info("User requested cancellation of generation.")
            self._current_cancel_token.cancel()

    def retry_last_message(self) -> None:
        """Re-submit the previous user prompt after discarding the last assistant turn."""
        if not self.active_chat:
            return

        chat_id = self.active_chat.id
        result = self.chat_service.retry_last_message(chat_id)
        if result is None:
            return

        prompt_text, _ = result
        # Reload chat to reflect removed assistant message
        self.load_chat(chat_id)
        # Send prompt again
        self.send_message(prompt_text)

    def _on_token_received(self, delta: str) -> None:
        self._stream_accumulated_text += delta
        if self._active_stream_widget is not None:
            self._active_stream_widget.set_content(self._stream_accumulated_text)
            self._scroll_to_bottom()

    def _on_generation_completed(self, full_text: str, total_tokens: int, duration_ms: int) -> None:
        self._cleanup_worker()
        self.input_bar.set_generating(False)
        if self.active_chat is not None:
            # Reload messages to display metrics footer
            self.load_chat(self.active_chat.id)

    def _on_generation_cancelled(self) -> None:
        self._cleanup_worker()
        self.input_bar.set_generating(False)
        if self.active_chat is not None:
            self.load_chat(self.active_chat.id)

    def _on_generation_error(self, error_msg: str) -> None:
        self._cleanup_worker()
        self.input_bar.set_generating(False)
        QMessageBox.warning(self, "Generation Interrupted", f"Generation error: {error_msg}")
        if self.active_chat is not None:
            self.load_chat(self.active_chat.id)

    def _cleanup_worker(self) -> None:
        if self._worker_thread is not None and self._worker_thread.isRunning():
            self._worker_thread.quit()
            self._worker_thread.wait()
        self._worker_thread = None
        self._worker = None
        self._current_cancel_token = None
        self._active_stream_widget = None

    def _on_export_clicked(self) -> None:
        if self.active_chat is not None:
            self.export_requested.emit(self.active_chat.id)
