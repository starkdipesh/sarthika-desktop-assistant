"""Unit tests for OS directory path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from sarthika_code.app.paths import get_app_paths


def test_app_paths_creation(tmp_path: Path) -> None:
    """Verify that AppPaths correctly resolves and creates subdirectories."""
    paths = get_app_paths(base_override=tmp_path)
    assert paths.config_dir == tmp_path / "config"
    assert paths.data_dir == tmp_path / "data"
    assert paths.database_dir == tmp_path / "data"
    assert paths.logs_dir == tmp_path / "logs"
    assert paths.exports_dir == tmp_path / "exports"

    assert paths.database_file == tmp_path / "data" / "sarthika.db"
    assert paths.log_file == tmp_path / "logs" / "sarthika.log"

    # Directories should not exist before ensure_directories
    assert not paths.config_dir.exists()
    paths.ensure_directories()
    assert paths.config_dir.exists()
    assert paths.data_dir.exists()
    assert paths.logs_dir.exists()
    assert paths.exports_dir.exists()


def test_app_paths_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that SARTHIKA_HOME environment variable overrides base paths."""
    override_dir = tmp_path / "custom_sarthika"
    monkeypatch.setenv("SARTHIKA_HOME", str(override_dir))

    paths = get_app_paths()
    assert paths.config_dir == override_dir / "config"
    assert paths.data_dir == override_dir / "data"
    assert paths.logs_dir == override_dir / "logs"


def test_default_app_paths_not_in_repo() -> None:
    """Verify that default paths point to system directories, never the repo."""
    paths = get_app_paths()
    current_repo = Path(__file__).resolve().parents[2]

    assert not str(paths.config_dir).startswith(str(current_repo))
    assert not str(paths.data_dir).startswith(str(current_repo))
    assert not str(paths.logs_dir).startswith(str(current_repo))
