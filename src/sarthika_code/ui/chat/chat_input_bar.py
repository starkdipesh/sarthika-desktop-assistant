"""Multi-line prompt input bar with keyboard shortcuts and generation controls.

Supports Enter to send, Shift+Enter for newline, Stop button during generation,
and retry action.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.prompts.registry import WorkflowRegistry

if TYPE_CHECKING:
    pass


class ChatPromptEdit(QPlainTextEdit):
    """Custom QPlainTextEdit emitting submit on Enter and inserting newline on Shift+Enter."""

    submit_pressed = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Insert newline on Shift+Enter
                super().keyPressEvent(event)
            else:
                # Trigger submission on plain Enter
                event.accept()
                self.submit_pressed.emit()
        else:
            super().keyPressEvent(event)


class ChatInputBar(QWidget):
    """Bottom composer housing prompt editor, workflow picker, context trigger, and send controls."""

    submit_requested = Signal(str)
    cancel_requested = Signal()
    retry_requested = Signal()
    workflow_selected = Signal(str)
    context_toggle_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_generating = False

        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet("background-color: #080b13;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 6, 20, 10)
        layout.setSpacing(6)

        # 1. Main Composer Container Card (dynamically expands across full screen)
        self.composer_card = QFrame()
        self.composer_card.setObjectName("ComposerCard")
        self.composer_card.setMinimumWidth(320)
        self.composer_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.composer_card.setStyleSheet("""
            QFrame#ComposerCard {
                background-color: #0c121e;
                border: 1px solid #182236;
                border-radius: 14px;
            }
            QFrame#ComposerCard:focus-within {
                border: 1px solid #0284c7;
                background-color: #0e1626;
            }
        """)
        card_layout = QVBoxLayout(self.composer_card)
        card_layout.setContentsMargins(16, 10, 16, 10)
        card_layout.setSpacing(8)

        # Prompt text editor inside the card
        self.txt_prompt = ChatPromptEdit()
        self.txt_prompt.setPlaceholderText("Ask anything, @ to mention, / for workflows... (Shift+Enter for newline)")
        self.txt_prompt.setFixedHeight(68)
        font = QFont()
        font.setPointSize(10)
        self.txt_prompt.setFont(font)
        self.txt_prompt.setStyleSheet("""
            QPlainTextEdit {
                background-color: transparent;
                color: #f8fafc;
                border: none;
                padding: 0px;
                font-size: 13px;
                line-height: 1.5;
                selection-background-color: #0284c7;
            }
        """)
        self.txt_prompt.submit_pressed.connect(self._on_submit_clicked)
        self.prompt_edit = self.txt_prompt
        card_layout.addWidget(self.txt_prompt)

        # Internal toolbar row (Context, Workflow, Send/Cancel)
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(8)

        # Context trigger button inside composer
        self.btn_context_shortcut = QPushButton("+ Attach")
        self.btn_context_shortcut.setToolTip("Attach files or inspect active context (Ctrl+O)")
        self.btn_context_shortcut.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_context_shortcut.setStyleSheet("""
            QPushButton {
                background-color: #101929;
                color: #38bdf8;
                border: 1px solid #1a283e;
                border-radius: 8px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #162238;
                border-color: #0284c7;
                color: #ffffff;
            }
        """)
        self.btn_context_shortcut.clicked.connect(self.context_toggle_requested.emit)
        toolbar_layout.addWidget(self.btn_context_shortcut)

        # Workflow selector pill inside composer
        self.combo_workflow = QComboBox()
        self.combo_workflow.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_workflow.setToolTip("Active assistant workflow pattern")
        self.combo_workflow.setStyleSheet("""
            QComboBox {
                background-color: #101929;
                color: #cbd5e1;
                border: 1px solid #1a283e;
                border-radius: 8px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QComboBox:hover {
                color: #f1f5f9;
                border-color: #0284c7;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #0b111e;
                color: #f8fafc;
                border: 1px solid #1a283e;
                selection-background-color: #0284c7;
                padding: 4px;
            }
        """)
        for wf in WorkflowRegistry.list_all_including_general():
            self.combo_workflow.addItem(f"⚡ {wf.name}", wf.id)
        self.combo_workflow.currentIndexChanged.connect(self._on_workflow_changed)
        toolbar_layout.addWidget(self.combo_workflow)

        toolbar_layout.addStretch()

        # Stop button during generation
        self.btn_cancel = QPushButton("■ Stop")
        self.btn_cancel.setToolTip("Stop response generation (Esc)")
        self.btn_cancel.setShortcut(QKeySequence("Escape"))
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #991b1b;
                color: #ffffff;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 11px;
                border: 1px solid #dc2626;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
        """)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        toolbar_layout.addWidget(self.btn_cancel)

        # Send button
        self.btn_send = QPushButton("↑ Send")
        self.btn_send.setToolTip("Send prompt to local model (Enter)")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                padding: 6px 18px;
                font-weight: 600;
                font-size: 12px;
                border: 1px solid #38bdf8;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            QPushButton:disabled {
                background-color: #151d2a;
                color: #475569;
                border-color: #212c3d;
            }
        """)
        self.btn_send.clicked.connect(self._on_submit_clicked)
        toolbar_layout.addWidget(self.btn_send)

        card_layout.addLayout(toolbar_layout)
        layout.addWidget(self.composer_card)

        # 2. Bottom Info & Hint Footer
        hint_layout = QHBoxLayout()
        hint_layout.setContentsMargins(4, 0, 4, 0)
        hint_layout.setSpacing(8)

        self.lbl_hint = QLabel("🔒 Runs 100% locally • Enter to send • Shift+Enter for newline • Esc to cancel")
        self.lbl_hint.setStyleSheet("color: #64748b; font-size: 11px;")
        hint_layout.addWidget(self.lbl_hint)

        hint_layout.addStretch()

        self.btn_retry = QPushButton("Retry Last Turn")
        self.btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_retry.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                font-size: 11px;
                text-decoration: underline;
                border: none;
            }
            QPushButton:hover {
                color: #94a3b8;
            }
        """)
        self.btn_retry.clicked.connect(self.retry_requested.emit)
        hint_layout.addWidget(self.btn_retry)

        layout.addLayout(hint_layout)

    def _on_workflow_changed(self, index: int) -> None:
        workflow_id = self.combo_workflow.itemData(index)
        if workflow_id:
            self.workflow_selected.emit(str(workflow_id))

    def set_active_workflow(self, workflow_id: str) -> None:
        idx = self.combo_workflow.findData(workflow_id)
        if idx >= 0 and idx != self.combo_workflow.currentIndex():
            self.combo_workflow.blockSignals(True)
            self.combo_workflow.setCurrentIndex(idx)
            self.combo_workflow.blockSignals(False)

    def update_context_count(self, count: int) -> None:
        """Update context shortcut button label with file count."""
        if count > 0:
            self.btn_context_shortcut.setText(f"📁 Context ({count})")
            self.btn_context_shortcut.setStyleSheet("""
                QPushButton {
                    background-color: #0c4a6e;
                    color: #7dd3fc;
                    border: 1px solid #0284c7;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #0284c7;
                    color: #ffffff;
                }
            """)
        else:
            self.btn_context_shortcut.setText("📁 Context")
            self.btn_context_shortcut.setStyleSheet("""
                QPushButton {
                    background-color: #111d33;
                    color: #38bdf8;
                    border: 1px solid #1e3a63;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #1e3a63;
                    color: #ffffff;
                }
            """)

    def set_generating(self, is_generating: bool) -> None:
        """Toggle UI between idle and generating states."""
        self._is_generating = is_generating
        self.btn_send.setEnabled(not is_generating)
        self.btn_cancel.setVisible(is_generating)
        self.btn_retry.setEnabled(not is_generating)
        if is_generating:
            self.lbl_hint.setText("⚡ Sarthika Code is generating locally... Press Esc or click 'Stop' to cancel.")
            self.lbl_hint.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 600;")
        else:
            self.lbl_hint.setText("🔒 Runs 100% locally • Enter to send • Shift+Enter for newline • Esc to cancel")
            self.lbl_hint.setStyleSheet("color: #64748b; font-size: 11px;")

    def get_prompt_text(self) -> str:
        return self.txt_prompt.toPlainText().strip()

    def clear(self) -> None:
        self.txt_prompt.clear()

    def set_prompt_text(self, text: str) -> None:
        self.txt_prompt.setPlainText(text)
        self.txt_prompt.moveCursor(self.txt_prompt.textCursor().MoveOperation.End)

    def _on_submit_clicked(self) -> None:
        if self._is_generating:
            return
        text = self.get_prompt_text()
        if text:
            self.submit_requested.emit(text)
            self.clear()
