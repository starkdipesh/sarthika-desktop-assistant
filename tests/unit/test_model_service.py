"""Unit tests for ModelService: model and executable validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from sarthika_code.domain.errors import ConfigurationError, ModelValidationError
from sarthika_code.llm.manager import LlamaServerManager
from sarthika_code.services.model_service import ModelService
from sarthika_code.services.settings_service import SettingsService


@pytest.fixture
def model_service(settings_service: SettingsService, tmp_path: Path) -> ModelService:
    manager = LlamaServerManager(log_dir=tmp_path / "logs")
    return ModelService(settings_service=settings_service, server_manager=manager)


def test_validate_model_path_empty(model_service: ModelService) -> None:
    """Verify empty path raises ModelValidationError."""
    with pytest.raises(ModelValidationError) as exc:
        model_service.validate_model_path("")
    assert "No model file path provided" in str(exc.value)


def test_validate_model_path_nonexistent(model_service: ModelService) -> None:
    """Verify non-existent path raises ModelValidationError."""
    with pytest.raises(ModelValidationError) as exc:
        model_service.validate_model_path("/nonexistent/path/model.gguf")
    assert "not found" in str(exc.value)


def test_validate_model_path_directory(model_service: ModelService, tmp_path: Path) -> None:
    """Verify directory path raises ModelValidationError."""
    dir_path = tmp_path / "model_dir"
    dir_path.mkdir()
    with pytest.raises(ModelValidationError) as exc:
        model_service.validate_model_path(dir_path)
    assert "is a directory" in str(exc.value)


def test_validate_model_path_non_gguf(model_service: ModelService, tmp_path: Path) -> None:
    """Verify non-.gguf extension raises ModelValidationError."""
    bin_file = tmp_path / "model.bin"
    bin_file.write_bytes(b"dummy binary contents" * 100)
    with pytest.raises(ModelValidationError) as exc:
        model_service.validate_model_path(bin_file)
    assert "Only .gguf models are supported" in str(exc.value)


def test_validate_model_path_valid(model_service: ModelService, tmp_path: Path) -> None:
    """Verify valid .gguf file returns ModelConfiguration with Unknown quantization."""
    gguf_file = tmp_path / "Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf"
    # Write at least 1024 bytes
    gguf_file.write_bytes(b"GGUF_HEADER_DATA" * 100)

    config = model_service.validate_model_path(gguf_file)
    assert config.model_name == "Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf"
    assert config.model_size_bytes == gguf_file.stat().st_size
    # Must NOT infer quantization from filename
    assert config.quantization == "Unknown"
    assert config.host == "127.0.0.1"


def test_validate_executable_path_empty(model_service: ModelService) -> None:
    """Verify empty executable path raises ConfigurationError."""
    with pytest.raises(ConfigurationError) as exc:
        model_service.validate_executable_path("")
    assert "No llama-server executable path" in str(exc.value)


def test_validate_executable_path_nonexistent(model_service: ModelService) -> None:
    """Verify non-existent executable raises ConfigurationError."""
    with pytest.raises(ConfigurationError) as exc:
        model_service.validate_executable_path("/nonexistent/bin/llama-server")
    assert "not found" in str(exc.value)


def test_validate_executable_path_valid(model_service: ModelService, tmp_path: Path) -> None:
    """Verify valid executable passes validation."""
    fake_exec = tmp_path / "llama-server"
    fake_exec.write_text("#!/bin/sh\necho 'llama.cpp version 1.0'\n")
    fake_exec.chmod(fake_exec.stat().st_mode | 0o111)

    validated = model_service.validate_executable_path(fake_exec)
    assert validated.resolve() == fake_exec.resolve()
