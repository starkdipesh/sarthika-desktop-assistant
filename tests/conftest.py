"""Pytest fixtures for Sarthika Code test suite.

Provides isolated temporary application directories, in-memory SQLite databases,
and headless PySide6 application contexts without requiring models or servers.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy.orm import Session

from sarthika_code.app.paths import AppPaths, get_app_paths
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.storage.database import DatabaseManager


@pytest.fixture(scope="session", autouse=True)
def configure_headless_qt() -> None:
    """Ensure Qt runs headlessly in testing environments without an X server."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["NO_AT_BRIDGE"] = "1"
    os.environ["QT_ACCESSIBILITY"] = "0"



@pytest.fixture
def temp_paths(tmp_path: Path) -> AppPaths:
    """Provide isolated application paths inside a temporary directory."""
    paths = get_app_paths(base_override=tmp_path)
    paths.ensure_directories()
    return paths


@pytest.fixture
def db_manager(temp_paths: AppPaths) -> Generator[DatabaseManager, None, None]:
    """Provide an initialized DatabaseManager using an isolated temporary SQLite file."""
    manager = DatabaseManager(temp_paths.database_file)
    manager.init_db()
    try:
        yield manager
    finally:
        manager.close()


@pytest.fixture
def memory_db_manager() -> Generator[DatabaseManager, None, None]:
    """Provide an in-memory SQLite DatabaseManager for fast isolated testing."""
    manager = DatabaseManager(":memory:")
    manager.init_db()
    try:
        yield manager
    finally:
        manager.close()


@pytest.fixture
def db_session(db_manager: DatabaseManager) -> Generator[Session, None, None]:
    """Provide a transactional SQLAlchemy Session from the isolated database."""
    with db_manager.session() as session:
        yield session


@pytest.fixture
def settings_service(db_manager: DatabaseManager) -> SettingsService:
    """Provide a SettingsService instance bound to the isolated database."""
    return SettingsService(db_manager)


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Ensure a singleton QApplication exists for widget testing."""
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication(["--platform", "offscreen"])
    return app
