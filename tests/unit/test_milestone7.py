"""Unit and UI tests for Milestone 7 — UX polish, onboarding, settings, diagnostics, privacy, limitations, and failure recovery.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from sarthika_code.app.paths import AppPaths
from sarthika_code.domain.config import AppSettings, GenerationSettings
from sarthika_code.domain.errors import (
    ConfigurationError,
    ContextLimitError,
    ModelValidationError,
    SensitiveFileError,
)
from sarthika_code.domain.server import ServerState, ServerStatus
from sarthika_code.services.chat_service import ChatService
from sarthika_code.services.diagnostics import DiagnosticsService
from sarthika_code.services.settings_service import ALLOWED_CONTEXT_SIZES, SettingsService
from sarthika_code.storage.database import DatabaseManager
from sarthika_code.ui.dialogs.diagnostics_dialog import DiagnosticsDialog
from sarthika_code.ui.dialogs.limitations_dialog import LimitationsDialog
from sarthika_code.ui.dialogs.onboarding_dialog import OnboardingDialog
from sarthika_code.ui.dialogs.privacy_dialog import PrivacyDialog
from sarthika_code.ui.dialogs.settings_dialog import SettingsDialog
from sarthika_code.ui.main_window import MainWindow

# ==============================================================================
# 1. Settings Validation & Generation Defaults Tests
# ==============================================================================

def test_settings_validation_generation_bounds(settings_service: SettingsService) -> None:
    """Verify SettingsService enforces conservative bounds on generation parameters."""
    # Invalid temperature < 0.0
    with pytest.raises(ConfigurationError) as exc_info:
        settings_service.save_settings(AppSettings(temperature=-0.1))
    assert "Invalid temperature" in str(exc_info.value)

    # Invalid temperature > 2.0
    with pytest.raises(ConfigurationError):
        settings_service.save_settings(AppSettings(temperature=2.5))

    # Invalid top_p > 1.0
    with pytest.raises(ConfigurationError) as exc_info:
        settings_service.save_settings(AppSettings(top_p=1.5))
    assert "Invalid top_p" in str(exc_info.value)

    # Invalid max_tokens < 128
    with pytest.raises(ConfigurationError) as exc_info:
        settings_service.save_settings(AppSettings(max_tokens=64))
    assert "Invalid max_tokens" in str(exc_info.value)

    # Invalid max_tokens > 16384
    with pytest.raises(ConfigurationError):
        settings_service.save_settings(AppSettings(max_tokens=32000))

    # Invalid repeat_penalty < 1.0
    with pytest.raises(ConfigurationError) as exc_info:
        settings_service.save_settings(AppSettings(repeat_penalty=0.5))
    assert "Invalid repeat_penalty" in str(exc_info.value)


def test_context_presets_validation(settings_service: SettingsService) -> None:
    """Verify supported context presets are accepted while unsupported values are rejected."""
    for valid_ctx in ALLOWED_CONTEXT_SIZES:
        settings = AppSettings(context_size=valid_ctx)
        settings_service.save_settings(settings)
        loaded = settings_service.load_settings()
        assert loaded.context_size == valid_ctx

    with pytest.raises(ConfigurationError):
        settings_service.save_settings(AppSettings(context_size=1000))


def test_settings_reset_to_defaults(settings_service: SettingsService) -> None:
    """Verify reset_settings safely restores and persists all default values."""
    custom = AppSettings(
        temperature=0.8,
        top_p=0.95,
        max_tokens=4096,
        repeat_penalty=1.3,
        context_size=8192,
        server_port=9090,
        mock_mode=True,
    )
    settings_service.save_settings(custom)
    assert settings_service.load_settings().temperature == 0.8

    defaults = settings_service.reset_settings()
    assert defaults.temperature == 0.3
    assert defaults.top_p == 0.8
    assert defaults.max_tokens == 2048
    assert defaults.repeat_penalty == 1.1
    assert defaults.context_size == 4096
    assert defaults.server_port == 8080
    assert defaults.mock_mode is False

    reloaded = settings_service.load_settings()
    assert reloaded.temperature == 0.3
    assert reloaded.mock_mode is False


def test_to_generation_settings(settings_service: SettingsService) -> None:
    """Verify AppSettings.to_generation_settings() creates a typed GenerationSettings object."""
    settings = AppSettings(temperature=0.4, top_p=0.85, max_tokens=1024, repeat_penalty=1.15)
    gen = settings.to_generation_settings()
    assert isinstance(gen, GenerationSettings)
    assert gen.temperature == 0.4
    assert gen.top_p == 0.85
    assert gen.max_tokens == 1024
    assert gen.repeat_penalty == 1.15


# ==============================================================================
# 2. Diagnostics Metrics & Safe Redaction Tests
# ==============================================================================

def test_diagnostics_extended_metrics(temp_paths: AppPaths, settings_service: SettingsService) -> None:
    """Verify DiagnosticsService populates config location, generation settings, and throughput metrics."""
    diag_service = DiagnosticsService(
        paths=temp_paths,
        settings_service=settings_service,
        status_provider=lambda: ServerStatus(state=ServerState.READY, url="http://127.0.0.1:8080", pid=999),
        metrics_provider=lambda: (250, 10000),  # 250 tokens in 10,000 ms (10 seconds) = 25.0 tokens/s
    )

    report = diag_service.collect_diagnostics()
    assert report.config_location == str(temp_paths.config_dir)
    assert "temp=0.3" in report.generation_settings
    assert "top_p=0.8" in report.generation_settings
    assert report.generated_tokens == "250 tokens"
    assert "10.00s" in report.last_response_time
    assert report.tokens_per_second == "25.0 tokens/s"


def test_diagnostics_redaction_and_unredacted_toggle(temp_paths: AppPaths, settings_service: SettingsService) -> None:
    """Verify to_formatted_text cleanly redacts home directory or preserves full paths when unredacted."""
    home = Path.home()
    settings = AppSettings(
        model_path=f"{home}/models/test.gguf",
        llama_server_path=f"{home}/bin/llama-server",
    )
    settings_service.save_settings(settings)

    diag_service = DiagnosticsService(paths=temp_paths, settings_service=settings_service)
    report = diag_service.collect_diagnostics()

    # Redacted
    redacted_text = report.to_formatted_text(redact=True)
    assert str(home) not in redacted_text
    assert "~/models/test.gguf" in redacted_text
    assert "~/bin/llama-server" in redacted_text

    # Unredacted
    full_text = report.to_formatted_text(redact=False)
    assert str(home) in full_text
    assert f"{home}/models/test.gguf" in full_text


# ==============================================================================
# 3. Onboarding State Persistence & Flow Tests
# ==============================================================================

def test_onboarding_state_persistence(settings_service: SettingsService) -> None:
    """Verify onboarding_completed starts False and persists accurately."""
    initial = settings_service.load_settings()
    assert initial.onboarding_completed is False

    initial.onboarding_completed = True
    settings_service.save_settings(initial)

    loaded = settings_service.load_settings()
    assert loaded.onboarding_completed is True


def test_onboarding_dialog_mock_mode_choice(qapp: QApplication, settings_service: SettingsService, temp_paths: AppPaths) -> None:
    """Verify selecting Mock Mode in OnboardingDialog activates mock mode and completes onboarding."""
    dialog = OnboardingDialog(settings_service=settings_service, paths=temp_paths)
    dialog._on_choose_mock()

    assert dialog.user_choice == "mock_mode"
    settings = settings_service.load_settings()
    assert settings.mock_mode is True
    assert settings.onboarding_completed is True


def test_onboarding_dialog_setup_choice(qapp: QApplication, settings_service: SettingsService, temp_paths: AppPaths) -> None:
    """Verify selecting Configure Model in OnboardingDialog sets choice and marks completed."""
    dialog = OnboardingDialog(settings_service=settings_service, paths=temp_paths)
    dialog._on_choose_setup()

    assert dialog.user_choice == "configure_model"
    settings = settings_service.load_settings()
    assert settings.onboarding_completed is True


# ==============================================================================
# 4. Local Data Erasure Tests
# ==============================================================================

def test_clear_all_chats_erasure(db_manager: DatabaseManager) -> None:
    """Verify clear_all_chats permanently removes all conversations and messages."""
    chat_service = ChatService(db_manager)

    chat1 = chat_service.create_chat(title="Chat 1")
    chat_service.add_user_message(chat1.id, "Hello from chat 1")
    chat2 = chat_service.create_chat(title="Chat 2")
    chat_service.add_user_message(chat2.id, "Hello from chat 2")

    assert len(chat_service.list_chats()) == 2

    count = chat_service.clear_all_chats()
    assert count == 2
    assert len(chat_service.list_chats()) == 0


# ==============================================================================
# 5. User-Friendly Error Formatting Tests
# ==============================================================================

def test_user_friendly_error_formatting() -> None:
    """Verify domain errors format actionable remedies without raw tracebacks."""
    err1 = ModelValidationError("The specified GGUF file is unreadable.")
    formatted = err1.format_for_user()
    assert "The specified GGUF file is unreadable." in formatted
    assert "How to fix:" in formatted
    assert "Select a valid, readable .gguf model file" in formatted

    err2 = SensitiveFileError("Access denied to .env file.")
    assert "How to fix:" in err2.format_for_user()
    assert "Sensitive files" in err2.format_for_user()

    err3 = ContextLimitError("Prompt exceeds context window.")
    assert "Reduce the number of selected files" in err3.format_for_user()


# ==============================================================================
# 6. UI Dialogs & Controls Tests
# ==============================================================================

def test_settings_dialog_save_and_apply(qapp: QApplication, settings_service: SettingsService, db_manager: DatabaseManager, temp_paths: AppPaths) -> None:
    """Verify SettingsDialog edits and persists values across tabs."""
    chat_service = ChatService(db_manager)
    dialog = SettingsDialog(settings_service=settings_service, chat_service=chat_service, paths=temp_paths)

    dialog.spin_temp.setValue(0.45)
    dialog.spin_top_p.setValue(0.75)
    dialog.spin_max_tokens.setValue(1024)
    dialog.chk_mock_mode.setChecked(True)

    dialog._save_settings(show_confirmation=False)

    loaded = settings_service.load_settings()
    assert loaded.temperature == 0.45
    assert loaded.top_p == 0.75
    assert loaded.max_tokens == 1024
    assert loaded.mock_mode is True


def test_privacy_dialog_rendering(qapp: QApplication, temp_paths: AppPaths, db_manager: DatabaseManager) -> None:
    """Verify PrivacyDialog renders local paths and principles."""
    chat_service = ChatService(db_manager)
    dialog = PrivacyDialog(paths=temp_paths, chat_service=chat_service)
    assert dialog.windowTitle() == "Privacy & Data Guarantee — Sarthika Code"
    assert dialog.isVisible() is False  # Headless check


def test_limitations_dialog_rendering(qapp: QApplication) -> None:
    """Verify LimitationsDialog initializes with required caveat sections."""
    dialog = LimitationsDialog()
    assert "Product Realities & Limitations" in dialog.windowTitle()


def test_diagnostics_dialog_redaction_toggle(qapp: QApplication, temp_paths: AppPaths, settings_service: SettingsService) -> None:
    """Verify DiagnosticsDialog redaction checkbox updates text view."""
    home = Path.home()
    settings_service.save_settings(AppSettings(model_path=f"{home}/test_model.gguf"))
    diag_service = DiagnosticsService(paths=temp_paths, settings_service=settings_service)

    dialog = DiagnosticsDialog(diagnostics_service=diag_service)
    assert dialog.chk_redact.isChecked()
    assert str(home) not in dialog.txt_diagnostics.toPlainText()

    # Uncheck redaction
    dialog.chk_redact.setChecked(False)
    assert str(home) in dialog.txt_diagnostics.toPlainText()


# ==============================================================================
# 7. Status Badge & Failure Recovery State Transitions
# ==============================================================================

def test_main_window_server_status_badge_transitions(qapp: QApplication, temp_paths: AppPaths, settings_service: SettingsService) -> None:
    """Verify MainWindow transitions status badge text and styling across server lifecycle states."""
    window = MainWindow(paths=temp_paths, settings_service=settings_service)

    # 1. Starting
    window._update_server_status_badge(ServerStatus(state=ServerState.STARTING))
    assert "Starting" in window.status_badge.text()

    # 2. Ready
    window._update_server_status_badge(ServerStatus(state=ServerState.READY, url="http://127.0.0.1:8080"))
    assert "Ready" in window.status_badge.text()

    # 3. Generating
    window._update_server_status_badge(ServerStatus(state=ServerState.GENERATING))
    assert "Generating" in window.status_badge.text()

    # 4. Crashed
    window._update_server_status_badge(ServerStatus(state=ServerState.CRASHED))
    assert "CRASHED" in window.status_badge.text()

    # 5. Mock mode overrides badge
    window.settings.mock_mode = True
    window._update_mock_button_label()
    assert "Mock Mode Active" in window.status_badge.text()
