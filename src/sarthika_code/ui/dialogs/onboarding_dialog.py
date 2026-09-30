"""First-launch onboarding and welcome dialog for Sarthika Code.

Provides transparent explanations of local-first execution, prerequisites,
privacy guarantees, and code verification responsibilities.
"""

from __future__ import annotations

import webbrowser
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.app.paths import AppPaths
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.utils.logging import get_logger

logger = get_logger("OnboardingDialog")


class OnboardingDialog(QDialog):
    """First-launch onboarding dialog introducing Sarthika Code and guiding initial setup."""

    def __init__(
        self,
        settings_service: SettingsService,
        paths: AppPaths | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings_service = settings_service
        self.paths = paths
        self.user_choice: str | None = None  # 'configure_model', 'mock_mode', or 'docs'

        self.setWindowTitle("Welcome to Sarthika Code")
        self.resize(720, 600)
        self.setMinimumSize(600, 480)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header Title
        title_label = QLabel("Welcome to Sarthika Code")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #38bdf8;")
        layout.addWidget(title_label)

        subtitle_label = QLabel(
            "A private, local-first desktop AI coding assistant that runs entirely on your computer."
        )
        subtitle_label.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(subtitle_label)

        # Scrollable Content Cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: 1px solid #1e293b; background-color: #0f172a; border-radius: 6px; }")

        container = QWidget()
        container.setStyleSheet("background-color: #0f172a;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(14)

        # Card 1: Local-First & 100% Privacy
        card1 = self._create_card(
            "🔒 100% Local-First & Absolute Privacy",
            "• Zero Cloud APIs: No requests are ever sent to OpenAI, Anthropic, or external cloud servers.\n"
            "• Zero Telemetry: No tracking, analytics beacons, user accounts, or advertisements.\n"
            "• Local Inference: All prompt evaluation runs on your local CPU via llama-server on localhost (127.0.0.1).\n"
            "• Local Storage: Conversations, code snippets, and settings are saved locally in SQLite.",
        )
        container_layout.addWidget(card1)

        # Card 2: Requirements & No Bundled Model
        card2 = self._create_card(
            "⚙️ Requirements & Model Weights",
            "• GGUF Model Required: Sarthika Code uses quantized GGUF models (e.g. Qwen2.5-Coder 3B Instruct Q4_K_M).\n"
            "• llama-server Binary Required: Needs the pre-compiled llama-server executable from llama.cpp.\n"
            "• No Model Bundled: Model weights are not bundled with the application to respect licensing and keep downloads small.\n"
            "• Try Mock Mode Anytime: You can immediately test the UI, streaming, and workflows using Offline Mock Mode without downloading model weights.",
        )
        container_layout.addWidget(card2)

        # Card 3: Safety & Code Verification
        card3 = self._create_card(
            "⚠️ Safety, Non-Destructive Operation & Review",
            "• Non-Destructive: Sarthika Code never modifies your files, never runs terminal commands, and never makes Git operations.\n"
            "• Explicit Context: The assistant only reads files that you explicitly attach in the Context panel.\n"
            "• Code Verification: Small local models can make mistakes or hallucinate syntax. Generated code is an assistive suggestion and always requires your review and testing.",
        )
        container_layout.addWidget(card3)

        container_layout.addStretch()
        scroll_area.setWidget(container)
        layout.addWidget(scroll_area, stretch=1)

        # Don't show again checkbox
        self.chk_dont_show = QCheckBox("Mark onboarding as completed (don't show on startup)")
        self.chk_dont_show.setChecked(True)
        self.chk_dont_show.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(self.chk_dont_show)

        # Action Buttons Row
        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        btn_docs = QPushButton("Open Documentation")
        btn_docs.setStyleSheet(
            "background-color: #334155; color: #f1f5f9; padding: 8px 14px; font-weight: bold; border-radius: 4px;"
        )
        btn_docs.clicked.connect(self._on_open_docs)
        button_row.addWidget(btn_docs)

        button_row.addStretch()

        btn_mock = QPushButton("Use Mock / Demo Mode")
        btn_mock.setStyleSheet(
            "background-color: #1e3a5f; color: #93c5fd; padding: 8px 16px; font-weight: bold; border-radius: 4px; border: 1px solid #3b82f6;"
        )
        btn_mock.clicked.connect(self._on_choose_mock)
        button_row.addWidget(btn_mock)

        btn_setup = QPushButton("Configure Local Model")
        btn_setup.setStyleSheet(
            "background-color: #2563eb; color: white; padding: 8px 18px; font-weight: bold; border-radius: 4px;"
        )
        btn_setup.clicked.connect(self._on_choose_setup)
        button_row.addWidget(btn_setup)

        layout.addLayout(button_row)

    def _create_card(self, title: str, text: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: #1e293b; border-radius: 6px; padding: 10px; border: 1px solid #334155;"
        )
        card_layout = QVBoxLayout(frame)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_lbl.setFont(title_font)
        title_lbl.setStyleSheet("color: #f8fafc;")
        card_layout.addWidget(title_lbl)

        content_lbl = QLabel(text)
        content_lbl.setWordWrap(True)
        content_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px; line-height: 1.4;")
        card_layout.addWidget(content_lbl)

        return frame

    def _save_completion_state(self) -> None:
        """Record onboarding completion in settings if requested."""
        if self.chk_dont_show.isChecked():
            settings = self.settings_service.load_settings()
            settings.onboarding_completed = True
            self.settings_service.save_settings(settings)
            logger.info("Onboarding marked as completed.")

    def _on_choose_setup(self) -> None:
        self.user_choice = "configure_model"
        self._save_completion_state()
        self.accept()

    def _on_choose_mock(self) -> None:
        self.user_choice = "mock_mode"
        settings = self.settings_service.load_settings()
        settings.mock_mode = True
        settings.onboarding_completed = True
        self.settings_service.save_settings(settings)
        logger.info("Mock mode enabled from onboarding dialog.")
        self.accept()

    def _on_open_docs(self) -> None:
        self.user_choice = "docs"
        doc_path = Path("docs/installation.md").resolve()
        if doc_path.exists():
            webbrowser.open(doc_path.as_uri())
        else:
            readme_path = Path("README.md").resolve()
            if readme_path.exists():
                webbrowser.open(readme_path.as_uri())
