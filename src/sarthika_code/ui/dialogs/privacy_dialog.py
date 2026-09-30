"""Privacy screen dialog for Sarthika Code.

Presents explicit, honest transparency about local-first execution, zero telemetry,
local storage locations, and user data ownership.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.app.paths import AppPaths
from sarthika_code.services.chat_service import ChatService


class PrivacyDialog(QDialog):
    """Dialog detailing privacy policies, guarantees, and exact local data locations."""

    def __init__(
        self,
        paths: AppPaths,
        chat_service: ChatService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.paths = paths
        self.chat_service = chat_service

        self.setWindowTitle("Privacy & Data Guarantee — Sarthika Code")
        self.resize(680, 560)
        self.setMinimumSize(540, 440)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Header
        title_lbl = QLabel("Privacy Guarantee & Local-First Principles")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        title_lbl.setStyleSheet("color: #38bdf8;")
        layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "Sarthika Code is designed from the ground up for absolute source-code privacy. "
            "Your code, conversations, and models never leave your machine."
        )
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(sub_lbl)

        # Scroll Area for Guarantees
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #1e293b; background-color: #0f172a; border-radius: 6px; }")

        container = QWidget()
        container.setStyleSheet("background-color: #0f172a;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(14, 14, 14, 14)
        c_layout.setSpacing(12)

        # Principle Cards
        c_layout.addWidget(
            self._create_section(
                "1. No Cloud AI APIs",
                "In Version 0.1, Sarthika Code has zero cloud API integrations (no OpenAI, no Anthropic, "
                "no Gemini, no Groq). It cannot transmit your prompts to external servers."
            )
        )
        c_layout.addWidget(
            self._create_section(
                "2. Zero Telemetry & Zero Analytics",
                "There are no telemetry beacons, error-tracking pings, user analytics, tracking cookies, "
                "or advertising SDKs bundled into the codebase."
            )
        )
        c_layout.addWidget(
            self._create_section(
                "3. Localhost-Only Server Binding",
                "The managed llama-server subprocess strictly binds to 127.0.0.1 (local loopback). "
                "It refuses external network bindings, ensuring your local model is inaccessible from the local network."
            )
        )
        c_layout.addWidget(
            self._create_section(
                "4. Local SQLite Persistence",
                "All conversation histories, messages, and settings are saved in an unencrypted local SQLite database "
                "on your file system. No remote database or synchronization service is used."
            )
        )
        c_layout.addWidget(
            self._create_section(
                "5. Read-Only Context & Safe Operation",
                "Sarthika Code never modifies your source files, never runs build tools or shell commands, "
                "and never touches Git repositories. File attachments are strictly read-only and explicitly chosen by you."
            )
        )

        # Exact Paths Group
        group_paths = QGroupBox("Exact Local Data Paths on This Machine")
        group_paths.setStyleSheet("QGroupBox { color: #f8fafc; font-weight: bold; border: 1px solid #334155; margin-top: 8px; padding-top: 10px; }")
        paths_form = QFormLayout(group_paths)

        txt_db = QLineEdit(str(self.paths.database_file))
        txt_db.setReadOnly(True)
        paths_form.addRow("SQLite Database:", txt_db)

        txt_log = QLineEdit(str(self.paths.log_file))
        txt_log.setReadOnly(True)
        paths_form.addRow("Debug Log File:", txt_log)

        txt_cfg = QLineEdit(str(self.paths.config_dir))
        txt_cfg.setReadOnly(True)
        paths_form.addRow("Config Directory:", txt_cfg)

        c_layout.addWidget(group_paths)

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        # Footer Actions
        btn_row = QHBoxLayout()
        if self.chat_service is not None:
            btn_clear = QPushButton("Erase Local Chat History...")
            btn_clear.setStyleSheet("background-color: #450a0a; color: #f87171; padding: 6px 14px; font-weight: bold; border-radius: 4px;")
            btn_clear.clicked.connect(self._clear_chats)
            btn_row.addWidget(btn_clear)

        btn_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)

    def _create_section(self, title: str, text: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background-color: #1e293b; border-radius: 4px; padding: 8px; border: 1px solid #334155;")
        flayout = QVBoxLayout(frame)
        flayout.setContentsMargins(8, 6, 8, 6)
        flayout.setSpacing(4)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-weight: bold; color: #f8fafc; font-size: 11px;")
        flayout.addWidget(lbl_t)

        lbl_b = QLabel(text)
        lbl_b.setWordWrap(True)
        lbl_b.setStyleSheet("color: #cbd5e1; font-size: 11px; line-height: 1.3;")
        flayout.addWidget(lbl_b)

        return frame

    def _clear_chats(self) -> None:
        if self.chat_service is None:
            return
        reply = QMessageBox.question(
            self,
            "Clear Local History",
            "Are you sure you want to permanently delete all conversation history?\n\n"
            "This will delete all stored chats and messages from your local SQLite database.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            count = self.chat_service.clear_all_chats()
            QMessageBox.information(
                self,
                "Data Erased",
                f"Successfully deleted {count} conversation(s) from local database.",
            )
