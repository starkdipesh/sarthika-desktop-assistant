"""Main chat workspace orchestrating conversation view, workflows, context files, and streaming controls.

Decouples GUI events from async provider generation through a dedicated QThread worker.
Includes welcome/workflow selection for empty conversations, project context management,
and developer prompt inspection in debug mode.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
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
from sarthika_code.prompts.registry import WorkflowRegistry
from sarthika_code.services.auth_service import LocalAuthService
from sarthika_code.services.chat_service import ChatService
from sarthika_code.services.context_service import ProjectContextService
from sarthika_code.services.model_service import ModelService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.ui.chat.chat_input_bar import ChatInputBar
from sarthika_code.ui.chat.context_panel import ContextPanel
from sarthika_code.ui.chat.message_widget import MessageWidget
from sarthika_code.ui.chat.vault_lock_overlay import VaultLockOverlay
from sarthika_code.ui.chat.workflow_selection_widget import WorkflowSelectionWidget
from sarthika_code.ui.dialogs.prompt_review_dialog import PromptReviewDialog
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
        file_context_prompt: str | None = None,
    ) -> None:
        super().__init__()
        self.chat_service = chat_service
        self.chat_id = chat_id
        self.assistant_message_id = assistant_message_id
        self.provider = provider
        self.settings = settings
        self.cancellation_token = cancellation_token
        self.file_context_prompt = file_context_prompt

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
                file_context_prompt=self.file_context_prompt,
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
    """Central conversation workspace displaying message history, workflows, and streaming controls."""

    chat_title_updated = Signal(str, str)  # chat_id, new_title
    export_requested = Signal(str)  # chat_id

    def __init__(
        self,
        chat_service: ChatService,
        settings_service: SettingsService,
        model_service: ModelService | None = None,
        context_service: ProjectContextService | None = None,
        auth_service: LocalAuthService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.chat_service = chat_service
        self.settings_service = settings_service
        self.model_service = model_service
        self.context_service = context_service or ProjectContextService(chat_service.db_manager)
        self.auth_service = auth_service or LocalAuthService(self.settings_service)
        self.active_chat: Chat | None = None
        self.welcome_widget: WorkflowSelectionWidget | None = None

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
            "background-color: #080b13; border-bottom: 1px solid #151c28; padding: 4px 20px;"
        )
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(12, 6, 12, 6)
        header_layout.setSpacing(10)

        self.lbl_chat_title = QLabel("Select or start a conversation")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        self.lbl_chat_title.setFont(title_font)
        self.lbl_chat_title.setStyleSheet("color: #f8fafc; font-weight: 600;")
        header_layout.addWidget(self.lbl_chat_title)

        header_layout.addStretch()

        # Context & Code panel toggle button
        self.btn_toggle_context = QPushButton("📁 Context (0)")
        self.btn_toggle_context.setToolTip("Attached project context and code snippets (Ctrl+O)")
        self.btn_toggle_context.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_context.setStyleSheet("""
            QPushButton {
                background-color: #0c121e;
                color: #38bdf8;
                border: 1px solid #182236;
                font-size: 11px;
                padding: 5px 12px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #121c2d;
                border-color: #0284c7;
                color: #ffffff;
            }
        """)
        self.btn_toggle_context.clicked.connect(self._toggle_context_panel)
        header_layout.addWidget(self.btn_toggle_context)

        # Workflow selector
        lbl_wf = QLabel("Workflow:")
        lbl_wf.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 500;")
        header_layout.addWidget(lbl_wf)

        self.combo_workflow = QComboBox()
        self.combo_workflow.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_workflow.setStyleSheet("""
            QComboBox {
                background-color: #0d1526;
                color: #cbd5e1;
                border: 1px solid #1c2e4a;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 500;
            }
            QComboBox:hover {
                color: #f1f5f9;
                border-color: #0284c7;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #1e2d4a;
                selection-background-color: #0284c7;
                padding: 4px;
            }
        """)
        for wf in WorkflowRegistry.list_all_including_general():
            self.combo_workflow.addItem(wf.name, wf.id)
        self.combo_workflow.currentIndexChanged.connect(self._on_workflow_combo_changed)
        header_layout.addWidget(self.combo_workflow)

        # Debug prompt inspection button (hidden by default)
        self.btn_inspect_prompt = QPushButton("Inspect Prompt (Debug)")
        self.btn_inspect_prompt.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_inspect_prompt.setStyleSheet("""
            QPushButton {
                background-color: #3f1910;
                color: #fdba74;
                border: 1px solid #ea580c;
                font-size: 11px;
                padding: 4px 10px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #5c2415;
            }
        """)
        self.btn_inspect_prompt.clicked.connect(self._on_inspect_prompt_clicked)
        self.btn_inspect_prompt.setVisible(False)
        header_layout.addWidget(self.btn_inspect_prompt)

        # Export button
        self.btn_export = QPushButton("⤓ Export")
        self.btn_export.setToolTip("Export conversation to Markdown or Plain Text")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #0d1526;
                color: #94a3b8;
                border: 1px solid #1c2e4a;
                font-size: 11px;
                padding: 5px 12px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #132038;
                color: #f1f5f9;
                border-color: #0284c7;
            }
            QPushButton:disabled {
                background-color: #090e1a;
                color: #334155;
                border-color: #141d2d;
            }
        """)
        self.btn_export.clicked.connect(self._on_export_clicked)
        self.btn_export.setEnabled(False)
        header_layout.addWidget(self.btn_export)

        main_layout.addWidget(self.header_frame)

        # Body Stack: Page 0 = normal conversation, Page 1 = VaultLockOverlay
        self.body_stack = QStackedWidget()

        self.chat_body_widget = QWidget()
        self.chat_body_widget.setStyleSheet("background-color: #080b13;")
        body_layout = QVBoxLayout(self.chat_body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Scroll area for messages or welcome screen
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: #080b13; border: none; }")

        self.message_container = QWidget()
        self.message_container.setStyleSheet("background-color: #080b13;")
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setContentsMargins(20, 16, 20, 16)
        self.message_layout.setSpacing(14)
        self.message_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.message_layout.addStretch()

        self.scroll_area.setWidget(self.message_container)
        body_layout.addWidget(self.scroll_area, stretch=1)

        # Project Context & Code Snippets Drawer (collapsible)
        self.context_panel = ContextPanel(self.context_service, self)
        self.context_panel.setFixedHeight(220)
        self.context_panel.setVisible(False)  # Hidden by default until toggled
        self.context_panel.context_changed.connect(self._update_context_button_label)
        self.context_panel.snippet_inserted.connect(self._on_snippet_inserted)
        body_layout.addWidget(self.context_panel)

        # Input bar
        self.input_bar = ChatInputBar()
        self.input_bar.submit_requested.connect(self.send_message)
        self.input_bar.cancel_requested.connect(self.cancel_generation)
        self.input_bar.retry_requested.connect(self.retry_last_message)
        self.input_bar.workflow_selected.connect(self._on_workflow_selected_from_composer)
        self.input_bar.context_toggle_requested.connect(self._toggle_context_panel)
        body_layout.addWidget(self.input_bar)

        self.body_stack.addWidget(self.chat_body_widget)

        # Page 1: Vault Lock Overlay
        self.vault_overlay = VaultLockOverlay(self.auth_service, self)
        self.vault_overlay.unlocked.connect(self._on_vault_unlocked)
        self.body_stack.addWidget(self.vault_overlay)

        main_layout.addWidget(self.body_stack, stretch=1)

        if self.auth_service.is_locked():
            self.set_locked(True)

    def set_locked(self, locked: bool) -> None:
        """Lock or unlock the workspace view."""
        if locked:
            self.body_stack.setCurrentWidget(self.vault_overlay)
            self.vault_overlay.focus_pin_input()
        else:
            self.body_stack.setCurrentWidget(self.chat_body_widget)

    def is_locked(self) -> bool:
        """Return True if workspace is currently showing lock screen."""
        return self.body_stack.currentWidget() == self.vault_overlay

    def _on_vault_unlocked(self) -> None:
        self.set_locked(False)

    def load_chat(self, chat_id: str) -> None:
        """Load conversation messages, active workflow, and attached context files into view."""
        self.active_chat = self.chat_service.get_chat(chat_id)
        if self.active_chat is None:
            self.lbl_chat_title.setText("Conversation not found")
            self.btn_export.setEnabled(False)
            return

        self.lbl_chat_title.setText(self.active_chat.title)
        self.btn_export.setEnabled(True)

        # Sync workflow combo without firing signal
        self.combo_workflow.blockSignals(True)
        idx = self.combo_workflow.findData(self.active_chat.workflow)
        if idx >= 0:
            self.combo_workflow.setCurrentIndex(idx)
        else:
            default_wf = WorkflowRegistry.get_default_workflow().id
            default_idx = self.combo_workflow.findData(default_wf)
            if default_idx >= 0:
                self.combo_workflow.setCurrentIndex(default_idx)
        self.combo_workflow.blockSignals(False)
        self.input_bar.set_active_workflow(self.active_chat.workflow)

        # Check debug mode visibility
        settings = self.settings_service.load_settings()
        self.btn_inspect_prompt.setVisible(getattr(settings, "debug_mode", False))

        # Refresh attached files in context panel
        self.context_panel.set_chat(chat_id, context_limit=settings.context_size)
        self._update_context_button_label()

        self._clear_messages()

        # If chat is empty, show the workflow selection welcome screen
        if not self.active_chat.messages:
            self._show_welcome_screen()
        else:
            for msg in self.active_chat.messages:
                self._add_message_widget(msg, is_mock=settings.mock_mode)
            self._scroll_to_bottom()

    def set_debug_mode(self, enabled: bool) -> None:
        """Update visibility of developer prompt inspection button."""
        self.btn_inspect_prompt.setVisible(enabled)

    def _toggle_context_panel(self) -> None:
        """Toggle the visibility of the Project Context and Code Snippets panel."""
        is_visible = self.context_panel.isVisible()
        self.context_panel.setVisible(not is_visible)

    def _update_context_button_label(self) -> None:
        """Update the header context button text based on attached file count."""
        if not self.active_chat:
            self.btn_toggle_context.setText("📁 Context & Code (0)")
            self.input_bar.update_context_count(0)
            return
        files = self.context_service.list_files(self.active_chat.id)
        self.btn_toggle_context.setText(f"📁 Context & Code ({len(files)})")
        self.input_bar.update_context_count(len(files))

    def _on_snippet_inserted(self, code: str, language: str) -> None:
        """Append formatted code block from snippet editor into prompt edit box."""
        fence = f"```{language}\n{code}\n```"
        if hasattr(self.input_bar, "prompt_edit"):
            current = self.input_bar.prompt_edit.toPlainText()
            if current.strip():
                self.input_bar.prompt_edit.setPlainText(f"{current}\n\n{fence}")
            else:
                self.input_bar.prompt_edit.setPlainText(fence)
            self.input_bar.prompt_edit.setFocus()

    def _show_welcome_screen(self) -> None:
        """Display the curated workflow grid in the workspace for new/empty conversations."""
        self.welcome_widget = WorkflowSelectionWidget()
        self.welcome_widget.setMaximumWidth(840)
        self.welcome_widget.workflow_selected.connect(self._on_workflow_card_selected)
        self.message_layout.insertWidget(0, self.welcome_widget)

    def _on_workflow_card_selected(self, workflow_id: str) -> None:
        """Handle selection of a curated workflow card from the welcome screen."""
        idx = self.combo_workflow.findData(workflow_id)
        if idx >= 0:
            self.combo_workflow.setCurrentIndex(idx)

        self.input_bar.set_active_workflow(workflow_id)

        wf = WorkflowRegistry.get_workflow(workflow_id)
        if wf and hasattr(self.input_bar, "prompt_edit"):
            req_hint = wf.input_requirements[0] if wf.input_requirements else "your request"
            self.input_bar.prompt_edit.setPlaceholderText(f"[{wf.name}] Enter {req_hint}...")
            self.input_bar.prompt_edit.setFocus()

    def _on_workflow_selected_from_composer(self, workflow_id: str) -> None:
        """Synchronize workflow selected inside composer toolbar with header combo and chat model."""
        idx = self.combo_workflow.findData(workflow_id)
        if idx >= 0 and idx != self.combo_workflow.currentIndex():
            self.combo_workflow.setCurrentIndex(idx)

    def _on_workflow_combo_changed(self, index: int) -> None:
        """Handle user changing active workflow for subsequent prompts."""
        workflow_id = self.combo_workflow.itemData(index)
        if not workflow_id:
            return

        self.input_bar.set_active_workflow(str(workflow_id))

        if self.active_chat and self.active_chat.workflow != workflow_id:
            self.chat_service.update_chat_workflow(self.active_chat.id, workflow_id)
            self.active_chat.workflow = workflow_id
            logger.info("Switched active workflow to '%s' for chat %s", workflow_id, self.active_chat.id)

    def _on_inspect_prompt_clicked(self) -> None:
        """Open developer prompt inspector dialog."""
        if not self.active_chat:
            return

        file_ctx_prompt = (
            self.context_service.build_context_prompt(self.active_chat.id)
            if self.context_panel.should_include_context()
            else None
        )

        prompt_data = self.chat_service.get_debug_prompt(
            self.active_chat.id,
            file_context_prompt=file_ctx_prompt,
        )
        dlg = PromptReviewDialog(prompt_data, self)
        dlg.exec()

    def _clear_messages(self) -> None:
        while self.message_layout.count() > 1:
            item = self.message_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        self.welcome_widget = None

    def _add_message_widget(self, message: Message, is_mock: bool = False) -> MessageWidget:
        widget = MessageWidget(message, is_mock_mode=is_mock)
        widget.setMaximumWidth(840)
        widget.retry_requested.connect(self.retry_last_message)
        # Insert before final stretch
        self.message_layout.insertWidget(self.message_layout.count() - 1, widget)
        return widget

    def _scroll_to_bottom(self) -> None:
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def send_message(self, prompt: str) -> None:
        """Submit a user prompt and initiate background streaming generation."""
        if not self.active_chat:
            selected_wf = self.combo_workflow.currentData() or "explain_code"
            new_chat = self.chat_service.create_chat(workflow=selected_wf)
            self.active_chat = new_chat
            self.chat_title_updated.emit(new_chat.id, new_chat.title)

        # Clear welcome screen if still present
        if self.welcome_widget is not None:
            self._clear_messages()

        chat_id = self.active_chat.id
        settings = self.settings_service.load_settings()

        # Check server readiness if not in mock mode
        if (
            not settings.mock_mode
            and self.model_service is not None
            and self.model_service.get_status().state != ServerState.READY
        ):
            box = QMessageBox(self)
            box.setWindowTitle("Model Server Offline")
            box.setIcon(QMessageBox.Icon.Warning)
            box.setText("The local model server is not currently running.")
            box.setInformativeText(
                "You can start your local llama-server, or enable Offline Mock / Demo Mode "
                "to test the user interface without downloading model weights."
            )
            btn_mock = box.addButton("Enable Mock Mode", QMessageBox.ButtonRole.ActionRole)
            box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() == btn_mock:
                settings.mock_mode = True
                self.settings_service.save_settings(settings)
                # Re-fetch settings
                settings = self.settings_service.load_settings()
            else:
                return

        # Check attached file context and budget limits
        file_context_prompt: str | None = None
        if self.context_panel.should_include_context():
            budget = self.context_service.get_budget(chat_id, context_limit=settings.context_size)
            if budget.is_exceeded:
                QMessageBox.warning(
                    self,
                    "Context Limit Exceeded",
                    f"The attached files ({budget.total_tokens:,} tokens) exceed your model's context limit ({budget.context_limit:,} tokens).\n\n"
                    "To prevent source code corruption, Sarthika Code will not silently truncate your files.\n"
                    "Please remove one or more files in the Context panel before sending.",
                )
                return

            file_context_prompt = self.context_service.build_context_prompt(chat_id)

        # 1. Persist and render user message
        user_msg = self.chat_service.add_user_message(chat_id, prompt)
        self._add_message_widget(user_msg, is_mock=settings.mock_mode)

        # Update title in header if auto-derived
        reloaded = self.chat_service.get_chat(chat_id)
        if reloaded and reloaded.title != self.lbl_chat_title.text():
            self.lbl_chat_title.setText(reloaded.title)
            self.chat_title_updated.emit(chat_id, reloaded.title)

        # Reset placeholder text
        if hasattr(self.input_bar, "prompt_edit"):
            self.input_bar.prompt_edit.setPlaceholderText(
                "Type a message or coding question... (Press Enter to send, Shift+Enter for new line)"
            )

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
            settings=settings.to_generation_settings(),
            cancellation_token=self._current_cancel_token,
            file_context_prompt=file_context_prompt,
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
