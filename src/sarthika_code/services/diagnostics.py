"""System, runtime, and hardware diagnostics service for Sarthika Code.

Compiles technical metrics, hardware capacity, and server status
into a privacy-redacted report suitable for troubleshooting.
"""

from __future__ import annotations

import contextlib
import os
import platform
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sarthika_code.app.paths import AppPaths
from sarthika_code.domain.server import ServerStatus
from sarthika_code.services.settings_service import SettingsService
from sarthika_code.utils.logging import _sanitize_path


@dataclass(frozen=True)
class DiagnosticsReport:
    """Structured report containing diagnostic indicators and environment metrics."""

    app_version: str
    python_version: str
    os_summary: str
    cpu_summary: str
    ram_summary: str
    model_path: str
    model_name: str
    model_size: str
    quantization: str
    llama_server_path: str
    server_url: str
    server_state: str
    server_pid: str
    context_size: int
    log_location: str
    database_location: str

    def to_formatted_text(self, redact: bool = True) -> str:
        """Format the report into a clean, human-readable multi-line string."""
        lines = [
            "================ SARTHIKA CODE DIAGNOSTICS ================",
            f"Application Version   : {self.app_version}",
            f"Python Version        : {self.python_version}",
            f"Operating System      : {self.os_summary}",
            f"CPU Summary           : {self.cpu_summary}",
            f"RAM Summary           : {self.ram_summary}",
            "-----------------------------------------------------------",
            f"Model Path            : {self.model_path if not redact else _sanitize_path(self.model_path)}",
            f"Model Filename        : {self.model_name}",
            f"Model Size            : {self.model_size}",
            f"Quantization          : {self.quantization}",
            f"llama-server Binary   : {self.llama_server_path if not redact else _sanitize_path(self.llama_server_path)}",
            f"Server URL            : {self.server_url}",
            f"Server State          : {self.server_state}",
            f"Server PID            : {self.server_pid}",
            f"Context Setting       : {self.context_size} tokens",
            "-----------------------------------------------------------",
            f"Log File Location     : {self.log_location if not redact else _sanitize_path(self.log_location)}",
            f"Database Location     : {self.database_location if not redact else _sanitize_path(self.database_location)}",
            "===========================================================",
        ]
        return "\n".join(lines)


class DiagnosticsService:
    """Compiles hardware, storage, and server status into a diagnostics report."""

    def __init__(
        self,
        paths: AppPaths,
        settings_service: SettingsService,
        status_provider: Callable[[], ServerStatus] | None = None,
    ) -> None:
        self.paths = paths
        self.settings_service = settings_service
        self.status_provider = status_provider

    def _get_cpu_summary(self) -> str:
        """Query CPU information safely without external dependencies."""
        cpu_count = os.cpu_count() or "Unknown"
        processor = platform.processor() or platform.machine() or "Generic"
        return f"{processor} ({cpu_count} logical cores)"

    def _get_ram_summary(self) -> str:
        """Query total and available RAM safely across platforms."""
        if sys.platform == "linux" and os.path.exists("/proc/meminfo"):
            try:
                meminfo: dict[str, int] = {}
                with open("/proc/meminfo", encoding="utf-8") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            val = parts[1].split()[0].strip()
                            meminfo[key] = int(val)
                total_gb = meminfo.get("MemTotal", 0) / (1024 * 1024)
                avail_gb = meminfo.get("MemAvailable", 0) / (1024 * 1024)
                return f"{total_gb:.1f} GB Total ({avail_gb:.1f} GB Available)"
            except Exception:
                pass
        return "Unknown"

    def collect_diagnostics(self) -> DiagnosticsReport:
        """Generate a complete diagnostic snapshot."""
        settings = self.settings_service.load_settings()

        status = ServerStatus()
        if self.status_provider is not None:
            with contextlib.suppress(Exception):
                status = self.status_provider()

        model_name = "None"
        model_size_str = "None"
        model_path_str = settings.model_path or "None configured"

        if settings.model_path and Path(settings.model_path).exists():
            p = Path(settings.model_path)
            model_name = p.name
            try:
                size_mb = p.stat().st_size / (1024 * 1024)
                model_size_str = f"{size_mb:.1f} MB ({p.stat().st_size} bytes)"
            except Exception:
                pass

        return DiagnosticsReport(
            app_version="0.1.0",
            python_version=platform.python_version(),
            os_summary=f"{platform.system()} {platform.release()} ({platform.architecture()[0]})",
            cpu_summary=self._get_cpu_summary(),
            ram_summary=self._get_ram_summary(),
            model_path=model_path_str,
            model_name=model_name,
            model_size=model_size_str,
            quantization="Unknown",  # Unknown until verified from server metadata probe
            llama_server_path=settings.llama_server_path or "None configured",
            server_url=status.url or f"http://{settings.server_host}:{settings.server_port}",
            server_state=status.state.value,
            server_pid=str(status.pid) if status.pid else "None",
            context_size=settings.context_size,
            log_location=str(self.paths.log_file),
            database_location=str(self.paths.database_file),
        )
