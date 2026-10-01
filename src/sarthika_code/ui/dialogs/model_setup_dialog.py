"""Model setup and llama-server management dialog for Sarthika Code.

Allows users to select GGUF model files, locate llama-server executables,
choose context presets with memory warnings, start/stop the server, or connect
to an existing localhost server.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.domain.errors import SarthikaError
from sarthika_code.domain.server import ServerState, ServerStatus
from sarthika_code.services.model_service import ModelService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.utils.logging import get_logger

logger = get_logger("ModelSetupDialog")


class ModelSetupDialog(QDialog):
    """Dialog for configuring local GGUF models, executables, and server lifecycle."""

    def __init__(
        self,
        model_service: ModelService,
        settings_service: SettingsService,
        on_open_diagnostics: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model_service = model_service
        self.settings_service = settings_service
        self.on_open_diagnostics = on_open_diagnostics
        self.settings = self.settings_service.load_settings()

        self.setWindowTitle("Model & Server Setup — Sarthika Code")
        self.resize(680, 580)
        self.setMinimumSize(540, 440)

        self._init_ui()
        self._sync_status(self.model_service.get_status())
        self.model_service.server_manager.add_state_listener(self._on_server_status_change)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # 1. Model Selection Group
        model_group = QGroupBox("1. Local GGUF Model File")
        model_layout = QVBoxLayout(model_group)

        file_row = QHBoxLayout()
        self.txt_model_path = QLineEdit(self.settings.model_path or "")
        self.txt_model_path.setPlaceholderText("Path to .gguf file (e.g. Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf)")
        file_row.addWidget(self.txt_model_path)

        btn_browse_model = QPushButton("Browse...")
        btn_browse_model.clicked.connect(self._browse_model)
        file_row.addWidget(btn_browse_model)

        btn_download = QPushButton("⚡ Download Model...")
        btn_download.setStyleSheet("background-color: #1e3a5f; color: #60a5fa; font-weight: bold;")
        btn_download.clicked.connect(self._open_downloader)
        file_row.addWidget(btn_download)
        model_layout.addLayout(file_row)

        self.lbl_model_info = QLabel("")
        self.lbl_model_info.setStyleSheet("color: #94a3b8; font-size: 11px;")
        model_layout.addWidget(self.lbl_model_info)
        layout.addWidget(model_group)

        # 2. llama-server Executable Group
        exec_group = QGroupBox("2. llama-server Executable")
        exec_layout = QVBoxLayout(exec_group)

        exec_row = QHBoxLayout()
        discovered_exec = self.model_service.discover_llama_server_path()
        initial_exec = self.settings.llama_server_path or (str(discovered_exec) if discovered_exec else "")
        self.txt_exec_path = QLineEdit(initial_exec)
        self.txt_exec_path.setPlaceholderText("Path to llama-server or llama-server.exe binary (auto-discovered if left empty)")
        exec_row.addWidget(self.txt_exec_path)

        btn_browse_exec = QPushButton("Browse...")
        btn_browse_exec.clicked.connect(self._browse_executable)
        exec_row.addWidget(btn_browse_exec)

        exec_layout.addLayout(exec_row)
        layout.addWidget(exec_group)

        # 3. Server Configuration & Context Presets
        config_group = QGroupBox("3. Runtime Configuration")
        config_layout = QVBoxLayout(config_group)

        row_settings = QHBoxLayout()

        # Context Size Combo
        lbl_ctx = QLabel("Context Window:")
        row_settings.addWidget(lbl_ctx)

        self.cmb_context = QComboBox()
        self.cmb_context.addItem("2048 tokens (Low-Memory / 8 GB RAM)", 2048)
        self.cmb_context.addItem("4096 tokens (Standard Recommended)", 4096)
        self.cmb_context.addItem("8192 tokens (Optional)", 8192)
        self.cmb_context.addItem("16384 tokens (Advanced — High RAM)", 16384)
        self.cmb_context.addItem("32768 tokens (Maximum — Heavy CPU)", 32768)

        # Select current setting index
        idx = self.cmb_context.findData(self.settings.context_size)
        if idx >= 0:
            self.cmb_context.setCurrentIndex(idx)
        else:
            self.cmb_context.setCurrentIndex(1)  # Default 4096
        self.cmb_context.currentIndexChanged.connect(self._on_context_changed)
        row_settings.addWidget(self.cmb_context)

        # Port Setting
        lbl_port = QLabel("Local Port:")
        row_settings.addWidget(lbl_port)
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(self.settings.server_port)
        row_settings.addWidget(self.spin_port)

        config_layout.addLayout(row_settings)

        # Memory Warning Label
        self.lbl_context_warning = QLabel("")
        self.lbl_context_warning.setStyleSheet("color: #eab308; font-weight: bold; font-size: 11px;")
        config_layout.addWidget(self.lbl_context_warning)
        layout.addWidget(config_group)

        # 4. External Server Connection Option
        ext_group = QGroupBox("4. Or Connect to Existing Local Server")
        ext_layout = QHBoxLayout(ext_group)
        self.txt_ext_url = QLineEdit("http://127.0.0.1:8080")
        ext_layout.addWidget(self.txt_ext_url)
        self.btn_connect_ext = QPushButton("Connect Existing")
        self.btn_connect_ext.clicked.connect(self._connect_existing)
        ext_layout.addWidget(self.btn_connect_ext)
        layout.addWidget(ext_group)

        # Status and Errors Display Box
        self.status_box = QFrame()
        self.status_box.setStyleSheet(
            "background-color: #1e293b; border-radius: 6px; padding: 12px;"
        )
        status_box_layout = QVBoxLayout(self.status_box)

        self.lbl_status = QLabel("Server Status: STOPPED")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #f8fafc;")
        status_box_layout.addWidget(self.lbl_status)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #ef4444; font-size: 12px;")
        self.lbl_error.setWordWrap(True)
        status_box_layout.addWidget(self.lbl_error)
        layout.addWidget(self.status_box)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("Start Local Server")
        self.btn_start.setStyleSheet(
            "background-color: #16a34a; color: white; padding: 8px 16px; font-weight: bold; border-radius: 4px;"
        )
        self.btn_start.clicked.connect(self._start_server)
        btn_row.addWidget(self.btn_start)

        self.btn_stop = QPushButton("Stop Server")
        self.btn_stop.setStyleSheet(
            "background-color: #dc2626; color: white; padding: 8px 16px; font-weight: bold; border-radius: 4px;"
        )
        self.btn_stop.clicked.connect(self._stop_server)
        btn_row.addWidget(self.btn_stop)

        if self.on_open_diagnostics:
            btn_diag = QPushButton("View Diagnostics")
            btn_diag.clicked.connect(self.on_open_diagnostics)
            btn_row.addWidget(btn_diag)

        btn_row.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self._check_initial_model_info()

    def _browse_model(self) -> None:
        """Open system file picker for .gguf model selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Local GGUF Model",
            str(Path.home()),
            "GGUF Models (*.gguf);;All Files (*)",
        )
        if file_path:
            self.txt_model_path.setText(file_path)
            self._update_model_info(file_path)

    def _browse_executable(self) -> None:
        """Open system file picker for llama-server binary selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select llama-server Executable",
            str(Path.home()),
            "Executables (*.exe llama-server*);;All Files (*)",
        )
        if file_path:
            self.txt_exec_path.setText(file_path)

    def _check_initial_model_info(self) -> None:
        """Check and display initial model file details if configured."""
        path_str = self.txt_model_path.text().strip()
        if path_str and Path(path_str).exists():
            self._update_model_info(path_str)

    def _update_model_info(self, file_path: str) -> None:
        """Display validated model file size and name."""
        try:
            p = Path(file_path)
            if p.exists() and p.is_file():
                mb = p.stat().st_size / (1024 * 1024)
                self.lbl_model_info.setText(f"File: {p.name} | Size: {mb:.1f} MB | Quantization: Unknown")
                self.lbl_error.setText("")
        except Exception as e:
            self.lbl_model_info.setText("")
            logger.warning("Could not read model file size: %s", e)

    def _on_context_changed(self) -> None:
        """Display warning when high context presets are selected."""
        ctx = int(self.cmb_context.currentData())
        if ctx >= 16384:
            self.lbl_context_warning.setText(
                "⚠️ Warning: Context sizes >= 16,384 tokens consume substantial RAM for the KV-cache and may cause slow CPU inference."
            )
        elif ctx >= 8192:
            self.lbl_context_warning.setText(
                "Notice: 8,192 tokens requires >= 16 GB RAM for comfortable inference."
            )
        else:
            self.lbl_context_warning.setText("")

    def _start_server(self) -> None:
        """Trigger server startup with validated inputs."""
        self.lbl_error.setText("")
        model_path = self.txt_model_path.text().strip()
        exec_path = self.txt_exec_path.text().strip()
        ctx = int(self.cmb_context.currentData())
        port = self.spin_port.value()

        try:
            status = self.model_service.start_configured_server(
                model_path=model_path,
                exec_path=exec_path,
                context_size=ctx,
                port=port,
            )
            self._sync_status(status)
        except SarthikaError as e:
            self.lbl_error.setText(e.format_for_user())
            self._sync_status(self.model_service.get_status())
        except Exception as e:
            self.lbl_error.setText(f"Failed to start server: {e}")
            self._sync_status(self.model_service.get_status())

    def _stop_server(self) -> None:
        """Trigger graceful stop of the active server."""
        try:
            status = self.model_service.stop_server()
            self._sync_status(status)
        except Exception as e:
            self.lbl_error.setText(f"Error stopping server: {e}")

    def _connect_existing(self) -> None:
        """Connect to an external localhost server."""
        self.lbl_error.setText("")
        url = self.txt_ext_url.text().strip()
        try:
            status = self.model_service.server_manager.connect_existing_server(url)
            self._sync_status(status)
        except SarthikaError as e:
            self.lbl_error.setText(e.format_for_user())
        except Exception as e:
            self.lbl_error.setText(f"Connection failed: {e}")

    def _sync_status(self, status: ServerStatus) -> None:
        """Update buttons and labels reflecting the active ServerStatus."""
        state_text = f"Server Status: {status.state.value}"
        if status.url:
            state_text += f" ({status.url})"
        if status.pid:
            state_text += f" [PID: {status.pid}]"

        self.lbl_status.setText(state_text)

        if status.state == ServerState.READY:
            self.lbl_status.setStyleSheet("font-weight: bold; color: #4ade80;")
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
        elif status.state == ServerState.STARTING:
            self.lbl_status.setStyleSheet("font-weight: bold; color: #facc15;")
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
        elif status.state in (ServerState.START_FAILED, ServerState.CRASHED, ServerState.UNAVAILABLE):
            self.lbl_status.setStyleSheet("font-weight: bold; color: #f87171;")
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            if status.last_error:
                self.lbl_error.setText(status.last_error)
        else:  # STOPPED / STOPPING
            self.lbl_status.setStyleSheet("font-weight: bold; color: #94a3b8;")
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

    def _on_server_status_change(self, status: ServerStatus) -> None:
        """Callback from server manager; safely update UI components."""
        # Use QMetaObject or direct update if running in same thread
        self._sync_status(status)

    def _open_downloader(self) -> None:
        """Launch the 1-click model setup wizard dialog."""
        from sarthika_code.ui.dialogs.setup_wizard_dialog import SetupWizardDialog

        wizard = SetupWizardDialog(
            model_service=self.model_service,
            settings_service=self.settings_service,
            parent=self,
        )
        if wizard.exec() == 1:
            updated = self.settings_service.load_settings()
            self.settings = updated
            self.txt_model_path.setText(updated.model_path or "")
            self.txt_exec_path.setText(updated.llama_server_path or "")
            self._check_initial_model_info()
            self._sync_status(self.model_service.get_status())

