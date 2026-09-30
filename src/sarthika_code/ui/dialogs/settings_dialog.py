"""Comprehensive Settings dialog for Sarthika Code.

Provides configuration for model paths, llama-server runtime, conservative generation defaults,
local data management, and lightweight appearance preferences.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.app.paths import AppPaths
from sarthika_code.domain.config import AppSettings
from sarthika_code.domain.errors import ConfigurationError, SarthikaError
from sarthika_code.services.chat_service import ChatService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.utils.logging import get_logger

logger = get_logger("SettingsDialog")


class SettingsDialog(QDialog):
    """Multi-tab application settings dialog for Sarthika Code."""

    def __init__(
        self,
        settings_service: SettingsService,
        chat_service: ChatService | None = None,
        paths: AppPaths | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings_service = settings_service
        self.chat_service = chat_service
        self.paths = paths
        self.settings = self.settings_service.load_settings()

        self.setWindowTitle("Settings & Preferences — Sarthika Code")
        self.resize(680, 520)
        self.setMinimumSize(560, 420)

        self._init_ui()
        self._load_current_values()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #334155; background-color: #0f172a; border-radius: 4px; }
            QTabBar::tab { background: #1e293b; color: #94a3b8; padding: 8px 16px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: #0f172a; color: #38bdf8; font-weight: bold; border-top: 2px solid #38bdf8; }
        """)

        # Tab 1: Model & Server
        tab_model = QWidget()
        self._init_model_tab(tab_model)
        self.tabs.addTab(tab_model, "Model & Server")

        # Tab 2: Generation Defaults (Advanced)
        tab_gen = QWidget()
        self._init_generation_tab(tab_gen)
        self.tabs.addTab(tab_gen, "Generation Defaults")

        # Tab 3: Local Data Management
        tab_data = QWidget()
        self._init_data_tab(tab_data)
        self.tabs.addTab(tab_data, "Data Management")

        # Tab 4: Appearance
        tab_ui = QWidget()
        self._init_appearance_tab(tab_ui)
        self.tabs.addTab(tab_ui, "Appearance")

        main_layout.addWidget(self.tabs, stretch=1)

        # Footer Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_reset = QPushButton("Reset to Defaults")
        self.btn_reset.setStyleSheet("background-color: #334155; color: #f1f5f9; padding: 6px 12px; border-radius: 4px;")
        self.btn_reset.clicked.connect(self._reset_defaults)
        btn_row.addWidget(self.btn_reset)

        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save & Apply")
        self.btn_save.setStyleSheet("background-color: #2563eb; color: white; padding: 6px 18px; font-weight: bold; border-radius: 4px;")
        self.btn_save.clicked.connect(self._save_settings)
        btn_row.addWidget(self.btn_save)

        main_layout.addLayout(btn_row)

    # --------------------------------------------------------------------------
    # Tab Builders
    # --------------------------------------------------------------------------

    def _init_model_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Model file
        lbl_model = QLabel("Local GGUF Model Path:")
        lbl_model.setStyleSheet("font-weight: bold; color: #f8fafc;")
        layout.addWidget(lbl_model)

        row_model = QHBoxLayout()
        self.txt_model_path = QLineEdit()
        self.txt_model_path.setPlaceholderText("Path to local .gguf model file")
        row_model.addWidget(self.txt_model_path)

        btn_browse_model = QPushButton("Browse...")
        btn_browse_model.clicked.connect(self._browse_model)
        row_model.addWidget(btn_browse_model)
        layout.addLayout(row_model)

        # llama-server executable
        lbl_exec = QLabel("llama-server Binary Path:")
        lbl_exec.setStyleSheet("font-weight: bold; color: #f8fafc;")
        layout.addWidget(lbl_exec)

        row_exec = QHBoxLayout()
        self.txt_exec_path = QLineEdit()
        self.txt_exec_path.setPlaceholderText("Path to llama-server or llama-server.exe")
        row_exec.addWidget(self.txt_exec_path)

        btn_browse_exec = QPushButton("Browse...")
        btn_browse_exec.clicked.connect(self._browse_exec)
        row_exec.addWidget(btn_browse_exec)
        layout.addLayout(row_exec)

        # Port, Threads & Context
        form_row = QHBoxLayout()

        col_port = QVBoxLayout()
        lbl_port = QLabel("Local Port (1024-65535):")
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        col_port.addWidget(lbl_port)
        col_port.addWidget(self.spin_port)
        form_row.addLayout(col_port)

        col_threads = QVBoxLayout()
        lbl_threads = QLabel("CPU Threads:")
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 32)
        col_threads.addWidget(lbl_threads)
        col_threads.addWidget(self.spin_threads)
        form_row.addLayout(col_threads)

        col_ctx = QVBoxLayout()
        lbl_ctx = QLabel("Context Window Preset:")
        self.cmb_context = QComboBox()
        self.cmb_context.addItem("2048 tokens (Low-Memory / 8 GB RAM)", 2048)
        self.cmb_context.addItem("4096 tokens (Standard Recommended)", 4096)
        self.cmb_context.addItem("8192 tokens (Optional)", 8192)
        self.cmb_context.addItem("16384 tokens (Advanced / High RAM)", 16384)
        self.cmb_context.addItem("32768 tokens (Maximum / Heavy CPU)", 32768)
        self.cmb_context.currentIndexChanged.connect(self._on_context_changed)
        col_ctx.addWidget(lbl_ctx)
        col_ctx.addWidget(self.cmb_context)
        form_row.addLayout(col_ctx)

        layout.addLayout(form_row)

        self.lbl_ctx_advisory = QLabel("")
        self.lbl_ctx_advisory.setStyleSheet("color: #eab308; font-size: 11px; font-weight: bold;")
        layout.addWidget(self.lbl_ctx_advisory)

        # Mock Mode toggle
        self.chk_mock_mode = QCheckBox("Enable Offline Mock / Demo Mode (Test UI without model weights)")
        self.chk_mock_mode.setStyleSheet("color: #93c5fd; font-weight: bold; margin-top: 6px;")
        layout.addWidget(self.chk_mock_mode)

        layout.addStretch()

    def _init_generation_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        banner = QFrame()
        banner.setStyleSheet("background-color: #1e293b; border-left: 3px solid #38bdf8; padding: 8px; border-radius: 4px;")
        banner_layout = QVBoxLayout(banner)
        banner_lbl = QLabel(
            "⚙️ Advanced Generation Controls\n"
            "Defaults are conservatively tuned for code generation. Higher context presets and max token "
            "limits increase memory allocation (KV cache) and CPU inference duration."
        )
        banner_lbl.setWordWrap(True)
        banner_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px; line-height: 1.4;")
        banner_layout.addWidget(banner_lbl)
        layout.addWidget(banner)

        form = QFormLayout()
        form.setSpacing(12)

        # Temperature
        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(0.0, 2.0)
        self.spin_temp.setSingleStep(0.05)
        self.spin_temp.setDecimals(2)
        self.spin_temp.setToolTip("Lower values (0.1-0.3) produce more deterministic, focused code. Higher values increase randomness.")
        form.addRow("Temperature (0.0 - 2.0):", self.spin_temp)

        # Top-P
        self.spin_top_p = QDoubleSpinBox()
        self.spin_top_p.setRange(0.1, 1.0)
        self.spin_top_p.setSingleStep(0.05)
        self.spin_top_p.setDecimals(2)
        self.spin_top_p.setToolTip("Nucleus sampling threshold. Recommended: 0.8.")
        form.addRow("Top-P (0.1 - 1.0):", self.spin_top_p)

        # Max Tokens
        self.spin_max_tokens = QSpinBox()
        self.spin_max_tokens.setRange(128, 16384)
        self.spin_max_tokens.setSingleStep(128)
        self.spin_max_tokens.setToolTip("Maximum number of tokens generated per turn. Recommended: 2048.")
        form.addRow("Max Tokens (128 - 16,384):", self.spin_max_tokens)

        # Repeat Penalty
        self.spin_repeat_penalty = QDoubleSpinBox()
        self.spin_repeat_penalty.setRange(1.0, 2.0)
        self.spin_repeat_penalty.setSingleStep(0.05)
        self.spin_repeat_penalty.setDecimals(2)
        self.spin_repeat_penalty.setToolTip("Penalizes repetitive loops in model output. Recommended: 1.1.")
        form.addRow("Repeat Penalty (1.0 - 2.0):", self.spin_repeat_penalty)

        layout.addLayout(form)
        layout.addStretch()

    def _init_data_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        group_paths = QGroupBox("Local Storage Paths (100% Local)")
        paths_layout = QFormLayout(group_paths)

        db_path = str(self.paths.database_file) if self.paths else "default"
        log_path = str(self.paths.log_file) if self.paths else "default"
        cfg_path = str(self.paths.config_dir) if self.paths else "default"

        txt_db = QLineEdit(db_path)
        txt_db.setReadOnly(True)
        paths_layout.addRow("SQLite Database:", txt_db)

        txt_log = QLineEdit(log_path)
        txt_log.setReadOnly(True)
        paths_layout.addRow("Application Log:", txt_log)

        txt_cfg = QLineEdit(cfg_path)
        txt_cfg.setReadOnly(True)
        paths_layout.addRow("Configuration Dir:", txt_cfg)

        layout.addWidget(group_paths)

        # Actions
        group_actions = QGroupBox("Data Privacy & Erasure")
        actions_layout = QVBoxLayout(group_actions)

        lbl_desc = QLabel(
            "You have complete sovereignty over your data. All chats and context records are stored strictly on this machine."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        actions_layout.addWidget(lbl_desc)

        btn_clear_chats = QPushButton("Clear All Conversation History...")
        btn_clear_chats.setStyleSheet("background-color: #450a0a; color: #f87171; padding: 6px 12px; font-weight: bold; border-radius: 4px;")
        btn_clear_chats.clicked.connect(self._clear_all_chats)
        actions_layout.addWidget(btn_clear_chats)

        layout.addWidget(group_actions)
        layout.addStretch()

    def _init_appearance_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        lbl_theme = QLabel("Theme Selection:")
        lbl_theme.setStyleSheet("font-weight: bold; color: #f8fafc;")
        layout.addWidget(lbl_theme)

        self.cmb_theme = QComboBox()
        self.cmb_theme.addItem("Dark Theme (Default & Optimized for Contrast)", "dark")
        self.cmb_theme.addItem("Light Theme", "light")
        self.cmb_theme.addItem("System Default", "system")
        layout.addWidget(self.cmb_theme)

        lbl_note = QLabel(
            "Note: Sarthika Code uses lightweight stylesheet theming to preserve CPU performance."
        )
        lbl_note.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(lbl_note)

        layout.addStretch()

    # --------------------------------------------------------------------------
    # Handlers & Values
    # --------------------------------------------------------------------------

    def _load_current_values(self) -> None:
        """Populate widgets with active preferences from self.settings."""
        self.txt_model_path.setText(self.settings.model_path or "")
        self.txt_exec_path.setText(self.settings.llama_server_path or "")
        self.spin_port.setValue(self.settings.server_port)
        self.spin_threads.setValue(self.settings.threads)

        idx = self.cmb_context.findData(self.settings.context_size)
        if idx >= 0:
            self.cmb_context.setCurrentIndex(idx)
        else:
            self.cmb_context.setCurrentIndex(1)
        self._on_context_changed()

        self.chk_mock_mode.setChecked(self.settings.mock_mode)

        self.spin_temp.setValue(self.settings.temperature)
        self.spin_top_p.setValue(self.settings.top_p)
        self.spin_max_tokens.setValue(self.settings.max_tokens)
        self.spin_repeat_penalty.setValue(self.settings.repeat_penalty)

        theme_idx = self.cmb_theme.findData(self.settings.theme)
        if theme_idx >= 0:
            self.cmb_theme.setCurrentIndex(theme_idx)

    def _browse_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Local GGUF Model",
            str(Path.home()),
            "GGUF Models (*.gguf);;All Files (*)",
        )
        if path:
            self.txt_model_path.setText(path)

    def _browse_exec(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select llama-server Executable",
            str(Path.home()),
            "Executables (*.exe llama-server*);;All Files (*)",
        )
        if path:
            self.txt_exec_path.setText(path)

    def _on_context_changed(self) -> None:
        ctx = int(self.cmb_context.currentData())
        if ctx >= 16384:
            self.lbl_ctx_advisory.setText(
                "⚠️ Warning: Context sizes >= 16,384 tokens consume substantial RAM for the KV-cache and may slow CPU inference."
            )
        elif ctx >= 8192:
            self.lbl_ctx_advisory.setText(
                "Notice: 8,192 tokens requires >= 16 GB RAM for comfortable CPU inference."
            )
        elif ctx == 2048:
            self.lbl_ctx_advisory.setText(
                "Info: 2,048 tokens is the low-memory mode recommended for 8 GB RAM systems."
            )
        else:
            self.lbl_ctx_advisory.setText("")

    def _save_settings(self, show_confirmation: bool = True) -> None:
        """Validate inputs and persist to SQLite."""
        updated = AppSettings(
            theme=str(self.cmb_theme.currentData()),
            model_path=self.txt_model_path.text().strip() or None,
            llama_server_path=self.txt_exec_path.text().strip() or None,
            server_host="127.0.0.1",
            server_port=self.spin_port.value(),
            context_size=int(self.cmb_context.currentData()),
            mock_mode=self.chk_mock_mode.isChecked(),
            threads=self.spin_threads.value(),
            debug_mode=self.settings.debug_mode,
            temperature=round(self.spin_temp.value(), 2),
            top_p=round(self.spin_top_p.value(), 2),
            max_tokens=self.spin_max_tokens.value(),
            repeat_penalty=round(self.spin_repeat_penalty.value(), 2),
            onboarding_completed=self.settings.onboarding_completed,
        )

        try:
            self.settings_service.save_settings(updated)
            self.settings = updated
            if show_confirmation:
                QMessageBox.information(self, "Settings Saved", "Preferences updated successfully.")
            self.accept()
        except ConfigurationError as e:
            if show_confirmation:
                QMessageBox.warning(self, "Invalid Configuration", e.format_for_user())
            raise
        except Exception as e:
            if show_confirmation:
                QMessageBox.critical(self, "Error Saving Settings", str(e))
            raise

    def _reset_defaults(self) -> None:
        """Prompt confirmation and restore factory defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to conservative defaults?\n\n"
            "This will reset context size to 4,096 tokens, port to 8080, and generation defaults.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings = self.settings_service.reset_settings()
            self._load_current_values()
            QMessageBox.information(self, "Settings Reset", "Settings have been restored to safe defaults.")

    def _clear_all_chats(self) -> None:
        """Prompt confirmation and erase all chat history."""
        if self.chat_service is None:
            return

        reply = QMessageBox.question(
            self,
            "Clear All Conversations",
            "Are you sure you want to permanently erase ALL conversation history?\n\n"
            "This action cannot be undone. All messages and context links will be deleted from your local SQLite database.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                count = self.chat_service.clear_all_chats()
                QMessageBox.information(
                    self,
                    "History Cleared",
                    f"Successfully deleted {count} conversation(s) from local database.",
                )
            except SarthikaError as e:
                QMessageBox.critical(self, "Clear Failed", e.format_for_user())
            except Exception as e:
                QMessageBox.critical(self, "Clear Failed", str(e))
