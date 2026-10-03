"""Individual message card widget for Sarthika Code chat view.

Renders user and assistant turns with safe Markdown rendering, copy response,
code-block copy buttons, and retry actions. Never executes scripts or commands.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
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
from sarthika_code.ui.chat.wavy_loader import WavyLoaderWidget

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
        self.is_user = self.message.role == "user"

        self._init_ui()

    def _init_ui(self) -> None:
        is_user = self.is_user

        self.setFrameShape(QFrame.Shape.NoFrame)
        if is_user:
            self.setStyleSheet(
                "MessageWidget {"
                "  background-color: #131c2d;"
                "  border: 1px solid #1f2e48;"
                "  border-radius: 16px;"
                "  margin: 6px 0px 8px 90px;"
                "}"
            )
        else:
            self.setStyleSheet(
                "MessageWidget {"
                "  background-color: transparent;"
                "  border: none;"
                "  margin: 8px 0px 16px 0px;"
                "}"
            )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16 if is_user else 4, 12 if is_user else 4, 16 if is_user else 4, 12 if is_user else 4)
        layout.setSpacing(8)

        # Header: Role label + Timestamp + Top Actions
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        role_badge = QLabel()
        role_font = QFont()
        role_font.setBold(True)
        role_font.setPointSize(10)
        role_badge.setFont(role_font)

        if is_user:
            role_badge.setText("👤 You")
            role_badge.setStyleSheet("color: #60a5fa; font-weight: 600;")
            header_layout.addWidget(role_badge)
        else:
            # Cute girl AI avatar icon if present
            avatar_path = Path(__file__).resolve().parent.parent.parent.parent / "assets" / "avatar.svg"
            if avatar_path.exists():
                lbl_icon = QLabel()
                pixmap = QIcon(str(avatar_path)).pixmap(22, 22)
                if not pixmap.isNull():
                    lbl_icon.setPixmap(pixmap)
                    header_layout.addWidget(lbl_icon)

            suffix = " (Demo Mode)" if self.is_mock_mode else ""
            role_badge.setText(f"✦ Sarthika Code{suffix}")
            role_badge.setStyleSheet("""
                background-color: #0c1e36;
                color: #38bdf8;
                font-weight: 700;
                letter-spacing: 0.3px;
                padding: 3px 9px;
                border: 1px solid #0284c7;
                border-radius: 10px;
            """)
            header_layout.addWidget(role_badge)

            if self.is_mock_mode:
                lbl_demo_pill = QLabel("DEMO")
                lbl_demo_pill.setStyleSheet(
                    "background-color: #1e3a5f; color: #7dd3fc; "
                    "font-size: 9px; font-weight: bold; padding: 2px 6px; border-radius: 4px;"
                )
                header_layout.addWidget(lbl_demo_pill)

        if self.message.created_at:
            time_label = QLabel(self.message.created_at.strftime("%H:%M:%S"))
            time_label.setStyleSheet("color: #64748b; font-size: 11px; margin-left: 4px;")
            header_layout.addWidget(time_label)

        header_layout.addStretch()

        # If user message, place Copy button in top right of bubble
        self.btn_copy = QPushButton("⎘ Copy")
        self.btn_copy.setToolTip("Copy message to clipboard")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #1a273e;
                color: #94a3b8;
                font-size: 11px;
                font-weight: 500;
                padding: 3px 9px;
                border: 1px solid #263857;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #243553;
                color: #f1f5f9;
                border-color: #38bdf8;
            }
        """)
        self.btn_copy.clicked.connect(self._copy_text)
        if is_user:
            header_layout.addWidget(self.btn_copy)

        layout.addLayout(header_layout)

        # Message Content
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(False)
        self.content_browser.setReadOnly(True)
        self.content_browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_browser.setStyleSheet(
            "QTextBrowser {"
            "  background-color: transparent;"
            "  color: #f1f5f9;"
            "  border: none;"
            "  selection-background-color: #0284c7;"
            "}"
        )
        self.content_browser.document().setDefaultStyleSheet(
            "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }"
            "p { line-height: 1.65; margin: 4px 0 8px 0; color: #e2e8f0; font-size: 13px; }"
            "code { background-color: #111a2d; color: #38bdf8; font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace; padding: 2px 6px; border-radius: 4px; font-size: 12px; }"
            "pre { background-color: #050811; color: #e2e8f0; font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace; padding: 12px 16px; border-radius: 10px; border: 1px solid #1a273e; font-size: 12px; line-height: 1.55; margin: 10px 0; }"
            "h1 { color: #f8fafc; font-size: 18px; margin: 14px 0 6px 0; font-weight: bold; border-bottom: 1px solid #1e293b; padding-bottom: 4px; }"
            "h2 { color: #f8fafc; font-size: 15px; margin: 12px 0 4px 0; font-weight: bold; }"
            "h3 { color: #f8fafc; font-size: 13px; margin: 10px 0 4px 0; font-weight: bold; }"
            "ul, ol { margin: 4px 0 8px 0; padding-left: 22px; color: #e2e8f0; }"
            "li { margin: 3px 0; line-height: 1.6; }"
            "blockquote { border-left: 3px solid #0284c7; padding-left: 12px; color: #94a3b8; font-style: italic; margin: 8px 0; }"
            "table { border-collapse: collapse; margin: 10px 0; width: 100%; }"
            "th, td { border: 1px solid #23334d; padding: 7px 12px; text-align: left; }"
            "th { background-color: #111d33; color: #f8fafc; font-weight: bold; }"
        )
        # Wavy loader for assistant messages while waiting for model generation
        self.wavy_loader = WavyLoaderWidget(self)
        layout.addWidget(self.wavy_loader)

        self.set_content(self.message.content)
        layout.addWidget(self.content_browser)

        # Bottom Actions & Metrics row for assistant
        self.code_blocks = extract_code_blocks(self.message.content)
        if not is_user:
            self.bottom_row_widget = QWidget()
            bottom_row = QHBoxLayout(self.bottom_row_widget)
            bottom_row.setContentsMargins(0, 0, 0, 0)
            bottom_row.setSpacing(6)

            # Copy Response text button
            header_layout.removeWidget(self.btn_copy)
            self.btn_copy.setText("⎘ Copy")
            self.btn_copy.setToolTip("Copy response")
            bottom_row.addWidget(self.btn_copy)

            # Copy Code button
            self.btn_copy_code = QPushButton("⎘ Code")
            self.btn_copy_code.setToolTip("Copy extracted code snippet")
            self.btn_copy_code.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_copy_code.setStyleSheet("""
                QPushButton {
                    background-color: #0c2b4d;
                    color: #7dd3fc;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 3px 10px;
                    border: 1px solid #0284c7;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #0284c7;
                    color: #ffffff;
                }
            """)
            self.btn_copy_code.clicked.connect(self._copy_code)
            if self.code_blocks:
                bottom_row.addWidget(self.btn_copy_code)
            else:
                self.btn_copy_code.setVisible(False)

            # Retry button
            self.btn_retry = QPushButton("↺ Retry")
            self.btn_retry.setToolTip("Regenerate response")
            self.btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_retry.setStyleSheet("""
                QPushButton {
                    background-color: #24190c;
                    color: #f59e0b;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 3px 10px;
                    border: 1px solid #78350f;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #78350f;
                    color: #fbbf24;
                }
            """)
            self.btn_retry.clicked.connect(self.retry_requested.emit)
            bottom_row.addWidget(self.btn_retry)

            # Quick thumbs feedback (Image 1 style)
            btn_thumb_up = QPushButton("👍")
            btn_thumb_up.setToolTip("Helpful response")
            btn_thumb_up.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_thumb_up.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #64748b;
                    border: 1px solid transparent;
                    border-radius: 4px;
                    padding: 2px 5px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #121c2d;
                    color: #38bdf8;
                }
            """)
            bottom_row.addWidget(btn_thumb_up)

            btn_thumb_down = QPushButton("👎")
            btn_thumb_down.setToolTip("Needs improvement")
            btn_thumb_down.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_thumb_down.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #64748b;
                    border: 1px solid transparent;
                    border-radius: 4px;
                    padding: 2px 5px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #121c2d;
                    color: #f87171;
                }
            """)
            bottom_row.addWidget(btn_thumb_down)

            bottom_row.addStretch()

            # Latency / tokens metrics badge
            self.lbl_metrics = QLabel()
            self.lbl_metrics.setStyleSheet("color: #64748b; font-size: 11px;")
            self._update_metrics_badge()
            bottom_row.addWidget(self.lbl_metrics)

            layout.addWidget(self.bottom_row_widget)

            # If initially empty, animate wavy loader and hide content/actions until first token
            if not self.message.content.strip():
                self.content_browser.setVisible(False)
                self.bottom_row_widget.setVisible(False)
                self.wavy_loader.start_animation()
            else:
                self.wavy_loader.stop_animation()
                self.content_browser.setVisible(True)
                self.bottom_row_widget.setVisible(True)
        else:
            self.wavy_loader.stop_animation()

    def _update_metrics_badge(self) -> None:
        """Format and display latency and token generation metrics."""
        if not hasattr(self, "lbl_metrics"):
            return
        if self.message.token_count or self.message.generation_duration_ms:
            metrics: list[str] = []
            if self.message.token_count:
                metrics.append(f"{self.message.token_count} tokens")
            if self.message.generation_duration_ms:
                sec = self.message.generation_duration_ms / 1000.0
                metrics.append(f"{sec:.1f}s")
                if self.message.token_count and sec > 0:
                    tps = self.message.token_count / sec
                    metrics.append(f"{tps:.1f} tok/s")
            self.lbl_metrics.setText("  •  ".join(metrics))
            self.lbl_metrics.setVisible(True)
        else:
            self.lbl_metrics.setVisible(False)

    def set_content(self, text: str, is_streaming: bool = False) -> None:
        """Update content safely rendering markdown, stopping wavy loader once tokens arrive."""
        self.message.content = text
        if text.strip():
            if hasattr(self, "wavy_loader") and self.wavy_loader.isVisible():
                self.wavy_loader.stop_animation()
            if not self.content_browser.isVisible():
                self.content_browser.setVisible(True)
            if hasattr(self, "bottom_row_widget") and not self.bottom_row_widget.isVisible():
                self.bottom_row_widget.setVisible(True)

            self.content_browser.setMarkdown(text)
            # Recalculate height dynamically without thrashing layout
            target_width = self.content_browser.width() if self.content_browser.width() > 100 else 760
            if self.content_browser.document().textWidth() != target_width:
                self.content_browser.document().setTextWidth(target_width)
            doc_height = int(self.content_browser.document().size().height())
            self.content_browser.setFixedHeight(max(36, doc_height + 20))

            # Only run code block regex extraction when not actively streaming
            if not is_streaming:
                self.code_blocks = extract_code_blocks(text)
                if hasattr(self, "btn_copy_code") and self.btn_copy_code is not None:
                    self.btn_copy_code.setVisible(bool(self.code_blocks))
                    self.btn_copy_code.setEnabled(True)
        else:
            if not self.is_user and hasattr(self, "wavy_loader"):
                self.content_browser.setVisible(False)
                if hasattr(self, "bottom_row_widget"):
                    self.bottom_row_widget.setVisible(False)
                self.wavy_loader.start_animation()

    def finish_generation(self, total_tokens: int | None = None, duration_ms: int | None = None) -> None:
        """Ensure wavy loader is stopped and bottom actions are visible upon completion."""
        if hasattr(self, "wavy_loader"):
            self.wavy_loader.stop_animation()
        self.content_browser.setVisible(True)
        if hasattr(self, "bottom_row_widget"):
            self.bottom_row_widget.setVisible(True)

        if total_tokens is not None:
            self.message.token_count = total_tokens
        if duration_ms is not None:
            self.message.generation_duration_ms = duration_ms
        self._update_metrics_badge()

        # Finalize code blocks extraction
        self.code_blocks = extract_code_blocks(self.message.content)
        if hasattr(self, "btn_copy_code") and self.btn_copy_code is not None:
            self.btn_copy_code.setVisible(bool(self.code_blocks))
            self.btn_copy_code.setEnabled(True)

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
