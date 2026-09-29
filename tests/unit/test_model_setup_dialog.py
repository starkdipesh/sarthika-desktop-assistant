"""Unit tests for ModelSetupDialog and DiagnosticsDialog UI components."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from sarthika_code.app.paths import AppPaths
from sarthika_code.domain.config import AppSettings
from sarthika_code.domain.server import ServerState, ServerStatus
from sarthika_code.llm.manager import LlamaServerManager
from sarthika_code.services.diagnostics import DiagnosticsService
from sarthika_code.services.model_service import ModelService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.ui.dialogs.diagnostics_dialog import DiagnosticsDialog
from sarthika_code.ui.dialogs.model_setup_dialog import ModelSetupDialog


def test_model_setup_dialog_initialization(
    qapp: QApplication,
    settings_service: SettingsService,
    temp_paths: AppPaths,
) -> None:
    """Verify ModelSetupDialog loads current settings and defaults."""
    settings = AppSettings(
        model_path="/path/to/test.gguf",
        llama_server_path="/path/to/llama-server",
        server_port=8080,
        context_size=4096,
    )
    settings_service.save_settings(settings)

    manager = LlamaServerManager(log_dir=temp_paths.logs_dir)
    model_service = ModelService(settings_service=settings_service, server_manager=manager)

    dialog = ModelSetupDialog(
        model_service=model_service,
        settings_service=settings_service,
    )
    try:
        assert dialog.txt_model_path.text() == "/path/to/test.gguf"
        assert dialog.txt_exec_path.text() == "/path/to/llama-server"
        assert dialog.spin_port.value() == 8080
        assert dialog.cmb_context.currentData() == 4096
        assert "STOPPED" in dialog.lbl_status.text()
    finally:
        dialog.close()


def test_model_setup_dialog_context_warning(
    qapp: QApplication,
    settings_service: SettingsService,
    temp_paths: AppPaths,
) -> None:
    """Verify selecting high context sizes displays a memory warning."""
    manager = LlamaServerManager(log_dir=temp_paths.logs_dir)
    model_service = ModelService(settings_service=settings_service, server_manager=manager)

    dialog = ModelSetupDialog(
        model_service=model_service,
        settings_service=settings_service,
    )
    try:
        # Standard context (4096) has no warning
        dialog.cmb_context.setCurrentIndex(dialog.cmb_context.findData(4096))
        assert dialog.lbl_context_warning.text() == ""

        # Advanced context (16384) displays high RAM warning
        dialog.cmb_context.setCurrentIndex(dialog.cmb_context.findData(16384))
        assert "Warning" in dialog.lbl_context_warning.text()
    finally:
        dialog.close()


def test_model_setup_dialog_status_sync(
    qapp: QApplication,
    settings_service: SettingsService,
    temp_paths: AppPaths,
) -> None:
    """Verify UI controls update according to ServerState."""
    manager = LlamaServerManager(log_dir=temp_paths.logs_dir)
    model_service = ModelService(settings_service=settings_service, server_manager=manager)

    dialog = ModelSetupDialog(
        model_service=model_service,
        settings_service=settings_service,
    )
    try:
        # READY state disables Start button, enables Stop button
        dialog._sync_status(ServerStatus(state=ServerState.READY, url="http://127.0.0.1:8080"))
        assert not dialog.btn_start.isEnabled()
        assert dialog.btn_stop.isEnabled()
        assert "READY" in dialog.lbl_status.text()

        # STOPPED state enables Start button, disables Stop button
        dialog._sync_status(ServerStatus(state=ServerState.STOPPED))
        assert dialog.btn_start.isEnabled()
        assert not dialog.btn_stop.isEnabled()
        assert "STOPPED" in dialog.lbl_status.text()
    finally:
        dialog.close()


def test_diagnostics_dialog(
    qapp: QApplication,
    temp_paths: AppPaths,
    settings_service: SettingsService,
) -> None:
    """Verify DiagnosticsDialog renders diagnostics text."""
    diag_service = DiagnosticsService(
        paths=temp_paths,
        settings_service=settings_service,
        status_provider=lambda: ServerStatus(state=ServerState.STOPPED),
    )
    dialog = DiagnosticsDialog(diagnostics_service=diag_service)
    try:
        text = dialog.txt_diagnostics.toPlainText()
        assert "SARTHIKA CODE DIAGNOSTICS" in text
        assert "STOPPED" in text
    finally:
        dialog.close()
