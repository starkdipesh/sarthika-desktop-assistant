"""Individual message card widget for Sarthika Code chat view.

Renders user and assistant turns with safe Markdown rendering, copy response,
code-block copy buttons, and retry actions. Never executes scripts or commands.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.domain.chat import Message

if TYPE_CHECKING:
    pass


def extract_code_blocks(text: str) -> list[str]:
    """Extract code snippets from markdown code fences."""
    pattern = r"```[a-zA-Z0-9_\-\.\+]*\n([\s\S]*?)```"
    matches = re.findall(pattern, text)
    if not matches:
        # Try unclosed code fence
        unclosed = re.findall(r"```[a-zA-Z0-9_\-\.\+]*\n([\s\S]*)", text)
        if unclosed:
            return unclosed
    return matches


class MessageWidget(QFrame):
    """Visual card representing a single conversation message turn."""

    retry_requested = Signal()

    def __init__(
        self,
        message: Message,
        is_mock_mode: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.message = message
        self.is_mock_mode = is_mock_mode

        self._init_ui()

    def _init_ui(self) -> None:
        is_user = self.message.role == "user"

        self.setFrameShape(QFrame.Shape.StyledPanel)
        if is_user:
            self.setStyleSheet(
                "MessageWidget {"
                "  background-color: #1e293b;"
                "  border: 1px solid #334155;"
                "  border-radius: 8px;"
                "  margin: 4px 12px 4px 48px;"
                "}"
            )
        else:
            self.setStyleSheet(
                "MessageWidget {"
                "  background-color: #0f172a;"
                "  border: 1px solid #1e3a5f;"
                "  border-radius: 8px;"
                "  margin: 4px 48px 4px 12px;"
                "}"
            )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header: Role label + Timestamp + Action buttons
        header_layout = QHBoxLayout()

        role_badge = QLabel()
        role_font = QFont()
        role_font.setBold(True)
        role_font.setPointSize(10)
        role_badge.setFont(role_font)

        if is_user:
            role_badge.setText("👤 You")
            role_badge.setStyleSheet("color: #60a5fa;")
            header_layout.addWidget(role_badge)
        else:
            # Cute girl AI avatar icon
            avatar_path = Path(__file__).resolve().parent.parent.parent.parent / "assets" / "avatar.svg"
            if avatar_path.exists():
                lbl_icon = QLabel()
                pixmap = QIcon(str(avatar_path)).pixmap(22, 22)
                if not pixmap.isNull():
                    lbl_icon.setPixmap(pixmap)
                    header_layout.addWidget(lbl_icon)

            suffix = " (Mock Mode)" if self.is_mock_mode else ""
            role_badge.setText(f"👧 Sarthika Code{suffix}")
            role_badge.setStyleSheet("color: #f472b6;")
            header_layout.addWidget(role_badge)

        if self.message.created_at:
            time_label = QLabel(self.message.created_at.strftime("%H:%M:%S"))
            time_label.setStyleSheet("color: #64748b; font-size: 10px; margin-left: 6px;")
            header_layout.addWidget(time_label)

        header_layout.addStretch()

        # Action Buttons: Copy Response, Copy Code, Retry
        self.btn_copy = QPushButton("Copy Text")
        self.btn_copy.setStyleSheet(
            "background-color: #334155; color: #cbd5e1; font-size: 11px; padding: 2px 8px; border-radius: 4px;"
        )
        self.btn_copy.clicked.connect(self._copy_text)
        header_layout.addWidget(self.btn_copy)

        self.code_blocks = extract_code_blocks(self.message.content)
        if not is_user and self.code_blocks:
            self.btn_copy_code = QPushButton("Copy Code")
            self.btn_copy_code.setStyleSheet(
                "background-color: #1e3a5f; color: #93c5fd; font-size: 11px; padding: 2px 8px; border-radius: 4px;"
            )
            self.btn_copy_code.clicked.connect(self._copy_code)
            header_layout.addWidget(self.btn_copy_code)

        if not is_user:
            self.btn_retry = QPushButton("Retry")
            self.btn_retry.setStyleSheet(
                "background-color: #334155; color: #f59e0b; font-size: 11px; padding: 2px 8px; border-radius: 4px;"
            )
            self.btn_retry.clicked.connect(self.retry_requested.emit)
            header_layout.addWidget(self.btn_retry)

        layout.addLayout(header_layout)

        # Message Content
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(False)
        self.content_browser.setReadOnly(True)
        self.content_browser.setStyleSheet(
            "QTextBrowser {"
            "  background-color: transparent;"
            "  color: #f8fafc;"
            "  border: none;"
            "  selection-background-color: #2563eb;"
            "}"
        )
        self.content_browser.document().setDefaultStyleSheet(
            "code { background-color: #1e293b; color: #38bdf8; font-family: monospace; padding: 2px 4px; border-radius: 3px; }"
            "pre { background-color: #111827; color: #e2e8f0; font-family: monospace; padding: 8px; border-radius: 4px; border: 1px solid #374151; }"
            "p { line-height: 1.4; margin: 4px 0; }"
        )
        self.set_content(self.message.content)
        layout.addWidget(self.content_browser)

        # Metrics footer for assistant messages if present
        if not is_user and (self.message.token_count or self.message.generation_duration_ms):
            footer_layout = QHBoxLayout()
            footer_layout.addStretch()

            metrics: list[str] = []
            if self.message.token_count:
                metrics.append(f"{self.message.token_count} tokens")
            if self.message.generation_duration_ms:
                sec = self.message.generation_duration_ms / 1000.0
                metrics.append(f"{sec:.1f}s")

            lbl_metrics = QLabel(" • ".join(metrics))
            lbl_metrics.setStyleSheet("color: #64748b; font-size: 10px;")
            footer_layout.addWidget(lbl_metrics)
            layout.addLayout(footer_layout)

    def set_content(self, text: str) -> None:
        """Update content safely rendering markdown."""
        self.content_browser.setMarkdown(text)
        # Recalculate height dynamically to fit content
        doc_height = int(self.content_browser.document().size().height())
        self.content_browser.setMinimumHeight(max(40, min(600, doc_height + 20)))

    def _copy_text(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.message.content)
            self.btn_copy.setText("Copied!")
            self.btn_copy.setEnabled(False)

    def _copy_code(self) -> None:
        if self.code_blocks:
            clipboard = QGuiApplication.clipboard()
            if clipboard is not None:
                # Copy the first/main code snippet
                clipboard.setText(self.code_blocks[0].strip())
                self.btn_copy_code.setText("Copied Code!")
                self.btn_copy_code.setEnabled(False)
