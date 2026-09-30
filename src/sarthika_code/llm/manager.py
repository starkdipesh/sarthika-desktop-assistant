"""Dedicated lifecycle manager for the local llama-server subprocess.

Implements safe subprocess execution with argument arrays (no shell=True),
strict localhost loopback binding, port discovery, stdout/stderr capture,
health checking, crash detection, graceful stop, and force termination.
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from sarthika_code.domain.config import ModelConfiguration
from sarthika_code.domain.errors import ConfigurationError, ServerError
from sarthika_code.domain.server import (
    ServerState,
    ServerStatus,
    validate_state_transition,
)
from sarthika_code.utils.logging import get_logger
from sarthika_code.utils.network import find_available_port, is_port_available

logger = get_logger("LlamaServerManager")


class LlamaServerManager:
    """Manages the lifecycle of a local llama-server child process."""

    def __init__(self, log_dir: Path | None = None) -> None:
        self.log_dir = log_dir
        self._status = ServerStatus()
        self._process: subprocess.Popen[str] | None = None
        self._log_file: Path | None = None
        self._listeners: list[Callable[[ServerStatus], None]] = []
        self._lock = threading.Lock()
        self._monitor_thread: threading.Thread | None = None
        self._stop_monitor_event = threading.Event()

    @property
    def status(self) -> ServerStatus:
        """Return the current snapshot of server status."""
        with self._lock:
            return self._status

    def add_state_listener(self, listener: Callable[[ServerStatus], None]) -> None:
        """Register a callback invoked whenever server status changes."""
        self._listeners.append(listener)

    def _set_status(self, new_state: ServerState, message: str, **kwargs: Any) -> ServerStatus:
        """Update status enforcing valid state transitions and notify listeners."""
        with self._lock:
            validate_state_transition(self._status.state, new_state)

            current_url = kwargs.get("url", self._status.url)
            current_pid = kwargs.get("pid", self._status.pid)
            started_at = kwargs.get("started_at", self._status.started_at)
            last_error = kwargs.get("last_error", self._status.last_error)
            is_managed = kwargs.get("is_managed", self._status.is_managed)

            if new_state == ServerState.STOPPED:
                current_pid = None
                current_url = None
                started_at = None

            self._status = ServerStatus(
                state=new_state,
                message=message,
                url=current_url,
                pid=current_pid,
                started_at=started_at,
                last_error=last_error,
                is_managed=is_managed,
            )
            updated = self._status

        logger.info("Server state transitioned: %s -> %s (%s)", updated.state.value, new_state.value, message)

        # Notify observers outside lock
        for listener in self._listeners:
            try:
                listener(updated)
            except Exception as e:
                logger.error("Error in server state listener: %s", e)

        return updated

    @staticmethod
    def build_command_args(config: ModelConfiguration) -> list[str]:
        """Construct a safe, validated argument array for llama-server.

        Guarantees:
        - No shell command strings (returns list of strings)
        - Host is strictly 127.0.0.1
        - Conservative, cross-version supported arguments
        """
        if config.host not in ("127.0.0.1", "localhost"):
            raise ConfigurationError(
                f"Forbidden host '{config.host}'. llama-server must bind strictly to 127.0.0.1.",
                user_guidance="For security and privacy, only local loopback (127.0.0.1) is permitted.",
            )

        return [
            str(config.executable_path),
            "--model", str(config.model_path),
            "--host", "127.0.0.1",
            "--port", str(config.port),
            "--ctx-size", str(config.context_size),
            "--threads", str(max(1, config.threads)),
        ]

    def start_server(
        self,
        config: ModelConfiguration,
        startup_timeout: float = 30.0,
    ) -> ServerStatus:
        """Launch the local llama-server subprocess and monitor readiness."""
        with self._lock:
            if self._status.state in (ServerState.STARTING, ServerState.READY, ServerState.GENERATING):
                raise ServerError(
                    "A llama-server instance is already active.",
                    user_guidance="Stop the active server before starting a new one.",
                )

        # Select and verify port availability
        port = config.port
        if not is_port_available(port, "127.0.0.1"):
            port = find_available_port(config.port)
            logger.info("Port %d busy; automatically selected available port %d.", config.port, port)
            # Create updated configuration with available port
            config = ModelConfiguration(
                model_path=config.model_path,
                model_name=config.model_name,
                model_size_bytes=config.model_size_bytes,
                executable_path=config.executable_path,
                context_size=config.context_size,
                threads=config.threads,
                host="127.0.0.1",
                port=port,
                quantization=config.quantization,
            )

        argv = self.build_command_args(config)
        server_url = f"http://127.0.0.1:{port}"

        self._set_status(
            ServerState.STARTING,
            message="Starting local llama-server...",
            url=server_url,
            is_managed=True,
            last_error=None,
        )

        # Configure log output file
        log_fp = None
        if self.log_dir is not None:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._log_file = self.log_dir / "llama_server.log"
            log_fp = open(self._log_file, "a", encoding="utf-8")  # noqa: SIM115

        try:
            # Spawn process without shell=True
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

            self._process = subprocess.Popen(
                argv,
                stdout=log_fp or subprocess.PIPE,
                stderr=log_fp or subprocess.PIPE,
                text=True,
                creationflags=creation_flags,
            )
            pid = self._process.pid
            logger.info("Spawned llama-server subprocess with PID %d at %s", pid, server_url)

        except Exception as e:
            if log_fp:
                log_fp.close()
            error_msg = f"Failed to spawn llama-server process: {e}"
            self._set_status(ServerState.START_FAILED, error_msg, last_error=str(e))
            raise ServerError(
                error_msg,
                user_guidance="Check that the llama-server executable path is valid and has execution permissions.",
            ) from e

        # Monitor startup and poll health check endpoint
        start_time = time.monotonic()
        started_utc = datetime.now(UTC)

        while time.monotonic() - start_time < startup_timeout:
            # Check if process exited prematurely
            returncode = self._process.poll()
            if returncode is not None:
                err_detail = f"Process exited with code {returncode}"
                self._set_status(ServerState.START_FAILED, f"Server failed to start ({err_detail}).", last_error=err_detail)
                raise ServerError(
                    f"llama-server terminated unexpectedly during startup ({err_detail}).",
                    user_guidance="Check Diagnostics logs to inspect model compatibility or memory limits.",
                )

            # Poll localhost health endpoint
            try:
                resp = httpx.get(f"{server_url}/health", timeout=1.0)
                if resp.status_code == 200:
                    status = self._set_status(
                        ServerState.READY,
                        message=f"Model Ready ({config.model_name})",
                        url=server_url,
                        pid=pid,
                        started_at=started_utc,
                    )
                    self._start_crash_monitor()
                    return status
            except (httpx.ConnectError, httpx.TimeoutException):
                pass

            time.sleep(0.25)

        # Timeout reached without healthy response
        timeout_err = f"Health check timed out after {startup_timeout:.0f} seconds."
        self._set_status(ServerState.START_FAILED, timeout_err, last_error=timeout_err)

        with self._lock:
            proc = self._process
            self._process = None

        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2.0)
            except Exception:
                with contextlib.suppress(Exception):
                    proc.kill()

        raise ServerError(
            f"llama-server failed to respond to health checks within {startup_timeout:.0f}s.",
            user_guidance="The server is taking too long to load the model. Try a smaller context size.",
        )

    def _start_crash_monitor(self) -> None:
        """Start a background daemon thread that detects unexpected process exit."""
        self._stop_monitor_event.clear()

        def _monitor() -> None:
            while not self._stop_monitor_event.is_set():
                if self._process is not None:
                    code = self._process.poll()
                    if code is not None:
                        # Process terminated
                        with self._lock:
                            current_state = self._status.state
                        if current_state in (ServerState.READY, ServerState.GENERATING):
                            err_msg = f"llama-server terminated unexpectedly with code {code}"
                            logger.error(err_msg)
                            self._set_status(ServerState.CRASHED, err_msg, last_error=err_msg)
                        break
                time.sleep(0.5)

        self._monitor_thread = threading.Thread(target=_monitor, daemon=True, name="LlamaServerCrashMonitor")
        self._monitor_thread.start()

    def stop_server(self, graceful_timeout: float = 5.0) -> ServerStatus:
        """Gracefully stop the managed llama-server, terminating forcefully on timeout."""
        self._stop_monitor_event.set()

        with self._lock:
            proc = self._process

        if proc is None or proc.poll() is not None:
            return self._set_status(ServerState.STOPPED, "Server is stopped.")

        with contextlib.suppress(Exception):
            self._set_status(ServerState.STOPPING, "Stopping llama-server...")

        logger.info("Sending termination signal to llama-server (PID %d)...", proc.pid)

        try:
            proc.terminate()
            proc.wait(timeout=graceful_timeout)
            logger.info("llama-server exited gracefully.")
        except subprocess.TimeoutExpired:
            logger.warning("llama-server failed to exit within %0.1fs; issuing force kill.", graceful_timeout)
            proc.kill()
            with contextlib.suppress(Exception):
                proc.wait(timeout=2.0)

        self._process = None
        return self._set_status(ServerState.STOPPED, "Server has stopped.")

    def connect_existing_server(self, url: str) -> ServerStatus:
        """Connect to an externally managed local llama-server instance."""
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if hostname not in ("127.0.0.1", "localhost"):
            raise ConfigurationError(
                f"External server address '{url}' is invalid.",
                user_guidance="Only local servers on 127.0.0.1 or localhost are supported for security.",
            )

        health_url = f"{url.rstrip('/')}/health"
        try:
            resp = httpx.get(health_url, timeout=3.0)
            if resp.status_code != 200:
                raise ServerError(
                    f"External server returned status code {resp.status_code}.",
                    user_guidance="Ensure your local llama-server is running and responding on /health.",
                )
        except Exception as e:
            self._set_status(
                ServerState.UNAVAILABLE,
                f"Could not connect to external server at {url}: {e}",
                last_error=str(e),
            )
            raise ServerError(
                f"Connection to local server at {url} failed: {e}",
                user_guidance="Verify the server is running on localhost at the specified port.",
            ) from e

        return self._set_status(
            ServerState.READY,
            message="Connected to external local server.",
            url=url,
            is_managed=False,
            started_at=datetime.now(UTC),
        )
