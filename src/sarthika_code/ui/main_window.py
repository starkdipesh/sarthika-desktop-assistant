"""PySide6 Main Window for Sarthika Code (Milestone 4 Chat Experience).

Provides the main application layout with conversation sidebar, interactive chat workspace,
local persistence, export actions, diagnostics, and server status monitoring.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QCloseEvent, QFont, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.app.paths import AppPaths
from sarthika_code.domain.server import ServerState, ServerStatus
from sarthika_code.prompts.registry import WorkflowRegistry
from sarthika_code.services.auth_service import LocalAuthService
from sarthika_code.services.chat_service import ChatService
from sarthika_code.services.context_service import ProjectContextService
from sarthika_code.services.diagnostics import DiagnosticsService
from sarthika_code.services.model_service import ModelService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.storage.database import DatabaseManager
from sarthika_code.ui.chat.chat_sidebar import ChatSidebar
from sarthika_code.ui.chat.chat_workspace import ChatWorkspace
from sarthika_code.ui.dialogs.auth_dialog import SetPinDialog
from sarthika_code.ui.dialogs.diagnostics_dialog import DiagnosticsDialog
from sarthika_code.ui.dialogs.limitations_dialog import LimitationsDialog
from sarthika_code.ui.dialogs.model_setup_dialog import ModelSetupDialog
from sarthika_code.ui.dialogs.onboarding_dialog import OnboardingDialog
from sarthika_code.ui.dialogs.privacy_dialog import PrivacyDialog
from sarthika_code.ui.dialogs.prompt_review_dialog import PromptReviewDialog
from sarthika_code.ui.dialogs.provider_test_dialog import ProviderTestDialog
from sarthika_code.ui.dialogs.settings_dialog import SettingsDialog
from sarthika_code.ui.dialogs.setup_wizard_dialog import SetupWizardDialog
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
        context_service: ProjectContextService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.paths = paths
        self.settings_service = settings_service
        self.model_service = model_service
        self.diagnostics_service = diagnostics_service

        db_mgr = getattr(settings_service, "db_manager", None) or DatabaseManager(paths.database_file)
        if chat_service is None:
            self.chat_service = ChatService(db_mgr)
        else:
            self.chat_service = chat_service

        if context_service is None:
            self.context_service = ProjectContextService(db_mgr)
        else:
            self.context_service = context_service

        self.auth_service = LocalAuthService(self.settings_service)
        self.settings = self.settings_service.load_settings()

        self.setWindowTitle("Sarthika Code — Local-First AI Coding Assistant")
        self.resize(1080, 720)
        self.setMinimumSize(800, 540)

        self._init_ui()
        self.sidebar.set_user_profile(self.settings.user_name)
        self._init_status_bar()
        self._init_menu()

        # Connect server state listener if model service is active
        if self.model_service is not None:
            self.model_service.server_manager.add_state_listener(self._on_server_status_changed)
            self._update_server_status_badge(self.model_service.get_status())

        # Load chats
        self._reload_chats()

        # Check first-launch onboarding
        if not self.settings.onboarding_completed:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._check_first_launch_onboarding)

    def _init_ui(self) -> None:
        """Construct the top header and split sidebar/chat layout."""
        self.setStyleSheet("QMainWindow { background-color: #080b13; }")

        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        central_widget.setStyleSheet("background-color: #080b13;")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
        header_frame = QFrame()
        header_frame.setStyleSheet(
            "background-color: #080b13; border-bottom: 1px solid #151c28; padding: 4px 14px;"
        )
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 6, 8, 6)
        header_layout.setSpacing(8)

        # Sidebar toggle button
        self.btn_toggle_sidebar = QPushButton("☰")
        self.btn_toggle_sidebar.setToolTip("Toggle Sidebar (Ctrl+B)")
        self.btn_toggle_sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_sidebar.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: 1px solid #1e2d4a;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #111d33;
                color: #f1f5f9;
                border-color: #0284c7;
            }
        """)
        self.btn_toggle_sidebar.clicked.connect(self._toggle_sidebar)
        header_layout.addWidget(self.btn_toggle_sidebar)

        title_label = QLabel("✦ Sarthika Code")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #38bdf8; letter-spacing: 0.3px;")
        header_layout.addWidget(title_label)

        lbl_privacy_tag = QLabel("🔒 Local & Private")
        lbl_privacy_tag.setStyleSheet("color: #475569; font-size: 11px; margin-left: 4px;")
        header_layout.addWidget(lbl_privacy_tag)

        header_layout.addStretch()

        # Developer & Engine Tools Pill Dock
        tools_frame = QFrame()
        tools_frame.setStyleSheet("""
            QFrame {
                background-color: #0c121e;
                border: 1px solid #182236;
                border-radius: 8px;
            }
        """)
        tools_layout = QHBoxLayout(tools_frame)
        tools_layout.setContentsMargins(4, 2, 4, 2)
        tools_layout.setSpacing(4)

        # Mock Mode toggle button
        self.btn_toggle_mock = QPushButton("Enable Mock / Demo Mode")
        self.btn_toggle_mock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_mock.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #7dd3fc;
                border: none;
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #122442;
                color: #ffffff;
            }
        """)
        self.btn_toggle_mock.clicked.connect(self._toggle_mock_mode)
        tools_layout.addWidget(self.btn_toggle_mock)

        # Test Streaming dialog button
        self.btn_test_streaming = QPushButton("Test Provider Streaming")
        self.btn_test_streaming.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_test_streaming.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: none;
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #162238;
                color: #f1f5f9;
            }
        """)
        self.btn_test_streaming.clicked.connect(self._open_provider_test)
        tools_layout.addWidget(self.btn_test_streaming)

        # Action buttons on header
        if self.model_service is not None:
            self.btn_model_setup = QPushButton("Model & Server Setup")
            self.btn_model_setup.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_model_setup.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #94a3b8;
                    border: none;
                    padding: 4px 10px;
                    border-radius: 6px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #162238;
                    color: #f1f5f9;
                }
            """)
            self.btn_model_setup.clicked.connect(self._open_model_setup)
            tools_layout.addWidget(self.btn_model_setup)

        if self.diagnostics_service is not None:
            self.btn_diag = QPushButton("Diagnostics")
            self.btn_diag.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_diag.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #94a3b8;
                    border: none;
                    padding: 4px 10px;
                    border-radius: 6px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #162238;
                    color: #f1f5f9;
                }
            """)
            self.btn_diag.clicked.connect(self._open_diagnostics)
            tools_layout.addWidget(self.btn_diag)

        header_layout.addWidget(tools_frame)

        # Status badge (clickable pill to configure model)
        self.status_badge = QLabel(" ● No Model Configured ")
        self.status_badge.setToolTip("Server & Model Status (Click to open setup)")
        self.status_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_badge.mousePressEvent = lambda ev: self._open_model_setup()  # type: ignore[assignment]
        self.status_badge.setStyleSheet("""
            background-color: #24190c;
            color: #f59e0b;
            border: 1px solid #78350f;
            border-radius: 8px;
            padding: 5px 12px;
            font-weight: 600;
            font-size: 11px;
        """)
        header_layout.addWidget(self.status_badge)

        # Quick New Chat icon button
        self.btn_quick_new = QPushButton("+")
        self.btn_quick_new.setToolTip("New Conversation (Ctrl+N)")
        self.btn_quick_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_quick_new.setStyleSheet("""
            QPushButton {
                background-color: #0c182c;
                color: #38bdf8;
                border: 1px solid #1e3a63;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
                padding: 3px 10px;
            }
            QPushButton:hover {
                background-color: #122442;
                border-color: #0284c7;
                color: #ffffff;
            }
        """)
        self.btn_quick_new.clicked.connect(self._on_new_chat)
        header_layout.addWidget(self.btn_quick_new)

        # Quick Lock Vault icon button
        self.btn_lock_vault = QPushButton("🔒")
        self.btn_lock_vault.setToolTip("Lock Private Vault (Ctrl+L)")
        self.btn_lock_vault.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lock_vault.setStyleSheet("""
            QPushButton {
                background-color: #0c1424;
                color: #94a3b8;
                border: 1px solid #162238;
                border-radius: 8px;
                font-size: 12px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #121c2d;
                color: #38bdf8;
                border-color: #0284c7;
            }
        """)
        self.btn_lock_vault.clicked.connect(self._lock_or_configure_vault)
        header_layout.addWidget(self.btn_lock_vault)

        # Settings icon button
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setToolTip("Settings & Preferences (Ctrl+,)")
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background-color: #0c1c33;
                color: #38bdf8;
                border: 1px solid #0284c7;
                padding: 4px 10px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0284c7;
                color: #ffffff;
            }
        """)
        self.btn_settings.clicked.connect(self._open_settings)
        header_layout.addWidget(self.btn_settings)

        # More Actions Menu icon button
        self.btn_more = QPushButton("⋮")
        self.btn_more.setToolTip("More options & tools")
        self.btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_more.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: 1px solid #1e2d4a;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #121c2d;
                color: #f1f5f9;
                border-color: #0284c7;
            }
        """)
        self.btn_more.clicked.connect(self._show_more_menu)
        header_layout.addWidget(self.btn_more)

        main_layout.addWidget(header_frame)

        # Central Splitter: Sidebar + Chat Workspace
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet("""
            QSplitter {
                background-color: #080b13;
            }
            QSplitter::handle {
                background-color: #151c28;
                width: 1px;
            }
        """)

        # Left Sidebar
        self.sidebar = ChatSidebar(self.splitter)
        self.sidebar.chat_selected.connect(self._on_chat_selected)
        self.sidebar.new_chat_requested.connect(self._on_new_chat)
        self.sidebar.rename_chat_requested.connect(self._on_rename_chat)
        self.sidebar.delete_chat_requested.connect(self._on_delete_chat)
        self.sidebar.export_chat_requested.connect(self._on_export_chat)
        self.sidebar.toggle_collapse_requested.connect(self._toggle_sidebar)
        self.sidebar.settings_requested.connect(self._open_settings)
        self.sidebar.privacy_requested.connect(self._open_privacy)
        self.sidebar.help_requested.connect(self._open_limitations)
        self.sidebar.lock_vault_requested.connect(self._lock_or_configure_vault)
        self.splitter.addWidget(self.sidebar)

        # Right Workspace
        self.workspace = ChatWorkspace(
            chat_service=self.chat_service,
            settings_service=self.settings_service,
            model_service=self.model_service,
            context_service=self.context_service,
            auth_service=self.auth_service,
            parent=self.splitter,
        )
        self.workspace.chat_title_updated.connect(self._on_title_updated)
        self.workspace.export_requested.connect(self._on_export_chat)
        self.splitter.addWidget(self.workspace)

        # Allocate 260px to sidebar and remainder to chat
        self.splitter.setSizes([260, 820])
        main_layout.addWidget(self.splitter, stretch=1)

        self._saved_sidebar_size = 260
        self._update_mock_button_label()

    def _init_status_bar(self) -> None:
        """Configure the bottom status bar."""
        bar = QStatusBar(self)
        bar.setStyleSheet("""
            QStatusBar {
                background-color: #080b13;
                color: #64748b;
                border-top: 1px solid #151c28;
                font-size: 11px;
                padding: 4px 14px;
            }
            QStatusBar::item {
                border: none;
            }
            QLabel {
                color: #64748b;
                font-size: 11px;
            }
        """)
        self.setStatusBar(bar)
        db_name = self.paths.database_file.name
        bar.showMessage(
            f"Database: {db_name} | Localhost Binding: {self.settings.server_host}:{self.settings.server_port}"
        )

    def _init_menu(self) -> None:
        """Create standard application menu items."""
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #080b13;
                color: #94a3b8;
                border-bottom: 1px solid #151c28;
                font-size: 12px;
                padding: 2px 6px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 10px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #121a29;
                color: #38bdf8;
            }
            QMenu {
                background-color: #0b101c;
                color: #f1f5f9;
                border: 1px solid #1c2637;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #1c2637;
                margin: 4px 8px;
            }
        """)

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

        lock_action = QAction("&Lock Private Vault", self)
        lock_action.setShortcut(QKeySequence("Ctrl+L"))
        lock_action.triggered.connect(self._lock_or_configure_vault)
        file_menu.addAction(lock_action)

        file_menu.addSeparator()

        settings_action = QAction("&Preferences / Settings...", self)
        settings_action.setShortcut(QKeySequence.StandardKey.Preferences)
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        if self.model_service is not None:
            quick_setup_action = QAction("&1-Click Model Setup Wizard...", self)
            quick_setup_action.triggered.connect(self._open_quick_setup)
            file_menu.addAction(quick_setup_action)

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
            diag_action.setShortcut(QKeySequence("Ctrl+D"))
            diag_action.triggered.connect(self._open_diagnostics)
            tools_menu.addAction(diag_action)

        mock_action = QAction("Toggle &Mock / Demo Mode", self)
        mock_action.triggered.connect(self._toggle_mock_mode)
        tools_menu.addAction(mock_action)

        debug_action = QAction("Toggle Developer &Debug Mode", self)
        debug_action.triggered.connect(self._toggle_debug_mode)
        tools_menu.addAction(debug_action)

        self.inspect_prompt_action = QAction("Inspect Constructed &Prompt (Debug)...", self)
        self.inspect_prompt_action.triggered.connect(self._open_prompt_review)
        self.inspect_prompt_action.setVisible(getattr(self.settings, "debug_mode", False))
        tools_menu.addAction(self.inspect_prompt_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        onboarding_action = QAction("&Welcome & Onboarding Guide...", self)
        onboarding_action.triggered.connect(self._open_onboarding)
        help_menu.addAction(onboarding_action)

        privacy_action = QAction("&Privacy Policy & Guarantees...", self)
        privacy_action.triggered.connect(self._open_privacy)
        help_menu.addAction(privacy_action)

        limitations_action = QAction("Product &Limitations & Realities...", self)
        limitations_action.triggered.connect(self._open_limitations)
        help_menu.addAction(limitations_action)

        help_menu.addSeparator()

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
            # Create first initial chat with default workflow
            default_wf = WorkflowRegistry.get_default_workflow().id
            first_chat = self.chat_service.create_chat(workflow=default_wf)
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
        """Create a fresh conversation session with default workflow."""
        default_wf = WorkflowRegistry.get_default_workflow().id
        new_chat = self.chat_service.create_chat(workflow=default_wf)
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

    def _open_settings(self) -> None:
        """Open the comprehensive Settings & Preferences Dialog."""
        dialog = SettingsDialog(
            settings_service=self.settings_service,
            chat_service=self.chat_service,
            paths=self.paths,
            parent=self,
        )
        dialog.exec()
        self.settings = self.settings_service.load_settings()
        self.sidebar.set_user_profile(self.settings.user_name)
        self._update_mock_button_label()
        self._reload_chats()

    def _lock_or_configure_vault(self) -> None:
        """Lock the private vault, or prompt to set PIN if none configured."""
        if not self.auth_service.is_pin_configured():
            dlg = SetPinDialog(self.auth_service, self)
            if dlg.exec() == QDialog.DialogCode.Accepted and self.auth_service.is_pin_configured():
                self.auth_service.lock()
                self.workspace.set_locked(True)
        else:
            self.auth_service.lock()
            self.workspace.set_locked(True)

    def _show_more_menu(self) -> None:
        """Display overflow action menu (Image 2 style)."""
        menu = QMenu(self)

        action_model = QAction("⚡ Model & Server Setup...", self)
        action_model.triggered.connect(self._open_model_setup)
        menu.addAction(action_model)

        if self.diagnostics_service is not None:
            action_diag = QAction("📊 System Diagnostics...", self)
            action_diag.setShortcut(QKeySequence("Ctrl+D"))
            action_diag.triggered.connect(self._open_diagnostics)
            menu.addAction(action_diag)

        action_privacy = QAction("🔒 Privacy & Guarantees...", self)
        action_privacy.triggered.connect(self._open_privacy)
        menu.addAction(action_privacy)

        action_limits = QAction("⚠️ Product Limitations...", self)
        action_limits.triggered.connect(self._open_limitations)
        menu.addAction(action_limits)

        action_onboard = QAction("🚀 Onboarding Guide...", self)
        action_onboard.triggered.connect(self._open_onboarding)
        menu.addAction(action_onboard)

        menu.addSeparator()

        action_lock = QAction("🔒 Lock Private Vault (Ctrl+L)", self)
        action_lock.triggered.connect(self._lock_or_configure_vault)
        menu.addAction(action_lock)

        action_test_stream = QAction("🧪 Test LLM Streaming...", self)
        action_test_stream.triggered.connect(self._open_provider_test)
        menu.addAction(action_test_stream)

        mock_txt = "Disable Mock Mode" if self.settings.mock_mode else "Enable Mock / Demo Mode"
        action_mock = QAction(f"🎭 {mock_txt}", self)
        action_mock.triggered.connect(self._toggle_mock_mode)
        menu.addAction(action_mock)

        menu.exec(self.btn_more.mapToGlobal(QPoint(0, self.btn_more.height())))

    def _open_privacy(self) -> None:
        """Open the Privacy Guarantee & Data Locations Dialog."""
        dialog = PrivacyDialog(
            paths=self.paths,
            chat_service=self.chat_service,
            parent=self,
        )
        dialog.exec()
        self._reload_chats()

    def _open_limitations(self) -> None:
        """Open the Product Limitations & Realities Dialog."""
        dialog = LimitationsDialog(parent=self)
        dialog.exec()

    def _open_onboarding(self) -> None:
        """Open the First-Launch Onboarding and Setup Guide."""
        dialog = OnboardingDialog(
            settings_service=self.settings_service,
            paths=self.paths,
            parent=self,
        )
        dialog.exec()
        self.settings = self.settings_service.load_settings()
        self._update_mock_button_label()
        if dialog.user_choice == "quick_setup":
            self._open_quick_setup()
        elif dialog.user_choice == "configure_model":
            self._open_model_setup()

    def _open_quick_setup(self) -> None:
        """Open the 1-Click Fast Setup Wizard."""
        if self.model_service is not None:
            wizard = SetupWizardDialog(
                model_service=self.model_service,
                settings_service=self.settings_service,
                paths=self.paths,
                parent=self,
            )
            result = wizard.exec()
            self.settings = self.settings_service.load_settings()
            self._update_mock_button_label()
            if result == 2:  # User clicked "Select Existing File..."
                self._open_model_setup()

    def _check_first_launch_onboarding(self) -> None:
        """Prompt first-time users with the onboarding guide."""
        self._open_onboarding()


    def _toggle_sidebar(self) -> None:
        """Toggle left sidebar between collapsed (hidden) and expanded state."""
        sizes = self.splitter.sizes()
        if sizes[0] > 0:
            self._saved_sidebar_size = sizes[0]
            self.splitter.setSizes([0, sizes[0] + sizes[1]])
            self.btn_toggle_sidebar.setText("☰")
            self.btn_toggle_sidebar.setToolTip("Expand Sidebar (Ctrl+B)")
        else:
            restore_size = getattr(self, "_saved_sidebar_size", 260) or 260
            self.splitter.setSizes([restore_size, max(400, sizes[1] - restore_size)])
            self.btn_toggle_sidebar.setText("◀")
            self.btn_toggle_sidebar.setToolTip("Collapse Sidebar (Ctrl+B)")

    def _update_mock_button_label(self) -> None:
        """Synchronize button text and badge with active mock setting."""
        if self.settings.mock_mode:
            self.btn_toggle_mock.setText("Disable Mock Mode")
            self.status_badge.setText(" ● Demo Mode (Mock Mode Active) ")
            self.status_badge.setStyleSheet(
                "background-color: #0c2340; color: #7dd3fc; "
                "border: 1px solid #0284c7; border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
            )
        else:
            self.btn_toggle_mock.setText("Enable Mock / Demo Mode")
            if self.model_service is not None:
                self._update_server_status_badge(self.model_service.get_status())
            else:
                self.status_badge.setText(" ● No Model Configured ")
                self.status_badge.setStyleSheet(
                    "background-color: #2b1f0d; color: #f59e0b; "
                    "border: 1px solid #b45309; border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
                )

    def _update_server_status_badge(self, status: ServerStatus) -> None:
        """Update status badge color, text, and tooltip according to ServerStatus."""
        if self.settings.mock_mode:
            return

        if status.state == ServerState.READY:
            self.status_badge.setText(f" 🔒 Ready ({status.url or 'local'}) ")
            self.status_badge.setToolTip(f"Server is healthy and ready on {status.url or 'localhost'}.")
            self.status_badge.setStyleSheet(
                "background-color: #052e16; color: #4ade80; "
                "border: 1px solid #16a34a; border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
            )
        elif status.state == ServerState.STARTING:
            self.status_badge.setText(" ⏳ Server Starting... ")
            self.status_badge.setToolTip("Loading model weights into memory. Please wait...")
            self.status_badge.setStyleSheet(
                "background-color: #3b2104; color: #fde047; "
                "border: 1px solid #ca8a04; border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
            )
        elif status.state == ServerState.GENERATING:
            self.status_badge.setText(" ⚡ Generating Response... ")
            self.status_badge.setToolTip("Local inference currently in progress.")
            self.status_badge.setStyleSheet(
                "background-color: #0c2340; color: #38bdf8; "
                "border: 1px solid #0284c7; border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
            )
        elif status.state == ServerState.CRASHED:
            self.status_badge.setText(" ⚠️ Server CRASHED ")
            self.status_badge.setToolTip("The server process exited unexpectedly. View Diagnostics or restart server.")
            self.status_badge.setStyleSheet(
                "background-color: #450a0a; color: #f87171; "
                "border: 1px solid #dc2626; border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
            )
        elif status.state in (ServerState.START_FAILED, ServerState.UNAVAILABLE):
            self.status_badge.setText(f" ⚠️ Server {status.state.value} ")
            self.status_badge.setToolTip(f"Server status: {status.state.value}. Check Settings or Diagnostics.")
            self.status_badge.setStyleSheet(
                "background-color: #450a0a; color: #f87171; "
                "border: 1px solid #dc2626; border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
            )
        else:  # STOPPED
            self.status_badge.setText(" ● No Model Configured " if not self.settings.model_path else " ● Server Stopped ")
            self.status_badge.setToolTip("Click 'Model & Server Setup' or 'Settings' to configure and start your local model.")
            self.status_badge.setStyleSheet(
                "background-color: #2b1f0d; color: #f59e0b; "
                "border: 1px solid #b45309; border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
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

    def _toggle_debug_mode(self) -> None:
        """Toggle developer debug mode for inspecting constructed prompts."""
        self.settings.debug_mode = not getattr(self.settings, "debug_mode", False)
        self.settings_service.save_settings(self.settings)
        self.workspace.set_debug_mode(self.settings.debug_mode)
        self.inspect_prompt_action.setVisible(self.settings.debug_mode)
        state_str = "Enabled" if self.settings.debug_mode else "Disabled"
        logger.info("Developer debug mode %s by user.", state_str.lower())
        self.statusBar().showMessage(f"Developer Debug Mode {state_str}", 4000)

    def _open_prompt_review(self) -> None:
        """Open debug prompt inspection dialog for active chat."""
        if self.workspace.active_chat is not None:
            prompt_data = self.chat_service.get_debug_prompt(self.workspace.active_chat.id)
            dlg = PromptReviewDialog(prompt_data, self)
            dlg.exec()

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
