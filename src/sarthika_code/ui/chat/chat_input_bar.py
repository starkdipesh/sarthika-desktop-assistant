"""Multi-line prompt input bar with keyboard shortcuts and generation controls.

Supports Enter to send, Shift+Enter for newline, Stop button during generation,
and retry action.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

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
    """Bottom input bar housing prompt editor, send, cancel, and retry buttons."""

    submit_requested = Signal(str)
    cancel_requested = Signal()
    retry_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_generating = False

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 12)
        layout.setSpacing(6)

        # Editor + Buttons row
        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)

        self.txt_prompt = ChatPromptEdit()
        self.txt_prompt.setPlaceholderText("Ask Sarthika Code a question or paste code here... (Shift+Enter for newline)")
        self.txt_prompt.setFixedHeight(72)
        font = QFont()
        font.setPointSize(10)
        self.txt_prompt.setFont(font)
        self.txt_prompt.setStyleSheet(
            "QPlainTextEdit {"
            "  background-color: #0f172a;"
            "  color: #f8fafc;"
            "  border: 1px solid #334155;"
            "  border-radius: 6px;"
            "  padding: 8px;"
            "}"
            "QPlainTextEdit:focus {"
            "  border: 1px solid #3b82f6;"
            "}"
        )
        self.txt_prompt.submit_pressed.connect(self._on_submit_clicked)
        row_layout.addWidget(self.txt_prompt, stretch=1)

        # Action button column
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(6)

        self.btn_send = QPushButton("Send")
        self.btn_send.setStyleSheet(
            "background-color: #2563eb; color: white; padding: 8px 18px; font-weight: bold; border-radius: 4px;"
        )
        self.btn_send.clicked.connect(self._on_submit_clicked)
        btn_layout.addWidget(self.btn_send)

        self.btn_cancel = QPushButton("Stop")
        self.btn_cancel.setStyleSheet(
            "background-color: #dc2626; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px;"
        )
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        btn_layout.addWidget(self.btn_cancel)

        row_layout.addLayout(btn_layout)
        layout.addLayout(row_layout)

        # Bottom hint bar
        hint_layout = QHBoxLayout()
        self.lbl_hint = QLabel("Enter to send • Shift+Enter for newline • 100% Local Inference")
        self.lbl_hint.setStyleSheet("color: #64748b; font-size: 10px;")
        hint_layout.addWidget(self.lbl_hint)

        hint_layout.addStretch()

        self.btn_retry = QPushButton("Retry Last Turn")
        self.btn_retry.setStyleSheet(
            "background-color: transparent; color: #94a3b8; font-size: 11px; text-decoration: underline; border: none;"
        )
        self.btn_retry.clicked.connect(self.retry_requested.emit)
        hint_layout.addWidget(self.btn_retry)

        layout.addLayout(hint_layout)

    def set_generating(self, is_generating: bool) -> None:
        """Toggle UI between idle and generating states."""
        self._is_generating = is_generating
        self.btn_send.setEnabled(not is_generating)
        self.btn_cancel.setVisible(is_generating)
        self.btn_retry.setEnabled(not is_generating)
        if is_generating:
            self.lbl_hint.setText("Sarthika Code is generating locally... Click 'Stop' to cancel.")
            self.lbl_hint.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: bold;")
        else:
            self.lbl_hint.setText("Enter to send • Shift+Enter for newline • 100% Local Inference")
            self.lbl_hint.setStyleSheet("color: #64748b; font-size: 10px;")

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
