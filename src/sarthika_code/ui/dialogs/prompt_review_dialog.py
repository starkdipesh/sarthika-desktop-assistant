"""Dialog for inspecting final constructed prompts in developer debug mode.

Allows developers to verify delimiters, injection mitigation, and safety instructions
before or during generation. Hidden from standard users by default.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class PromptReviewDialog(QDialog):
    """Developer-facing inspector for reviewing constructed system prompts and message buffers."""

    def __init__(self, prompt_data: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.prompt_data = prompt_data
        self.setWindowTitle("Workflow Prompt Review — Developer Debug Mode")
        self.resize(750, 560)
        self.setMinimumSize(600, 400)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header with debug badge
        header_layout = QHBoxLayout()
        title_lbl = QLabel(f"Workflow: {self.prompt_data.get('workflow_name', 'General Chat')}")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        title_lbl.setStyleSheet("color: #f8fafc;")
        header_layout.addWidget(title_lbl)

        header_layout.addStretch()

        debug_badge = QLabel(" DEBUG MODE ONLY ")
        debug_badge.setStyleSheet(
            "background-color: #7c2d12; color: #fdba74; border: 1px solid #ea580c; "
            "border-radius: 4px; padding: 2px 6px; font-weight: bold; font-size: 10px;"
        )
        header_layout.addWidget(debug_badge)
        layout.addLayout(header_layout)

        # Info line
        workflow_id = self.prompt_data.get("workflow_id", "explain_code")
        info_lbl = QLabel(
            f"Workflow ID: <code>{workflow_id}</code> | "
            f"Safety Invariants: <b>Enforced</b> | Delimiters: <b>Active</b>"
        )
        info_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(info_lbl)

        # Tab widget for different views
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #1e293b; background-color: #030712; }
            QTabBar::tab { background-color: #0f172a; color: #94a3b8; padding: 6px 12px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #1e293b; color: #f8fafc; font-weight: bold; }
        """)

        # Tab 1: Full Combined Prompt
        tab_full = QWidget()
        full_layout = QVBoxLayout(tab_full)
        txt_full = QPlainTextEdit()
        txt_full.setReadOnly(True)
        txt_full.setPlainText(self.prompt_data.get("raw_text", self.prompt_data.get("full_debug_view", "")))
        txt_full.setFont(QFont("Monospace", 10))
        txt_full.setStyleSheet("background-color: #030712; color: #e2e8f0; border: none; padding: 8px;")
        full_layout.addWidget(txt_full)
        tabs.addTab(tab_full, "Full Constructed Buffer")

        # Tab 2: System Prompt
        tab_sys = QWidget()
        sys_layout = QVBoxLayout(tab_sys)
        txt_sys = QPlainTextEdit()
        txt_sys.setReadOnly(True)
        txt_sys.setPlainText(self.prompt_data.get("system_prompt", ""))
        txt_sys.setFont(QFont("Monospace", 10))
        txt_sys.setStyleSheet("background-color: #030712; color: #38bdf8; border: none; padding: 8px;")
        sys_layout.addWidget(txt_sys)
        tabs.addTab(tab_sys, "System Prompt & Safety Rules")

        layout.addWidget(tabs, stretch=1)

        # Footer button row
        footer_layout = QHBoxLayout()
        btn_copy = QPushButton("Copy Full Prompt")
        btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(txt_full.toPlainText()))
        footer_layout.addWidget(btn_copy)

        footer_layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: white;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        btn_close.clicked.connect(self.accept)
        footer_layout.addWidget(btn_close)

        layout.addLayout(footer_layout)
