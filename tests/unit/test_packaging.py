"""Unit tests for packaging strategy, release build validation, and artifact safety rules."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.build_release import (
    BuildError,
    clean_build_artifacts,
    get_project_version,
    validate_prerequisites,
    verify_build_artifacts,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_get_project_version() -> None:
    """Verify version extraction matches pyproject.toml."""
    version = get_project_version()
    assert version == "0.1.0"


def test_validate_prerequisites_success() -> None:
    """Verify that prerequisites validation passes on existing repository structure."""
    metadata = validate_prerequisites(validate_pyinstaller=False)
    assert metadata["project_version"] == "0.1.0"
    assert Path(metadata["entrypoint"]).exists()
    assert Path(metadata["icon_ico"]).exists()
    assert Path(metadata["icon_png"]).exists()


def test_validate_prerequisites_fails_on_missing_entrypoint(tmp_path: Path) -> None:
    """Verify validate_prerequisites fails clearly if entrypoint is missing."""
    with (
        patch("scripts.build_release.REPO_ROOT", tmp_path),
        pytest.raises(BuildError) as exc_info,
    ):
        validate_prerequisites(validate_pyinstaller=False)

    assert "missing" in str(exc_info.value).lower()


def test_validate_prerequisites_fails_on_missing_pyinstaller() -> None:
    """Verify validate_prerequisites fails when PyInstaller is required but not in PATH."""
    with (
        patch("shutil.which", return_value=None),
        pytest.raises(BuildError) as exc_info,
    ):
        validate_prerequisites(validate_pyinstaller=True)

    assert "PyInstaller executable not found" in str(exc_info.value)


def test_clean_build_artifacts_safety(tmp_path: Path) -> None:
    """Verify clean_build_artifacts cleans directories inside repo root safely."""
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()
    dist_dir = fake_repo / "dist"
    build_dir = fake_repo / "build"
    dist_dir.mkdir()
    build_dir.mkdir()

    (dist_dir / "old_exe.exe").write_bytes(b"old")
    (build_dir / "old_temp.tmp").write_bytes(b"old")

    with patch("scripts.build_release.REPO_ROOT", fake_repo):
        clean_build_artifacts(dist_dir, build_dir)

    assert not dist_dir.exists()
    assert not build_dir.exists()


def test_clean_build_artifacts_refuses_external_directories(tmp_path: Path) -> None:
    """Verify clean_build_artifacts refuses to delete directories outside repo root."""
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    external_dir = tmp_path / "important_user_data"
    external_dir.mkdir()

    with (
        patch("scripts.build_release.REPO_ROOT", fake_repo),
        pytest.raises(BuildError) as exc_info,
    ):
        clean_build_artifacts(external_dir, fake_repo / "build")

    assert "Refusing to delete unsafe directory" in str(exc_info.value)
    assert external_dir.exists()


def test_verify_build_artifacts_detects_forbidden_files(tmp_path: Path) -> None:
    """Verify verify_build_artifacts raises BuildError if a model or database was packaged."""
    dist_output = tmp_path / "SarthikaCode"
    dist_output.mkdir()

    # Create safe file
    (dist_output / "SarthikaCode.exe").write_bytes(b"MZ_EXE")

    # Verify safe package passes
    res = verify_build_artifacts(dist_output)
    assert res["file_count"] == 1

    # Inject forbidden GGUF model
    (dist_output / "model.gguf").write_bytes(b"GGUF")
    with pytest.raises(BuildError) as exc_info:
        verify_build_artifacts(dist_output)
    assert "forbidden file" in str(exc_info.value).lower()

    # Remove GGUF, inject forbidden database
    (dist_output / "model.gguf").unlink()
    (dist_output / "chat.sqlite").write_bytes(b"SQLITE")
    with pytest.raises(BuildError) as exc_info:
        verify_build_artifacts(dist_output)
    assert "forbidden file" in str(exc_info.value).lower()

    # Remove database, inject sensitive .env
    (dist_output / "chat.sqlite").unlink()
    (dist_output / ".env.local").write_text("API_KEY=123", encoding="utf-8")
    with pytest.raises(BuildError) as exc_info:
        verify_build_artifacts(dist_output)
    assert "sensitive file" in str(exc_info.value).lower()


def test_spec_file_and_version_info_structure() -> None:
    """Verify sarthika_code.spec and windows_version_info.txt exist and contain required metadata."""
    spec_file = REPO_ROOT / "sarthika_code.spec"
    assert spec_file.exists()
    spec_text = spec_file.read_text(encoding="utf-8")
    assert "SarthikaCode" in spec_text
    assert "assets" in spec_text
    assert "forbidden_extensions" in spec_text
    assert "PySide6" in spec_text

    version_file = REPO_ROOT / "scripts" / "windows_version_info.txt"
    assert version_file.exists()
    v_text = version_file.read_text(encoding="utf-8")
    assert "Sarthika Code" in v_text
    assert "0.1.0.0" in v_text
    assert "SarthikaCode.exe" in v_text
    assert "Sarthika Code Contributors" in v_text
