"""Local security and authentication service for Sarthika Code.

Provides local-first passcode/PIN vault protection to keep conversation history
and local context safe from unauthorized local access.
Strictly local-first: no remote servers, no cloud verification, no telemetry.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import TYPE_CHECKING

from sarthika_code.services.settings_service import SettingsService
from sarthika_code.utils.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger("AuthService")


class LocalAuthService:
    """Manages local PIN verification, vault locking, and security state."""

    def __init__(self, settings_service: SettingsService) -> None:
        self.settings_service = settings_service
        self._is_locked = False

        # Check if lock on start is configured
        settings = self.settings_service.load_settings()
        if settings.auth_lock_on_start and settings.auth_pin_hash:
            self._is_locked = True

    @staticmethod
    def hash_pin(pin: str, salt: str | None = None) -> tuple[str, str]:
        """Generate a PBKDF2 HMAC-SHA256 hash and salt for a security PIN."""
        if not salt:
            salt = secrets.token_hex(16)
        # 100,000 rounds of PBKDF2 HMAC-SHA256
        key = hashlib.pbkdf2_hmac(
            "sha256",
            pin.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=100_000,
        )
        return key.hex(), salt

    @staticmethod
    def verify_pin(pin: str, stored_hash: str, salt: str) -> bool:
        """Verify whether candidate PIN matches the stored PBKDF2 hash."""
        candidate_hash, _ = LocalAuthService.hash_pin(pin, salt)
        return secrets.compare_digest(candidate_hash, stored_hash)

    def is_pin_configured(self) -> bool:
        """Check whether a security PIN is set for this local installation."""
        settings = self.settings_service.load_settings()
        return bool(settings.auth_pin_hash and settings.auth_pin_salt)

    def is_locked(self) -> bool:
        """Return True if the private vault is currently in locked state."""
        return self._is_locked

    def lock(self) -> None:
        """Immediately lock the vault."""
        self._is_locked = True
        logger.info("Local security vault locked.")

    def unlock(self, pin: str) -> bool:
        """Attempt to unlock the vault with the provided PIN. Returns True if successful."""
        settings = self.settings_service.load_settings()
        if not settings.auth_pin_hash or not settings.auth_pin_salt:
            # No PIN set, unlock immediately
            self._is_locked = False
            return True

        if self.verify_pin(pin, settings.auth_pin_hash, settings.auth_pin_salt):
            self._is_locked = False
            logger.info("Local security vault unlocked successfully.")
            return True

        logger.warning("Failed vault unlock attempt with incorrect PIN.")
        return False

    def set_pin(self, new_pin: str, lock_on_start: bool = True) -> None:
        """Set or update the security PIN and persist settings."""
        if len(new_pin) < 4:
            raise ValueError("Security PIN must be at least 4 characters long.")

        pin_hash, salt = self.hash_pin(new_pin)
        settings = self.settings_service.load_settings()
        settings.auth_pin_hash = pin_hash
        settings.auth_pin_salt = salt
        settings.auth_lock_on_start = lock_on_start
        self.settings_service.save_settings(settings)
        self._is_locked = False
        logger.info("New security PIN configured and saved.")

    def remove_pin(self, current_pin: str) -> bool:
        """Remove security PIN after verifying the current PIN."""
        if not self.unlock(current_pin):
            return False

        settings = self.settings_service.load_settings()
        settings.auth_pin_hash = None
        settings.auth_pin_salt = None
        settings.auth_lock_on_start = False
        self.settings_service.save_settings(settings)
        self._is_locked = False
        logger.info("Security PIN removed.")
        return True
