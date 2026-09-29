"""Minimal Provider Test Dialog for Sarthika Code (Milestone 3).

Allows selecting between Mock and Local providers, submitting a test prompt,
viewing real-time streaming tokens, and verifying cancellation.
This is not the final chat workspace.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.domain.config import GenerationSettings
from sarthika_code.llm.base import (
    CancellationToken,
    ChatMessage,
    LLMProvider,
    StreamCompletedEvent,
    StreamErrorEvent,
    StreamStartedEvent,
    StreamTokenEvent,
)
from sarthika_code.llm.factory import LLMProviderFactory
from sarthika_code.llm.manager import LlamaServerManager
from sarthika_code.llm.mock import MockLLMProvider
from sarthika_code.services.settings_service import SettingsService

if TYPE_CHECKING:
    pass


class StreamWorker(QObject):
    """Background worker executing async streaming generation off the Qt GUI thread."""

    token_received = Signal(str)
    started = Signal(str)
    completed = Signal(str, int, int)  # full_text, tokens, duration_ms
    error_occurred = Signal(str, bool)  # error_message, is_cancelled

    def __init__(
        self,
        provider: LLMProvider,
        messages: list[ChatMessage],
        settings: GenerationSettings,
        cancel_token: CancellationToken,
    ) -> None:
        super().__init__()
        self.provider = provider
        self.messages = messages
        self.settings = settings
        self.cancel_token = cancel_token

    def run(self) -> None:
        """Execute async stream in a dedicated asyncio loop on this worker thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._stream_loop())
        finally:
            loop.close()

    async def _stream_loop(self) -> None:
        full_text_list: list[str] = []
        token_count = 0

        try:
            async for event in self.provider.stream_chat(
                messages=self.messages,
                settings=self.settings,
                cancellation_token=self.cancel_token,
            ):
                if isinstance(event, StreamStartedEvent):
                    self.started.emit(event.model_name or "model")
                elif isinstance(event, StreamTokenEvent):
                    token_count += 1
                    full_text_list.append(event.delta)
                    self.token_received.emit(event.delta)
                elif isinstance(event, StreamCompletedEvent):
                    self.completed.emit(event.full_text, event.total_tokens or token_count, event.duration_ms or 0)
                    return
                elif isinstance(event, StreamErrorEvent):
                    self.error_occurred.emit(event.error, event.is_cancelled)
                    return
        except Exception as e:
            self.error_occurred.emit(str(e), False)


class ProviderTestDialog(QDialog):
    """Minimal test harness for validating streaming and cancellation."""

    def __init__(
        self,
        settings_service: SettingsService,
        server_manager: LlamaServerManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings_service = settings_service
        self.server_manager = server_manager
        self.settings = self.settings_service.load_settings()

        self._current_cancel_token: CancellationToken | None = None
        self._worker_thread: QThread | None = None
        self._worker: StreamWorker | None = None

        self.setWindowTitle("LLM Provider Streaming Test — Sarthika Code")
        self.resize(760, 560)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Provider Selector Bar
        top_bar = QHBoxLayout()

        lbl_provider = QLabel("Active Provider:")
        lbl_provider.setStyleSheet("font-weight: bold;")
        top_bar.addWidget(lbl_provider)

        self.cmb_provider = QComboBox()
        self.cmb_provider.addItem("Offline Mock Provider", "mock")
        self.cmb_provider.addItem("Local llama-server Provider (127.0.0.1)", "local")

        # Select initial item based on settings
        if self.settings.mock_mode:
            self.cmb_provider.setCurrentIndex(0)
        else:
            self.cmb_provider.setCurrentIndex(1)
        self.cmb_provider.currentIndexChanged.connect(self._on_provider_selection_changed)
        top_bar.addWidget(self.cmb_provider)

        self.lbl_provider_meta = QLabel("")
        self.lbl_provider_meta.setStyleSheet("color: #94a3b8; font-size: 11px;")
        top_bar.addWidget(self.lbl_provider_meta)
        top_bar.addStretch()

        layout.addLayout(top_bar)

        # Prompt Input Row
        prompt_layout = QHBoxLayout()
        self.txt_prompt = QLineEdit("Write a Python function to check if a number is prime.")
        prompt_layout.addWidget(self.txt_prompt)

        self.btn_send = QPushButton("Start Streaming")
        self.btn_send.setStyleSheet(
            "background-color: #2563eb; color: white; padding: 6px 16px; font-weight: bold; border-radius: 4px;"
        )
        self.btn_send.clicked.connect(self._start_streaming)
        prompt_layout.addWidget(self.btn_send)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet(
            "background-color: #dc2626; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px;"
        )
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_streaming)
        prompt_layout.addWidget(self.btn_cancel)

        layout.addLayout(prompt_layout)

        # Streaming Output Box
        self.txt_output = QPlainTextEdit()
        self.txt_output.setReadOnly(True)
        mono_font = QFont("Courier New", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.txt_output.setFont(mono_font)
        self.txt_output.setStyleSheet(
            "background-color: #0f172a; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; padding: 12px;"
        )
        layout.addWidget(self.txt_output)

        # Status and Metrics Box
        self.status_box = QFrame()
        self.status_box.setStyleSheet(
            "background-color: #1e293b; border-radius: 4px; padding: 8px;"
        )
        status_layout = QHBoxLayout(self.status_box)
        status_layout.setContentsMargins(10, 6, 10, 6)

        self.lbl_status = QLabel("Ready for test prompt.")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 12px;")
        status_layout.addWidget(self.lbl_status)
        status_layout.addStretch()

        self.lbl_metrics = QLabel("")
        self.lbl_metrics.setStyleSheet("color: #38bdf8; font-size: 12px;")
        status_layout.addWidget(self.lbl_metrics)

        layout.addWidget(self.status_box)

        # Footer Button Row
        footer_layout = QHBoxLayout()
        btn_clear = QPushButton("Clear Output")
        btn_clear.clicked.connect(self.txt_output.clear)
        footer_layout.addWidget(btn_clear)

        footer_layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self._on_close)
        footer_layout.addWidget(btn_close)
        layout.addLayout(footer_layout)

        self._update_provider_metadata_label()

    def _get_active_provider(self) -> LLMProvider:
        """Instantiate the provider selected in the combo box."""
        choice = self.cmb_provider.currentData()
        if choice == "mock":
            return MockLLMProvider()

        # Real provider
        return LLMProviderFactory.create_provider(
            settings=self.settings,
            server_manager=self.server_manager,
        )

    def _on_provider_selection_changed(self) -> None:
        """Update provider metadata when user switches dropdown selection."""
        self._update_provider_metadata_label()

    def _update_provider_metadata_label(self) -> None:
        """Display operational details of active provider."""
        provider = self._get_active_provider()
        meta = provider.provider_metadata()
        self.lbl_provider_meta.setText(f"({meta.get('status', 'Ready')} | Host: {meta.get('host', 'local')})")

    def _start_streaming(self) -> None:
        """Launch background streaming thread."""
        prompt = self.txt_prompt.text().strip()
        if not prompt:
            return

        self.txt_output.clear()
        self.lbl_status.setText("Connecting and streaming tokens...")
        self.lbl_status.setStyleSheet("color: #facc15; font-size: 12px;")
        self.lbl_metrics.setText("")

        self.btn_send.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.cmb_provider.setEnabled(False)

        provider = self._get_active_provider()
        self._current_cancel_token = CancellationToken()

        messages = [
            ChatMessage(role="system", content="You are a helpful local coding assistant."),
            ChatMessage(role="user", content=prompt),
        ]
        settings = GenerationSettings(temperature=0.3, max_tokens=1024)

        # Prepare thread and worker
        self._worker_thread = QThread()
        self._worker = StreamWorker(
            provider=provider,
            messages=messages,
            settings=settings,
            cancel_token=self._current_cancel_token,
        )
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.token_received.connect(self._on_token_received)
        self._worker.completed.connect(self._on_stream_completed)
        self._worker.error_occurred.connect(self._on_stream_error)

        # Cleanup connections
        self._worker.completed.connect(self._worker_thread.quit)
        self._worker.error_occurred.connect(self._worker_thread.quit)

        self._worker_thread.start()

    def _cancel_streaming(self) -> None:
        """Request immediate cancellation of active stream."""
        if self._current_cancel_token is not None:
            self._current_cancel_token.cancel()
        self.lbl_status.setText("Cancelling generation...")
        self.lbl_status.setStyleSheet("color: #f87171; font-size: 12px;")

    def _on_token_received(self, delta: str) -> None:
        """Append received token fragment to output widget."""
        cursor = self.txt_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(delta)
        self.txt_output.setTextCursor(cursor)

    def _on_stream_completed(self, full_text: str, total_tokens: int, duration_ms: int) -> None:
        """Update metrics upon successful completion."""
        tps = (total_tokens / (duration_ms / 1000)) if duration_ms > 0 else 0.0
        self.lbl_status.setText("Generation completed successfully.")
        self.lbl_status.setStyleSheet("color: #4ade80; font-size: 12px;")
        self.lbl_metrics.setText(f"{total_tokens} tokens | {duration_ms} ms (~{tps:.1f} t/s)")
        self._reset_buttons()

    def _on_stream_error(self, error_message: str, is_cancelled: bool) -> None:
        """Handle errors or user cancellation."""
        if is_cancelled:
            self.lbl_status.setText("Generation stopped by user (Cancelled).")
            self.lbl_status.setStyleSheet("color: #f59e0b; font-size: 12px;")
            self.txt_output.appendPlainText("\n\n[Generation Cancelled]")
        else:
            self.lbl_status.setText(f"Stream error: {error_message}")
            self.lbl_status.setStyleSheet("color: #ef4444; font-size: 12px;")
            self.txt_output.appendPlainText(f"\n\n[Error: {error_message}]")
        self._reset_buttons()

    def _reset_buttons(self) -> None:
        """Reset button states after generation concludes."""
        self.btn_send.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.cmb_provider.setEnabled(True)

    def _on_close(self) -> None:
        """Cleanly cancel any running thread before closing dialog."""
        if self._current_cancel_token is not None:
            self._current_cancel_token.cancel()
        if self._worker_thread is not None and self._worker_thread.isRunning():
            self._worker_thread.quit()
            self._worker_thread.wait(1000)
        self.accept()
