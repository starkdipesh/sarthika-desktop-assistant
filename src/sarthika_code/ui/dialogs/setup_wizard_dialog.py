"""One-Click Setup Wizard and Model Downloader for Sarthika Code.

Provides a completely non-technical, zero-terminal first-run setup experience.
Downloads the recommended local GGUF model and engine binary with real-time
progress, ETA, speed, and automatically launches the local inference engine.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.app.paths import AppPaths, get_app_paths
from sarthika_code.services.download_service import (
    RECOMMENDED_MODELS,
    DownloadableModel,
    DownloadProgress,
    ModelDownloadService,
)
from sarthika_code.services.model_service import ModelService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.utils.logging import get_logger

logger = get_logger("SetupWizardDialog")


class DownloadWorker(QObject):
    """Background worker thread executing engine and model downloads."""

    progress_signal = Signal(object)  # Emits DownloadProgress
    completed_signal = Signal(str, str)  # Emits (model_path, engine_path)
    failed_signal = Signal(str)  # Emits error message

    def __init__(
        self,
        download_service: ModelDownloadService,
        selected_model: DownloadableModel,
        needs_engine: bool,
    ) -> None:
        super().__init__()
        self.download_service = download_service
        self.selected_model = selected_model
        self.needs_engine = needs_engine
        self._is_cancelled = False

    def run(self) -> None:
        """Execute the download pipeline."""
        try:
            engine_path_str = ""
            # Step 1: Download engine if needed
            if self.needs_engine and not self.download_service.is_engine_available():
                logger.info("Engine binary missing; initiating automatic download...")
                engine_dest = self.download_service.download_engine(
                    on_progress=lambda p: self.progress_signal.emit(p),
                    task_id="setup_engine",
                )
                engine_path_str = str(engine_dest)

            # Step 2: Download selected model
            logger.info("Initiating model download for: %s", self.selected_model.name)
            model_dest = self.download_service.download_model(
                self.selected_model,
                on_progress=lambda p: self.progress_signal.emit(p),
                task_id="setup_model",
            )

            self.completed_signal.emit(str(model_dest), engine_path_str)

        except Exception as exc:
            if not self._is_cancelled:
                logger.error("Download failed in worker: %s", exc)
                self.failed_signal.emit(str(exc))

    def cancel(self) -> None:
        self._is_cancelled = True
        self.download_service.cancel_download("setup_engine")
        self.download_service.cancel_download("setup_model")


class SetupWizardDialog(QDialog):
    """Non-technical, 1-click onboarding wizard with integrated downloader."""

    def __init__(
        self,
        model_service: ModelService,
        settings_service: SettingsService,
        paths: AppPaths | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model_service = model_service
        self.settings_service = settings_service
        self.paths = paths or get_app_paths()
        self.download_service = ModelDownloadService(self.paths)

        self.selected_model: DownloadableModel = RECOMMENDED_MODELS[1]  # Default to 3B
        self.worker_thread: QThread | None = None
        self.worker: DownloadWorker | None = None
        self.setup_succeeded = False

        self.setWindowTitle("Sarthika Code — Quick Setup")
        self.resize(680, 560)
        self.setMinimumSize(580, 480)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(6)

        title_lbl = QLabel("⚡ One-Click Local AI Setup")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        title_lbl.setStyleSheet("color: #38bdf8;")
        header_layout.addWidget(title_lbl)

        desc_lbl = QLabel(
            "Get ready to chat with local AI in one click. No terminal commands, git, "
            "or technical knowledge required. Sarthika Code will configure everything locally."
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.4;")
        header_layout.addWidget(desc_lbl)
        layout.addLayout(header_layout)

        # Options Box / Model Selection
        self.model_box = QFrame()
        self.model_box.setStyleSheet(
            "background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px;"
        )
        box_layout = QVBoxLayout(self.model_box)
        box_layout.setSpacing(12)

        box_title = QLabel("Choose Your Local Model:")
        box_title.setStyleSheet("color: #f8fafc; font-weight: bold; font-size: 13px;")
        box_layout.addWidget(box_title)

        self.model_group = QButtonGroup(self)

        # Option 1: 1.5B
        self.radio_1_5b = QRadioButton()
        self.radio_1_5b.setStyleSheet("color: #f1f5f9; font-size: 13px;")
        self.radio_1_5b_label = QLabel(
            f"<b>{RECOMMENDED_MODELS[0].name}</b> — Size: {RECOMMENDED_MODELS[0].size_formatted}<br>"
            f"<span style='color: #94a3b8; font-size: 11px;'>{RECOMMENDED_MODELS[0].description}</span>"
        )
        self.radio_1_5b_label.setWordWrap(True)
        row_1_5b = QHBoxLayout()
        row_1_5b.addWidget(self.radio_1_5b)
        row_1_5b.addWidget(self.radio_1_5b_label, stretch=1)
        box_layout.addLayout(row_1_5b)
        self.model_group.addButton(self.radio_1_5b, 0)

        # Option 2: 3B (Default)
        self.radio_3b = QRadioButton()
        self.radio_3b.setChecked(True)
        self.radio_3b.setStyleSheet("color: #f1f5f9; font-size: 13px;")
        self.radio_3b_label = QLabel(
            f"<b>{RECOMMENDED_MODELS[1].name}</b> — Size: {RECOMMENDED_MODELS[1].size_formatted} <i>(Recommended)</i><br>"
            f"<span style='color: #94a3b8; font-size: 11px;'>{RECOMMENDED_MODELS[1].description}</span>"
        )
        self.radio_3b_label.setWordWrap(True)
        row_3b = QHBoxLayout()
        row_3b.addWidget(self.radio_3b)
        row_3b.addWidget(self.radio_3b_label, stretch=1)
        box_layout.addLayout(row_3b)
        self.model_group.addButton(self.radio_3b, 1)

        self.model_group.idClicked.connect(self._on_model_selected)
        layout.addWidget(self.model_box)

        # Download Progress Area (Hidden initially)
        self.progress_frame = QFrame()
        self.progress_frame.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #2563eb; border-radius: 8px; padding: 16px;"
        )
        self.progress_frame.setVisible(False)
        prog_layout = QVBoxLayout(self.progress_frame)
        prog_layout.setSpacing(10)

        self.status_title = QLabel("Preparing setup...")
        self.status_title.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        prog_layout.addWidget(self.status_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 5px;
                text-align: center;
                background-color: #1e293b;
                color: #f8fafc;
                font-weight: bold;
                height: 24px;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                border-radius: 4px;
            }
        """)
        prog_layout.addWidget(self.progress_bar)

        self.status_detail = QLabel("Initializing download connection...")
        self.status_detail.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        prog_layout.addWidget(self.status_detail)

        layout.addWidget(self.progress_frame)

        # Privacy guarantee note
        self.privacy_note = QLabel("🔒 100% Private: Downloads directly to your PC. No accounts, telemetry, or tracking.")
        self.privacy_note.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.privacy_note)

        layout.addStretch()

        # Action Buttons
        self.button_row = QHBoxLayout()
        self.button_row.setSpacing(10)

        self.btn_mock = QPushButton("Explore Offline Demo Mode")
        self.btn_mock.setStyleSheet(
            "background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; padding: 10px 16px; border-radius: 6px; font-size: 12px;"
        )
        self.btn_mock.clicked.connect(self._on_choose_mock)
        self.button_row.addWidget(self.btn_mock)

        self.btn_manual = QPushButton("Select Existing File...")
        self.btn_manual.setStyleSheet(
            "background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; padding: 10px 14px; border-radius: 6px; font-size: 12px;"
        )
        self.btn_manual.clicked.connect(self._on_choose_manual)
        self.button_row.addWidget(self.btn_manual)

        self.button_row.addStretch()

        self.btn_start = QPushButton("🚀 Download & Start Setup")
        self.btn_start.setStyleSheet(
            "background-color: #2563eb; color: white; padding: 10px 22px; font-weight: bold; border-radius: 6px; font-size: 13px;"
        )
        self.btn_start.clicked.connect(self._on_start_download)
        self.button_row.addWidget(self.btn_start)

        self.btn_cancel_dl = QPushButton("Cancel")
        self.btn_cancel_dl.setVisible(False)
        self.btn_cancel_dl.setStyleSheet(
            "background-color: #dc2626; color: white; padding: 10px 18px; font-weight: bold; border-radius: 6px; font-size: 12px;"
        )
        self.btn_cancel_dl.clicked.connect(self._on_cancel_download)
        self.button_row.addWidget(self.btn_cancel_dl)

        layout.addLayout(self.button_row)

    def _on_model_selected(self, btn_id: int) -> None:
        self.selected_model = RECOMMENDED_MODELS[btn_id]

    def _on_start_download(self) -> None:
        """Begin downloading engine and model in background thread."""
        self.model_box.setEnabled(False)
        self.btn_start.setVisible(False)
        self.btn_mock.setEnabled(False)
        self.btn_manual.setEnabled(False)
        self.btn_cancel_dl.setVisible(True)
        self.progress_frame.setVisible(True)

        needs_engine = not self.download_service.is_engine_available()

        self.worker_thread = QThread(self)
        self.worker = DownloadWorker(self.download_service, self.selected_model, needs_engine)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress_signal.connect(self._on_progress_update)
        self.worker.completed_signal.connect(self._on_download_completed)
        self.worker.failed_signal.connect(self._on_download_failed)

        self.worker_thread.start()

    def _on_progress_update(self, progress: DownloadProgress) -> None:
        """Update progress bar and status message."""
        self.progress_bar.setValue(int(progress.percent))
        if progress.status == "downloading":
            self.status_title.setText(f"Downloading {self.selected_model.name}...")
            speed_mb = progress.speed_bytes_sec / (1024 * 1024)
            eta_m = int(progress.eta_seconds // 60)
            eta_s = int(progress.eta_seconds % 60)
            detail = f"{progress.message} • {speed_mb:.1f} MB/s • ETA: {eta_m}m {eta_s:02d}s"
            self.status_detail.setText(detail)
        elif progress.status == "extracting":
            self.status_title.setText("Setting up AI engine...")
            self.status_detail.setText(progress.message)
        elif progress.status == "connecting":
            self.status_title.setText("Connecting...")
            self.status_detail.setText(progress.message)
        elif progress.status == "completed":
            self.status_title.setText("Setup completed!")
            self.status_detail.setText(progress.message)

    def _on_download_completed(self, model_path: str, engine_path: str) -> None:
        """Save settings and start server automatically."""
        logger.info("Download completed. Configuring and starting server...")
        self.status_title.setText("Starting local AI engine...")
        self.status_detail.setText("Initializing local inference server...")

        settings = self.settings_service.load_settings()
        settings.model_path = model_path
        if engine_path:
            settings.llama_server_path = engine_path
        settings.mock_mode = False
        settings.onboarding_completed = True
        self.settings_service.save_settings(settings)

        # Attempt to auto-start the server
        try:
            self.model_service.start_configured_server()
            self.status_title.setText("Ready to chat!")
            self.status_detail.setText("Local model initialized successfully.")
        except Exception as e:
            logger.warning("Auto-start after download encountered: %s", e)

        self._cleanup_thread()
        self.setup_succeeded = True
        self.accept()

    def _on_download_failed(self, error: str) -> None:
        self.status_title.setText("Download Failed")
        self.status_detail.setText(f"Error: {error}")
        self.status_detail.setStyleSheet("color: #f87171; font-size: 11px;")
        self.btn_cancel_dl.setVisible(False)
        self.btn_start.setVisible(True)
        self.btn_start.setText("Retry Download")
        self.model_box.setEnabled(True)
        self.btn_mock.setEnabled(True)
        self.btn_manual.setEnabled(True)
        self._cleanup_thread()

    def _on_cancel_download(self) -> None:
        if self.worker:
            self.worker.cancel()
        self.status_title.setText("Download Cancelled")
        self.status_detail.setText("Operation cancelled by user.")
        self.btn_cancel_dl.setVisible(False)
        self.btn_start.setVisible(True)
        self.model_box.setEnabled(True)
        self.btn_mock.setEnabled(True)
        self.btn_manual.setEnabled(True)
        self._cleanup_thread()

    def _on_choose_mock(self) -> None:
        settings = self.settings_service.load_settings()
        settings.mock_mode = True
        settings.onboarding_completed = True
        self.settings_service.save_settings(settings)
        self.setup_succeeded = True
        self.accept()

    def _on_choose_manual(self) -> None:
        """Close wizard and let user use the classic file picker."""
        self.done(2)  # Return code 2 indicates manual model setup

    def _cleanup_thread(self) -> None:
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait(2000)
        self.worker_thread = None
        self.worker = None

    def closeEvent(self, event) -> None:
        self._on_cancel_download()
        super().closeEvent(event)
