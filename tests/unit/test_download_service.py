"""Unit tests for ModelDownloadService, engine discovery, and 1-click setup wizard."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sarthika_code.app.paths import AppPaths
from sarthika_code.services.download_service import (
    RECOMMENDED_MODELS,
    DownloadProgress,
    ModelDownloadService,
)
from sarthika_code.services.model_service import ModelService
from sarthika_code.services.settings_service import SettingsService


def test_recommended_models_catalog(temp_paths: AppPaths) -> None:
    """Verify catalog includes expected models with valid URLs and filenames."""
    service = ModelDownloadService(temp_paths)
    models = service.get_recommended_models()

    assert len(models) >= 2
    model_ids = [m.id for m in models]
    assert "qwen-2.5-coder-1.5b" in model_ids
    assert "qwen-2.5-coder-3b" in model_ids

    for m in models:
        assert m.download_url.startswith("https://")
        assert m.filename.endswith(".gguf")
        assert m.size_bytes > 0


def test_model_and_engine_destination_paths(temp_paths: AppPaths) -> None:
    """Verify resolved paths point to the designated models and bin directories."""
    service = ModelDownloadService(temp_paths)
    m = RECOMMENDED_MODELS[0]

    dest_model = service.get_model_destination_path(m)
    assert dest_model.parent == temp_paths.models_dir
    assert dest_model.name == m.filename

    dest_engine = service.get_engine_destination_path()
    assert dest_engine.parent == temp_paths.bin_dir
    if sys.platform == "win32":
        assert dest_engine.name == "llama-server.exe"
    else:
        assert dest_engine.name == "llama-server"


def test_discover_llama_server_path(
    temp_paths: AppPaths,
    settings_service: SettingsService,
    tmp_path: Path,
) -> None:
    """Verify ModelService auto-discovery finds engine in bin_dir."""
    from sarthika_code.llm.manager import LlamaServerManager

    server_mgr = LlamaServerManager(log_dir=temp_paths.logs_dir)
    model_service = ModelService(settings_service=settings_service, server_manager=server_mgr)

    exec_name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    fake_bin = temp_paths.bin_dir / exec_name
    temp_paths.bin_dir.mkdir(parents=True, exist_ok=True)
    fake_bin.write_text("#!/bin/sh\necho test\n")
    fake_bin.chmod(0o755)

    discovered = model_service.discover_llama_server_path(temp_paths)
    assert discovered is not None
    assert discovered.resolve() == fake_bin.resolve()


def test_download_model_mock_http(temp_paths: AppPaths) -> None:
    """Verify download_model streams data, reports progress, and performs atomic rename."""
    service = ModelDownloadService(temp_paths)
    model = RECOMMENDED_MODELS[0]

    fake_data = b"GGUF_MOCK_PAYLOAD" * 500
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-length": str(len(fake_data))}
    mock_response.iter_bytes.return_value = [fake_data[:500], fake_data[500:]]

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.stream.return_value.__enter__.return_value = mock_response

    progress_events: list[DownloadProgress] = []

    def on_prog(p: DownloadProgress) -> None:
        progress_events.append(p)

    with patch("httpx.Client", return_value=mock_client):
        dest = service.download_model(model, on_progress=on_prog)

    assert dest.exists()
    assert dest.stat().st_size == len(fake_data)
    assert not dest.with_suffix(".part").exists()
    assert len(progress_events) >= 1
    assert progress_events[-1].status == "completed"


def test_download_model_cancellation(temp_paths: AppPaths) -> None:
    """Verify that cancelling download stops stream and deletes partial file."""
    service = ModelDownloadService(temp_paths)
    model = RECOMMENDED_MODELS[0]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-length": "1000000"}

    def infinite_chunks(chunk_size: int = 1024):
        # Trigger cancel on first iteration
        service.cancel_download("test_cancel")
        yield b"chunk1"
        yield b"chunk2"

    mock_response.iter_bytes.side_effect = infinite_chunks

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.stream.return_value.__enter__.return_value = mock_response

    with (
        patch("httpx.Client", return_value=mock_client),
        pytest.raises(RuntimeError, match="cancelled"),
    ):
        service.download_model(model, task_id="test_cancel")

    dest = service.get_model_destination_path(model)
    assert not dest.exists()
    assert not dest.with_suffix(dest.suffix + ".part").exists()


def test_setup_wizard_dialog_instantiation(
    qapp: object,
    temp_paths: AppPaths,
    settings_service: SettingsService,
) -> None:
    """Verify SetupWizardDialog initializes with appropriate widgets and defaults."""
    from sarthika_code.llm.manager import LlamaServerManager
    from sarthika_code.ui.dialogs.setup_wizard_dialog import SetupWizardDialog

    server_mgr = LlamaServerManager(log_dir=temp_paths.logs_dir)
    model_service = ModelService(settings_service=settings_service, server_manager=server_mgr)

    dialog = SetupWizardDialog(
        model_service=model_service,
        settings_service=settings_service,
        paths=temp_paths,
    )

    assert dialog.windowTitle() == "Sarthika Code — Quick Setup"
    assert dialog.btn_start.isEnabled()
    assert not dialog.btn_start.isHidden()
    assert dialog.progress_frame.isHidden()
    assert dialog.radio_3b.isChecked()


    # Selecting 1.5B updates selection
    dialog.radio_1_5b.setChecked(True)
    dialog._on_model_selected(0)
    assert dialog.selected_model.id == "qwen-2.5-coder-1.5b"
    dialog.close()
