"""Unit tests for SettingsRepository and SettingsService."""

from __future__ import annotations

import pytest

from sarthika_code.domain.config import AppSettings
from sarthika_code.domain.errors import ConfigurationError
from sarthika_code.services.settings_service import SettingsService


def test_default_settings_when_empty(settings_service: SettingsService) -> None:
    """Verify default AppSettings are returned if no settings exist in DB."""
    settings = settings_service.load_settings()
    assert settings.theme == "dark"
    assert settings.model_path is None
    assert settings.llama_server_path is None
    assert settings.server_host == "127.0.0.1"
    assert settings.server_port == 8080
    assert settings.context_size == 4096
    assert not settings.mock_mode
    assert settings.threads == 4


def test_save_and_load_settings(settings_service: SettingsService) -> None:
    """Verify saving custom settings and retrieving them correctly."""
    custom = AppSettings(
        theme="light",
        model_path="/custom/path/model.gguf",
        llama_server_path="/custom/bin/llama-server",
        server_host="127.0.0.1",
        server_port=9090,
        context_size=2048,
        mock_mode=True,
        threads=6,
    )
    settings_service.save_settings(custom)

    loaded = settings_service.load_settings()
    assert loaded.theme == "light"
    assert loaded.model_path == "/custom/path/model.gguf"
    assert loaded.llama_server_path == "/custom/bin/llama-server"
    assert loaded.server_port == 9090
    assert loaded.context_size == 2048
    assert loaded.mock_mode is True
    assert loaded.threads == 6


def test_validation_rejects_non_localhost(settings_service: SettingsService) -> None:
    """Verify that setting an external host is blocked by validation."""
    invalid = AppSettings(server_host="192.168.1.100")
    with pytest.raises(ConfigurationError) as exc_info:
        settings_service.save_settings(invalid)
    assert "Invalid server host" in str(exc_info.value)


def test_validation_rejects_invalid_context_size(settings_service: SettingsService) -> None:
    """Verify that unsupported context sizes are blocked."""
    invalid = AppSettings(context_size=3000)
    with pytest.raises(ConfigurationError) as exc_info:
        settings_service.save_settings(invalid)
    assert "Unsupported context size" in str(exc_info.value)


def test_validation_rejects_invalid_port(settings_service: SettingsService) -> None:
    """Verify that invalid ports are blocked."""
    invalid = AppSettings(server_port=80)
    with pytest.raises(ConfigurationError) as exc_info:
        settings_service.save_settings(invalid)
    assert "Invalid port" in str(exc_info.value)


def test_individual_key_value_settings(settings_service: SettingsService) -> None:
    """Verify get_setting and set_setting for generic keys."""
    assert settings_service.get_setting("custom_flag", default="fallback") == "fallback"
    settings_service.set_setting("custom_flag", {"enabled": True, "count": 5})
    retrieved = settings_service.get_setting("custom_flag")
    assert retrieved == {"enabled": True, "count": 5}
