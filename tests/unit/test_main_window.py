"""Unit tests for MainWindow and application launch without model configured."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from sarthika_code.app.paths import AppPaths
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.ui.main_window import MainWindow


def test_main_window_initializes_without_model(
    qapp: QApplication,
    temp_paths: AppPaths,
    settings_service: SettingsService,
) -> None:
    """Verify MainWindow launches gracefully with 'No Model Configured' badge."""
    window = MainWindow(paths=temp_paths, settings_service=settings_service)
    try:
        assert window.windowTitle() == "Sarthika Code — Local-First AI Coding Assistant"
        assert "No Model Configured" in window.status_badge.text()
        assert window.btn_toggle_mock.text() == "Enable Mock / Demo Mode"
    finally:
        window.close()


def test_main_window_mock_mode_toggle(
    qapp: QApplication,
    temp_paths: AppPaths,
    settings_service: SettingsService,
) -> None:
    """Verify toggling mock mode updates UI badge and persists state."""
    window = MainWindow(paths=temp_paths, settings_service=settings_service)
    try:
        assert not window.settings.mock_mode

        # Trigger mock mode toggle
        window._toggle_mock_mode()
        assert window.settings.mock_mode is True
        assert "Mock Mode Active" in window.status_badge.text()
        assert window.btn_toggle_mock.text() == "Disable Mock Mode"

        # Verify persisted in database
        reloaded_settings = settings_service.load_settings()
        assert reloaded_settings.mock_mode is True

        # Toggle back off
        window._toggle_mock_mode()
        assert window.settings.mock_mode is False
        assert "No Model Configured" in window.status_badge.text()
        assert window.btn_toggle_mock.text() == "Enable Mock / Demo Mode"
    finally:
        window.close()
