"""Unit tests for local authentication service, PIN protection, and vault security."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from sarthika_code.services.auth_service import LocalAuthService
from sarthika_code.services.chat_service import ChatService
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.storage.database import DatabaseManager
from sarthika_code.ui.chat.chat_sidebar import ChatSidebar
from sarthika_code.ui.chat.chat_workspace import ChatWorkspace
from sarthika_code.ui.chat.vault_lock_overlay import VaultLockOverlay


def test_auth_service_pin_lifecycle(settings_service: SettingsService) -> None:
    """Verify PIN hashing, validation, locking, and removal."""
    auth = LocalAuthService(settings_service)

    # 1. Initial state: No PIN configured
    assert auth.is_pin_configured() is False
    assert auth.is_locked() is False

    # 2. Reject short PIN (< 4 chars)
    with pytest.raises(ValueError):
        auth.set_pin("12")

    # 3. Configure valid PIN
    auth.set_pin("1234", lock_on_start=True)
    assert auth.is_pin_configured() is True
    assert auth.is_locked() is False

    # Verify persisted in settings
    settings = settings_service.load_settings()
    assert settings.auth_pin_hash is not None
    assert settings.auth_pin_salt is not None
    assert settings.auth_lock_on_start is True

    # 4. Lock vault
    auth.lock()
    assert auth.is_locked() is True

    # 5. Unlock with wrong PIN fails
    assert auth.unlock("9999") is False
    assert auth.is_locked() is True

    # 6. Unlock with correct PIN succeeds
    assert auth.unlock("1234") is True
    assert auth.is_locked() is False

    # 7. Remove PIN
    assert auth.remove_pin("wrong") is False
    assert auth.remove_pin("1234") is True
    assert auth.is_pin_configured() is False


def test_vault_lock_overlay_unlock_signal(qapp: QApplication, settings_service: SettingsService) -> None:
    """Verify VaultLockOverlay emits unlocked signal when correct PIN is entered."""
    auth = LocalAuthService(settings_service)
    auth.set_pin("5678")
    auth.lock()

    overlay = VaultLockOverlay(auth)
    unlocked_called = False

    def on_unlocked() -> None:
        nonlocal unlocked_called
        unlocked_called = True

    overlay.unlocked.connect(on_unlocked)

    # Enter wrong PIN
    overlay.txt_pin.setText("0000")
    overlay.btn_unlock.click()
    assert unlocked_called is False
    assert "Incorrect" in overlay.lbl_error.text()

    # Enter correct PIN
    overlay.txt_pin.setText("5678")
    overlay.btn_unlock.click()
    assert unlocked_called is True
    assert auth.is_locked() is False

    overlay.close()


def test_sidebar_user_profile_card(qapp: QApplication) -> None:
    """Verify ChatSidebar renders user profile and avatar accurately."""
    sidebar = ChatSidebar()
    sidebar.set_user_profile("Dipesh Mahakali")

    assert sidebar.lbl_user_name.text() == "Dipesh Mahakali"
    assert sidebar.lbl_avatar.text() == "D"

    # Custom name
    sidebar.set_user_profile("Alice")
    assert sidebar.lbl_user_name.text() == "Alice"
    assert sidebar.lbl_avatar.text() == "A"

    sidebar.close()


def test_chat_workspace_locking_behavior(
    qapp: QApplication,
    db_manager: DatabaseManager,
    settings_service: SettingsService,
) -> None:
    """Verify ChatWorkspace switches view when locked and unlocked."""
    auth = LocalAuthService(settings_service)
    auth.set_pin("4321")

    chat_service = ChatService(db_manager)
    workspace = ChatWorkspace(
        chat_service=chat_service,
        settings_service=settings_service,
        auth_service=auth,
    )

    assert workspace.is_locked() is False

    workspace.set_locked(True)
    assert workspace.is_locked() is True

    workspace.set_locked(False)
    assert workspace.is_locked() is False

    workspace.close()

