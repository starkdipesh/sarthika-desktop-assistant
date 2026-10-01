"""Application coordinator and dependency container for Sarthika Code.

Initializes logging, local directories, SQLite database, llama-server manager,
model services, diagnostics, and PySide6 application lifecycle.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from sarthika_code.app.paths import AppPaths, get_app_paths
from sarthika_code.llm.manager import LlamaServerManager
from sarthika_code.services.chat_service import ChatService
from sarthika_code.services.context_service import ProjectContextService
from sarthika_code.services.diagnostics import DiagnosticsService
from sarthika_code.services.model_service import ModelService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.services.workflow_service import WorkflowService
from sarthika_code.storage.database import DatabaseManager
from sarthika_code.ui.main_window import MainWindow
from sarthika_code.utils.logging import get_logger, setup_logging


class SarthikaApp:
    """Manages application lifecycle, storage setup, services, and UI orchestration."""

    def __init__(self, base_path: Path | None = None) -> None:
        self.paths: AppPaths = get_app_paths(base_override=base_path)
        self.paths.ensure_directories()

        # Initialize logging
        setup_logging(log_file_path=self.paths.log_file)
        self.logger = get_logger("Application")
        self.logger.info("Initializing Sarthika Code (v0.1)...")
        self.logger.info("Configuration directory: %s", self.paths.config_dir)
        self.logger.info("Database file: %s", self.paths.database_file)
        self.logger.info("Logs directory: %s", self.paths.logs_dir)

        # Initialize SQLite database schema
        self.db_manager = DatabaseManager(self.paths.database_file)
        self.db_manager.init_db()
        self.logger.info("Database schema initialized successfully.")

        # Initialize application services
        self.settings_service = SettingsService(self.db_manager)
        self.chat_service = ChatService(self.db_manager)
        self.context_service = ProjectContextService(self.db_manager)
        self.workflow_service = WorkflowService()
        self.server_manager = LlamaServerManager(log_dir=self.paths.logs_dir)
        self.model_service = ModelService(
            settings_service=self.settings_service,
            server_manager=self.server_manager,
        )

        # Auto-configure discovered llama-server if not yet set or invalid
        current_settings = self.settings_service.get_settings()
        if not current_settings.llama_server_path or not Path(current_settings.llama_server_path).is_file():
            discovered = self.model_service.discover_llama_server_path(self.paths)
            if discovered:
                self.settings_service.update_settings(llama_server_path=str(discovered))
                self.logger.info("Auto-configured llama-server path: %s", discovered)

        self.diagnostics_service = DiagnosticsService(
            paths=self.paths,
            settings_service=self.settings_service,
            status_provider=lambda: self.server_manager.status,
            metrics_provider=lambda: self.chat_service.get_last_generation_metrics(),
        )

        # PySide6 Application instance
        self.qapp: QApplication | None = None
        self.main_window: MainWindow | None = None

    def initialize_ui(self) -> MainWindow:
        """Create QApplication instance and MainWindow."""
        instance = QApplication.instance()
        if isinstance(instance, QApplication):
            self.qapp = instance
        else:
            self.qapp = QApplication(sys.argv)
            self.qapp.setApplicationName("Sarthika Code")
            self.qapp.setApplicationVersion("0.1.0")
            self.qapp.setOrganizationName("Sarthika")

        self.main_window = MainWindow(
            paths=self.paths,
            settings_service=self.settings_service,
            model_service=self.model_service,
            diagnostics_service=self.diagnostics_service,
            chat_service=self.chat_service,
            context_service=self.context_service,
        )
        return self.main_window

    def run(self) -> int:
        """Launch the desktop UI and block on Qt event loop until exit."""
        if self.main_window is None:
            self.initialize_ui()

        assert self.main_window is not None
        assert self.qapp is not None

        self.main_window.show()
        self.logger.info("Main window displayed. Starting Qt event loop.")

        exit_code = self.qapp.exec()
        self.shutdown()
        return exit_code

    def shutdown(self) -> None:
        """Perform graceful cleanup of persistence and background server processes."""
        self.logger.info("Shutting down application resources.")
        try:
            self.server_manager.stop_server(graceful_timeout=2.0)
            self.logger.info("llama-server process cleaned up.")
        except Exception as e:
            self.logger.error("Error stopping server on shutdown: %s", e)

        try:
            self.db_manager.close()
            self.logger.info("Database connections disposed.")
        except Exception as e:
            self.logger.error("Error during database shutdown: %s", e)
