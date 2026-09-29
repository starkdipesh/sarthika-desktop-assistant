"""PySide6 Main Window for Sarthika Code (Milestone 4 Chat Experience).

Provides the main application layout with conversation sidebar, interactive chat workspace,
local persistence, export actions, diagnostics, and server status monitoring.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QFont, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.app.paths import AppPaths
from sarthika_code.domain.server import ServerState, ServerStatus
from sarthika_code.services.chat_service import ChatService
from sarthika_code.services.diagnostics import DiagnosticsService
from sarthika_code.services.model_service import ModelService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.storage.database import DatabaseManager
from sarthika_code.ui.chat.chat_sidebar import ChatSidebar
from sarthika_code.ui.chat.chat_workspace import ChatWorkspace
from sarthika_code.ui.dialogs.diagnostics_dialog import DiagnosticsDialog
from sarthika_code.ui.dialogs.model_setup_dialog import ModelSetupDialog
from sarthika_code.ui.dialogs.provider_test_dialog import ProviderTestDialog
from sarthika_code.utils.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger("MainWindow")


class MainWindow(QMainWindow):
    """Primary application window for Sarthika Code."""

    def __init__(
        self,
        paths: AppPaths,
        settings_service: SettingsService,
        model_service: ModelService | None = None,
        diagnostics_service: DiagnosticsService | None = None,
        chat_service: ChatService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.paths = paths
        self.settings_service = settings_service
        self.model_service = model_service
        self.diagnostics_service = diagnostics_service

        if chat_service is None:
            db_mgr = getattr(settings_service, "db_manager", None) or DatabaseManager(paths.database_file)
            self.chat_service = ChatService(db_mgr)
        else:
            self.chat_service = chat_service

        self.settings = self.settings_service.load_settings()

        self.setWindowTitle("Sarthika Code — Local-First AI Coding Assistant")
        self.resize(1080, 720)
        self.setMinimumSize(800, 540)

        self._init_ui()
        self._init_status_bar()
        self._init_menu()

        # Connect server state listener if model service is active
        if self.model_service is not None:
            self.model_service.server_manager.add_state_listener(self._on_server_status_changed)
            self._update_server_status_badge(self.model_service.get_status())

        # Load chats
        self._reload_chats()

    def _init_ui(self) -> None:
        """Construct the top header and split sidebar/chat layout."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
        header_frame = QFrame()
        header_frame.setStyleSheet(
            "background-color: #0f172a; border-bottom: 1px solid #1e293b; padding: 4px 16px;"
        )
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 6, 12, 6)

        title_label = QLabel("Sarthika Code")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #f8fafc;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Mock Mode toggle button
        self.btn_toggle_mock = QPushButton("Enable Mock / Demo Mode")
        self.btn_toggle_mock.setStyleSheet(
            "background-color: #1e3a5f; color: #93c5fd; padding: 5px 12px; border-radius: 4px; font-size: 11px;"
        )
        self.btn_toggle_mock.clicked.connect(self._toggle_mock_mode)
        header_layout.addWidget(self.btn_toggle_mock)

        # Test Streaming dialog button
        self.btn_test_streaming = QPushButton("Test Provider Streaming")
        self.btn_test_streaming.setStyleSheet(
            "background-color: #0284c7; color: white; padding: 5px 12px; border-radius: 4px; font-size: 11px;"
        )
        self.btn_test_streaming.clicked.connect(self._open_provider_test)
        header_layout.addWidget(self.btn_test_streaming)

        # Action buttons on header
        if self.model_service is not None:
            self.btn_model_setup = QPushButton("Model & Server Setup")
            self.btn_model_setup.setStyleSheet(
                "background-color: #334155; color: #f1f5f9; padding: 5px 12px; border-radius: 4px; font-size: 11px;"
            )
            self.btn_model_setup.clicked.connect(self._open_model_setup)
            header_layout.addWidget(self.btn_model_setup)

        if self.diagnostics_service is not None:
            self.btn_diag = QPushButton("Diagnostics")
            self.btn_diag.setStyleSheet(
                "background-color: #334155; color: #f1f5f9; padding: 5px 12px; border-radius: 4px; font-size: 11px;"
            )
            self.btn_diag.clicked.connect(self._open_diagnostics)
            header_layout.addWidget(self.btn_diag)

        # Status badge
        self.status_badge = QLabel(" ● No Model Configured ")
        self.status_badge.setStyleSheet(
            "background-color: #3d3416; color: #f59e0b; "
            "border: 1px solid #d97706; border-radius: 4px; padding: 4px 8px; font-weight: bold; font-size: 11px;"
        )
        header_layout.addWidget(self.status_badge)

        main_layout.addWidget(header_frame)

        # Central Splitter: Sidebar + Chat Workspace
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #1e293b; width: 1px; }")

        # Left Sidebar
        self.sidebar = ChatSidebar(self.splitter)
        self.sidebar.chat_selected.connect(self._on_chat_selected)
        self.sidebar.new_chat_requested.connect(self._on_new_chat)
        self.sidebar.rename_chat_requested.connect(self._on_rename_chat)
        self.sidebar.delete_chat_requested.connect(self._on_delete_chat)
        self.sidebar.export_chat_requested.connect(self._on_export_chat)
        self.splitter.addWidget(self.sidebar)

        # Right Workspace
        self.workspace = ChatWorkspace(
            chat_service=self.chat_service,
            settings_service=self.settings_service,
            model_service=self.model_service,
            parent=self.splitter,
        )
        self.workspace.chat_title_updated.connect(self._on_title_updated)
        self.workspace.export_requested.connect(self._on_export_chat)
        self.splitter.addWidget(self.workspace)

        # Allocate 250px to sidebar and remainder to chat
        self.splitter.setSizes([250, 830])
        main_layout.addWidget(self.splitter, stretch=1)

        self._update_mock_button_label()

    def _init_status_bar(self) -> None:
        """Configure the bottom status bar."""
        bar = QStatusBar(self)
        self.setStatusBar(bar)
        db_name = self.paths.database_file.name
        bar.showMessage(
            f"Database: {db_name} | Localhost Binding: {self.settings.server_host}:{self.settings.server_port}"
        )

    def _init_menu(self) -> None:
        """Create standard application menu items."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        new_action = QAction("&New Conversation", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._on_new_chat)
        file_menu.addAction(new_action)

        export_action = QAction("&Export Conversation...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._open_export_dialog)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        if self.model_service is not None:
            setup_action = QAction("&Model & Server Setup...", self)
            setup_action.triggered.connect(self._open_model_setup)
            file_menu.addAction(setup_action)

        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")
        stream_test_action = QAction("&Test LLM Streaming...", self)
        stream_test_action.triggered.connect(self._open_provider_test)
        tools_menu.addAction(stream_test_action)

        if self.diagnostics_service is not None:
            diag_action = QAction("&System Diagnostics...", self)
            diag_action.triggered.connect(self._open_diagnostics)
            tools_menu.addAction(diag_action)

        mock_action = QAction("Toggle &Mock / Demo Mode", self)
        mock_action.triggered.connect(self._toggle_mock_mode)
        tools_menu.addAction(mock_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About Sarthika Code", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    # --------------------------------------------------------------------------
    # Chat Actions & Coordination
    # --------------------------------------------------------------------------

    def _reload_chats(self, active_chat_id: str | None = None) -> None:
        """Reload conversation list from database into sidebar."""
        chats = self.chat_service.list_chats()
        if not chats:
            # Create first initial chat
            first_chat = self.chat_service.create_chat()
            chats = [first_chat]
            active_chat_id = first_chat.id
        elif active_chat_id is None:
            active_chat_id = chats[0].id

        self.sidebar.set_chats(chats, active_chat_id=active_chat_id)
        if active_chat_id:
            self.workspace.load_chat(active_chat_id)

    def _on_chat_selected(self, chat_id: str) -> None:
        """Handle selection of a conversation in sidebar."""
        self.workspace.load_chat(chat_id)

    def _on_new_chat(self) -> None:
        """Create a fresh conversation session."""
        new_chat = self.chat_service.create_chat()
        self._reload_chats(active_chat_id=new_chat.id)

    def _on_rename_chat(self, chat_id: str, new_title: str) -> None:
        """Rename an existing conversation."""
        if self.chat_service.rename_chat(chat_id, new_title):
            self._reload_chats(active_chat_id=chat_id)

    def _on_delete_chat(self, chat_id: str) -> None:
        """Delete an existing conversation."""
        if self.chat_service.delete_chat(chat_id):
            self._reload_chats()

    def _on_title_updated(self, chat_id: str, new_title: str) -> None:
        """Handle auto-derived or updated title."""
        self._reload_chats(active_chat_id=chat_id)

    def _open_export_dialog(self) -> None:
        """Open export dialog for active conversation."""
        if self.workspace.active_chat is not None:
            self._on_export_chat(self.workspace.active_chat.id)

    def _on_export_chat(self, chat_id: str, default_format: str = "markdown") -> None:
        """Prompt user for file destination and export conversation content."""
        chat = self.chat_service.get_chat(chat_id)
        if chat is None:
            return

        clean_title = re.sub(r'[\\/*?:"<>| ]', "_", chat.title)[:30]
        ext = ".md" if default_format == "markdown" else ".txt"
        default_filename = f"{clean_title}_export{ext}"

        file_filter = "Markdown Document (*.md);;Plain Text Document (*.txt)"
        selected_filter = "Markdown Document (*.md)" if default_format == "markdown" else "Plain Text Document (*.txt)"

        file_path_str, chosen_filter = QFileDialog.getSaveFileName(
            self,
            "Export Conversation",
            default_filename,
            file_filter,
            selected_filter,
        )

        if not file_path_str:
            return

        target_path = Path(file_path_str)
        fmt = "txt" if "txt" in chosen_filter or target_path.suffix == ".txt" else "markdown"

        try:
            self.chat_service.export_chat_to_file(chat_id, target_path, file_format=fmt)
            QMessageBox.information(
                self,
                "Export Successful",
                f"Conversation successfully exported to:\n{target_path}",
            )
        except Exception as e:
            logger.error("Failed to export chat %s: %s", chat_id, e)
            QMessageBox.critical(self, "Export Failed", f"Could not export conversation: {e}")

    # --------------------------------------------------------------------------
    # Dialogs & Status Handlers
    # --------------------------------------------------------------------------

    def _open_provider_test(self) -> None:
        """Open the Provider Streaming Test Dialog."""
        server_mgr = self.model_service.server_manager if self.model_service is not None else None
        dialog = ProviderTestDialog(
            settings_service=self.settings_service,
            server_manager=server_mgr,
            parent=self,
        )
        dialog.exec()
        self.settings = self.settings_service.load_settings()
        self._update_mock_button_label()

    def _open_model_setup(self) -> None:
        """Open the Model Setup Dialog."""
        if self.model_service is not None:
            dialog = ModelSetupDialog(
                model_service=self.model_service,
                settings_service=self.settings_service,
                on_open_diagnostics=self._open_diagnostics,
                parent=self,
            )
            dialog.exec()
            self.settings = self.settings_service.load_settings()
            self._update_mock_button_label()

    def _open_diagnostics(self) -> None:
        """Open the System Diagnostics Dialog."""
        if self.diagnostics_service is not None:
            dialog = DiagnosticsDialog(
                diagnostics_service=self.diagnostics_service,
                parent=self,
            )
            dialog.exec()

    def _update_mock_button_label(self) -> None:
        """Synchronize button text and badge with active mock setting."""
        if self.settings.mock_mode:
            self.btn_toggle_mock.setText("Disable Mock Mode")
            self.status_badge.setText(" ● Mock Mode Active ")
            self.status_badge.setStyleSheet(
                "background-color: #1e3a5f; color: #60a5fa; "
                "border: 1px solid #3b82f6; border-radius: 4px; padding: 4px 8px; font-weight: bold; font-size: 11px;"
            )
        else:
            self.btn_toggle_mock.setText("Enable Mock / Demo Mode")
            if self.model_service is not None:
                self._update_server_status_badge(self.model_service.get_status())
            else:
                self.status_badge.setText(" ● No Model Configured ")
                self.status_badge.setStyleSheet(
                    "background-color: #3d3416; color: #f59e0b; "
                    "border: 1px solid #d97706; border-radius: 4px; padding: 4px 8px; font-weight: bold; font-size: 11px;"
                )

    def _update_server_status_badge(self, status: ServerStatus) -> None:
        """Update status badge color and text according to ServerStatus."""
        if self.settings.mock_mode:
            return

        if status.state == ServerState.READY:
            self.status_badge.setText(f" ● Ready ({status.url or 'local'}) ")
            self.status_badge.setStyleSheet(
                "background-color: #14532d; color: #4ade80; "
                "border: 1px solid #16a34a; border-radius: 4px; padding: 4px 8px; font-weight: bold; font-size: 11px;"
            )
        elif status.state == ServerState.STARTING:
            self.status_badge.setText(" ● Server Starting... ")
            self.status_badge.setStyleSheet(
                "background-color: #713f12; color: #facc15; "
                "border: 1px solid #ca8a04; border-radius: 4px; padding: 4px 8px; font-weight: bold; font-size: 11px;"
            )
        elif status.state == ServerState.GENERATING:
            self.status_badge.setText(" ● Generating Response... ")
            self.status_badge.setStyleSheet(
                "background-color: #1e3a5f; color: #38bdf8; "
                "border: 1px solid #0284c7; border-radius: 4px; padding: 4px 8px; font-weight: bold; font-size: 11px;"
            )
        elif status.state in (ServerState.START_FAILED, ServerState.CRASHED, ServerState.UNAVAILABLE):
            self.status_badge.setText(f" ● Server {status.state.value} ")
            self.status_badge.setStyleSheet(
                "background-color: #450a0a; color: #f87171; "
                "border: 1px solid #dc2626; border-radius: 4px; padding: 4px 8px; font-weight: bold; font-size: 11px;"
            )
        else:  # STOPPED
            self.status_badge.setText(" ● No Model Configured ")
            self.status_badge.setStyleSheet(
                "background-color: #3d3416; color: #f59e0b; "
                "border: 1px solid #d97706; border-radius: 4px; padding: 4px 8px; font-weight: bold; font-size: 11px;"
            )

    def _on_server_status_changed(self, status: ServerStatus) -> None:
        """Callback invoked when server manager status transitions."""
        self._update_server_status_badge(status)

    def _toggle_mock_mode(self) -> None:
        """Toggle between mock mode and real server mode."""
        self.settings.mock_mode = not self.settings.mock_mode
        self.settings_service.save_settings(self.settings)
        self._update_mock_button_label()
        state_str = "enabled" if self.settings.mock_mode else "disabled"
        logger.info("Mock mode %s by user.", state_str)

        # Refresh workspace message cards
        if self.workspace.active_chat is not None:
            self.workspace.load_chat(self.workspace.active_chat.id)

    def _show_about_dialog(self) -> None:
        """Display the application information dialog."""
        QMessageBox.about(
            self,
            "About Sarthika Code",
            "<b>Sarthika Code v0.1</b><br><br>"
            "A private, local-first desktop AI coding assistant.<br>"
            "Runs on your CPU using local GGUF models via llama.cpp.<br><br>"
            "License: Apache-2.0<br>"
            "Zero Cloud APIs • Zero Telemetry • 100% Local",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle clean, graceful application shutdown."""
        logger.info("Main window close event received. Initiating graceful shutdown.")
        self.workspace.cancel_generation()

        if self.model_service is not None and self.model_service.server_manager.status.state in (
            ServerState.STARTING,
            ServerState.READY,
            ServerState.GENERATING,
        ):
            logger.info("Stopping managed llama-server subprocess...")
            self.model_service.stop_server()
        event.accept()
