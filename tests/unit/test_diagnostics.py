"""Unit tests for DiagnosticsService and path redaction."""

from __future__ import annotations

from pathlib import Path

from sarthika_code.app.paths import AppPaths
from sarthika_code.domain.config import AppSettings
from sarthika_code.domain.server import ServerState, ServerStatus
from sarthika_code.services.diagnostics import DiagnosticsService
from sarthika_code.services.settings_service import SettingsService


def test_collect_diagnostics(
    temp_paths: AppPaths, settings_service: SettingsService, tmp_path: Path
) -> None:
    """Verify DiagnosticsService populates all diagnostic metrics."""
    fake_model = tmp_path / "model.gguf"
    fake_model.write_bytes(b"DATA" * 500)

    settings = AppSettings(
        model_path=str(fake_model),
        llama_server_path="/usr/local/bin/llama-server",
        server_port=8080,
        context_size=4096,
    )
    settings_service.save_settings(settings)

    diag_service = DiagnosticsService(
        paths=temp_paths,
        settings_service=settings_service,
        status_provider=lambda: ServerStatus(
            state=ServerState.READY,
            url="http://127.0.0.1:8080",
            pid=12345,
        ),
    )

    report = diag_service.collect_diagnostics()
    assert report.app_version == "0.1.0"
    assert report.server_state == "READY"
    assert report.server_pid == "12345"
    assert report.model_name == "model.gguf"
    assert report.quantization == "Unknown"
    assert "8080" in report.server_url


def test_diagnostics_report_redaction(
    temp_paths: AppPaths, settings_service: SettingsService
) -> None:
    """Verify that to_formatted_text(redact=True) redacts home directory paths."""
    home = Path.home()
    settings = AppSettings(
        model_path=f"{home}/models/qwen.gguf",
        llama_server_path=f"{home}/bin/llama-server",
    )
    settings_service.save_settings(settings)

    diag_service = DiagnosticsService(
        paths=temp_paths,
        settings_service=settings_service,
        status_provider=lambda: ServerStatus(),
    )

    report = diag_service.collect_diagnostics()
    formatted = report.to_formatted_text(redact=True)

    # Home path should be redacted to ~
    assert str(home) not in formatted
    assert "~/models/qwen.gguf" in formatted
    assert "~/bin/llama-server" in formatted
