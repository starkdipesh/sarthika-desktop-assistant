"""Unit tests for ModelService: model and executable validation."""

from __future__ import annotations

import sys
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
    exec_name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    fake_exec = tmp_path / exec_name
    fake_exec.write_text("#!/bin/sh\necho 'llama.cpp version 1.0'\n")
    fake_exec.chmod(fake_exec.stat().st_mode | 0o111)

    validated = model_service.validate_executable_path(fake_exec)
    assert validated.resolve() == fake_exec.resolve()


def test_start_configured_server_fails_when_model_removed(
    model_service: ModelService, tmp_path: Path
) -> None:
    """Verify start_configured_server raises ModelValidationError if the model file was deleted/moved."""
    exec_name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    fake_exec = tmp_path / exec_name
    fake_exec.write_text("#!/bin/sh\n")
    fake_exec.chmod(0o755)


    fake_model = tmp_path / "model.gguf"
    fake_model.write_bytes(b"GGUF_HEADER_DATA" * 100)

    # Save paths in settings
    from sarthika_code.domain.config import AppSettings
    model_service.settings_service.save_settings(
        AppSettings(
            model_path=str(fake_model),
            llama_server_path=str(fake_exec),
        )
    )

    # Now remove the model file to simulate being moved or deleted
    fake_model.unlink()

    with pytest.raises(ModelValidationError) as exc:
        model_service.start_configured_server()
    assert "not found" in str(exc.value).lower()


def test_start_configured_server_fails_when_executable_missing(
    model_service: ModelService, tmp_path: Path
) -> None:
    """Verify start_configured_server raises ConfigurationError if the executable is missing."""
    fake_model = tmp_path / "model.gguf"
    fake_model.write_bytes(b"GGUF_HEADER_DATA" * 100)

    from sarthika_code.domain.config import AppSettings
    model_service.settings_service.save_settings(
        AppSettings(
            model_path=str(fake_model),
            llama_server_path=str(tmp_path / "missing_exec"),
        )
    )

    with pytest.raises(ConfigurationError) as exc:
        model_service.start_configured_server()
    assert "not found" in str(exc.value).lower()


def test_mock_mode_works_with_no_model_configured() -> None:
    """Verify mock mode functions completely without any model file or llama-server executable configured."""
    import asyncio

    from sarthika_code.domain.config import AppSettings
    from sarthika_code.llm.base import ChatMessage
    from sarthika_code.llm.factory import LLMProviderFactory
    from sarthika_code.llm.mock import MockLLMProvider

    # No model or executable paths set
    settings = AppSettings(mock_mode=True, model_path="", llama_server_path="")
    provider = LLMProviderFactory.create_provider(settings)

    assert isinstance(provider, MockLLMProvider)
    assert asyncio.run(provider.health_check()) is True

    # Streaming works without any files on disk
    messages = [ChatMessage(role="user", content="Hello in mock mode")]

    async def _test_stream() -> list[str]:
        tokens = []
        async for event in provider.stream_chat(messages):
            from sarthika_code.llm.base import StreamTokenEvent
            if isinstance(event, StreamTokenEvent):
                tokens.append(event.delta)
        return tokens

    tokens = asyncio.run(_test_stream())
    assert len(tokens) > 0

