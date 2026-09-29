"""Model validation and server orchestration service for Sarthika Code.

Validates GGUF model files and llama-server executables upon explicit user selection.
Never scans the filesystem automatically and never assumes quantization from filenames.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sarthika_code.domain.config import AppSettings, ModelConfiguration
from sarthika_code.domain.errors import ConfigurationError, ModelValidationError
from sarthika_code.domain.server import ServerStatus
from sarthika_code.llm.manager import LlamaServerManager
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.utils.logging import get_logger

logger = get_logger("ModelService")


class ModelService:
    """Service handling model file validation, executable verification, and server orchestration."""

    def __init__(
        self,
        settings_service: SettingsService,
        server_manager: LlamaServerManager,
    ) -> None:
        self.settings_service = settings_service
        self.server_manager = server_manager

    def validate_model_path(self, model_path: str | Path | None) -> ModelConfiguration:
        """Validate an explicitly selected local GGUF model file.

        Enforces:
        - Path is not empty and file exists
        - Extension is strictly .gguf (case-insensitive)
        - Does not scan the filesystem
        - Does not assume quantization from filename (marked as 'Unknown')
        """
        if not model_path:
            raise ModelValidationError(
                "No model file path provided.",
                user_guidance="Please choose a local .gguf model file using the file selector.",
            )

        path = Path(model_path).resolve()

        if not path.exists():
            raise ModelValidationError(
                f"Model file not found at: {path}",
                user_guidance="Verify the model file path and make sure the file exists on disk.",
            )

        if not path.is_file():
            raise ModelValidationError(
                f"Path '{path}' is a directory, not a model file.",
                user_guidance="Select a specific .gguf file, not a folder.",
            )

        if path.suffix.lower() != ".gguf":
            raise ModelValidationError(
                f"File '{path.name}' has invalid extension '{path.suffix}'. Only .gguf models are supported.",
                user_guidance="Ensure you selected a valid GGUF model file.",
            )

        size_bytes = path.stat().st_size
        if size_bytes < 1024:
            raise ModelValidationError(
                f"Model file '{path.name}' is too small ({size_bytes} bytes). The file appears corrupted or empty.",
                user_guidance="Re-download the complete GGUF model file.",
            )

        # Quantization is explicitly marked as Unknown rather than guessed from filename
        settings = self.settings_service.load_settings()
        executable = settings.llama_server_path or ""

        return ModelConfiguration(
            model_path=str(path),
            model_name=path.name,
            model_size_bytes=size_bytes,
            executable_path=executable,
            context_size=settings.context_size,
            threads=settings.threads,
            host=settings.server_host,
            port=settings.server_port,
            quantization="Unknown",
        )

    def validate_executable_path(self, exec_path: str | Path | None) -> Path:
        """Validate an explicitly selected llama-server executable.

        Enforces:
        - Path is not empty and exists as a file
        - Possesses operating-system execution permissions
        - Optionally probes --version with a safe timeout
        """
        if not exec_path:
            raise ConfigurationError(
                "No llama-server executable path provided.",
                user_guidance="Select the llama-server executable downloaded from llama.cpp releases.",
            )

        path = Path(exec_path).resolve()

        if not path.exists():
            raise ConfigurationError(
                f"Executable not found at: {path}",
                user_guidance="Verify the executable path and ensure llama-server is installed.",
            )

        if not path.is_file():
            raise ConfigurationError(
                f"Path '{path}' is a directory, not an executable file.",
                user_guidance="Select the specific llama-server binary file.",
            )

        # Operating system specific execution permission check
        if sys.platform != "win32":
            if not os.access(path, os.X_OK):
                raise ConfigurationError(
                    f"File '{path.name}' does not have execution permissions.",
                    user_guidance=f"Run 'chmod +x {path}' in your terminal to grant execute permissions.",
                )
        else:
            if path.suffix.lower() not in (".exe", ".bat", ".cmd"):
                raise ConfigurationError(
                    f"File '{path.name}' is not an executable on Windows (.exe expected).",
                    user_guidance="Select the llama-server.exe file.",
                )

        # Safe non-blocking version check
        try:
            res = subprocess.run(
                [str(path), "--version"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
            logger.info("Probed executable version: %s", (res.stdout or res.stderr or "").strip())
        except Exception as e:
            logger.warning("Could not execute --version probe on '%s': %s", path.name, e)

        return path

    def start_configured_server(
        self,
        model_path: str | None = None,
        exec_path: str | None = None,
        context_size: int | None = None,
        port: int | None = None,
    ) -> ServerStatus:
        """Validate parameters and start the managed llama-server."""
        settings = self.settings_service.load_settings()

        effective_model = model_path or settings.model_path
        effective_exec = exec_path or settings.llama_server_path
        effective_ctx = context_size or settings.context_size
        effective_port = port or settings.server_port

        validated_exec = self.validate_executable_path(effective_exec)
        model_config = self.validate_model_path(effective_model)

        config = ModelConfiguration(
            model_path=model_config.model_path,
            model_name=model_config.model_name,
            model_size_bytes=model_config.model_size_bytes,
            executable_path=str(validated_exec),
            context_size=effective_ctx,
            threads=settings.threads,
            host="127.0.0.1",
            port=effective_port,
            quantization=model_config.quantization,
        )

        # Update persistent settings
        updated_settings = AppSettings(
            theme=settings.theme,
            model_path=config.model_path,
            llama_server_path=config.executable_path,
            server_host="127.0.0.1",
            server_port=config.port,
            context_size=config.context_size,
            mock_mode=settings.mock_mode,
            threads=config.threads,
        )
        self.settings_service.save_settings(updated_settings)

        return self.server_manager.start_server(config)

    def stop_server(self) -> ServerStatus:
        """Stop the active llama-server instance."""
        return self.server_manager.stop_server()

    def get_status(self) -> ServerStatus:
        """Return the current server status."""
        return self.server_manager.status
