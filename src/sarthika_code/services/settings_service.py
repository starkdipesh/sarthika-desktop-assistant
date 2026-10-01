"""Application service managing user preferences and configuration persistence.

Ensures settings are properly validated and safely stored in the local SQLite database.
"""

from __future__ import annotations

import json
from typing import Any

from sarthika_code.domain.config import AppSettings
from sarthika_code.domain.errors import ConfigurationError
from sarthika_code.storage.database import DatabaseManager
from sarthika_code.storage.repositories import SettingsRepository
from sarthika_code.utils.logging import get_logger

logger = get_logger("SettingsService")

ALLOWED_CONTEXT_SIZES = (2048, 4096, 8192, 16384, 32768)


class SettingsService:
    """Coordinates typed configuration access and persistent updates."""

    SETTINGS_KEY = "app_settings"

    def __init__(
        self,
        db_manager: DatabaseManager,
        repository: SettingsRepository | None = None,
    ) -> None:
        self.db_manager = db_manager
        self.repo = repository or SettingsRepository()

    def load_settings(self) -> AppSettings:
        """Load persistent application settings from SQLite, falling back to defaults."""
        with self.db_manager.session() as session:
            raw_json = self.repo.get(session, self.SETTINGS_KEY)

        if not raw_json:
            logger.info("No persisted settings found; using default configuration.")
            return AppSettings()

        try:
            data = json.loads(raw_json)
            if not isinstance(data, dict):
                raise ValueError("Settings payload is not a valid dictionary")
            return AppSettings.from_dict(data)
        except Exception as e:
            logger.warning("Corrupted settings encountered in database (%s); resetting to defaults.", e)
            return AppSettings()

    def save_settings(self, settings: AppSettings) -> None:
        """Validate and persist application settings to SQLite."""
        self.validate_settings(settings)
        serialized = json.dumps(settings.to_dict())

        with self.db_manager.session() as session:
            self.repo.set(session, self.SETTINGS_KEY, serialized)

        logger.info("Persisted updated application settings.")

    def get_settings(self) -> AppSettings:
        """Convenience alias for load_settings."""
        return self.load_settings()

    def update_settings(self, **kwargs: Any) -> AppSettings:
        """Update specific settings attributes and persist them."""
        settings = self.load_settings()
        for k, v in kwargs.items():
            if hasattr(settings, k):
                setattr(settings, k, v)
        self.save_settings(settings)
        return settings

    def validate_settings(self, settings: AppSettings) -> None:
        """Enforce architectural security and boundary constraints on settings."""
        # Enforce localhost only
        if settings.server_host not in ("127.0.0.1", "localhost"):
            raise ConfigurationError(
                message=f"Invalid server host '{settings.server_host}'.",
                user_guidance="Sarthika Code strictly binds to local loopback ('127.0.0.1') for privacy and security.",
            )

        # Enforce valid context sizes
        if settings.context_size not in ALLOWED_CONTEXT_SIZES:
            raise ConfigurationError(
                message=f"Unsupported context size {settings.context_size}.",
                user_guidance=f"Choose a supported context size: {ALLOWED_CONTEXT_SIZES}.",
            )

        # Enforce valid port range
        if not (1024 <= settings.server_port <= 65535):
            raise ConfigurationError(
                message=f"Invalid port {settings.server_port}.",
                user_guidance="Specify a valid user port between 1024 and 65535.",
            )

        # Enforce conservative generation setting bounds
        if not (0.0 <= settings.temperature <= 2.0):
            raise ConfigurationError(
                message=f"Invalid temperature {settings.temperature}.",
                user_guidance="Temperature must be between 0.0 (deterministic) and 2.0 (creative). Recommended: 0.2 to 0.4.",
            )

        if not (0.0 <= settings.top_p <= 1.0):
            raise ConfigurationError(
                message=f"Invalid top_p {settings.top_p}.",
                user_guidance="Top-p must be between 0.0 and 1.0. Recommended: 0.8.",
            )

        if not (128 <= settings.max_tokens <= 16384):
            raise ConfigurationError(
                message=f"Invalid max_tokens {settings.max_tokens}.",
                user_guidance="Max generation tokens must be between 128 and 16,384 tokens.",
            )

        if not (1.0 <= settings.repeat_penalty <= 2.0):
            raise ConfigurationError(
                message=f"Invalid repeat_penalty {settings.repeat_penalty}.",
                user_guidance="Repeat penalty must be between 1.0 and 2.0. Recommended: 1.1.",
            )

    def reset_settings(self) -> AppSettings:
        """Safely restore all settings to default values and persist them."""
        defaults = AppSettings()
        self.save_settings(defaults)
        logger.info("Application settings reset to safe defaults.")
        return defaults

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Retrieve an individual raw setting by key."""
        with self.db_manager.session() as session:
            val = self.repo.get(session, key)
            if val is None:
                return default
            try:
                return json.loads(val)
            except Exception:
                return val

    def set_setting(self, key: str, value: Any) -> None:
        """Store an individual raw setting by key."""
        serialized = json.dumps(value) if not isinstance(value, str) else value
        with self.db_manager.session() as session:
            self.repo.set(session, key, serialized)
