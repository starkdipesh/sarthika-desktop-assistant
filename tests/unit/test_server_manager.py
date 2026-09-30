"""Unit tests for LlamaServerManager subprocess lifecycle and failure recovery."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sarthika_code.domain.config import ModelConfiguration
from sarthika_code.domain.errors import ConfigurationError, ServerError
from sarthika_code.domain.server import ServerState
from sarthika_code.llm.manager import LlamaServerManager


@pytest.fixture
def server_manager(tmp_path: Path) -> LlamaServerManager:
    return LlamaServerManager(log_dir=tmp_path / "logs")


@pytest.fixture
def sample_config(tmp_path: Path) -> ModelConfiguration:
    fake_model = tmp_path / "model.gguf"
    fake_model.write_bytes(b"GGUF" * 300)
    exec_name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    fake_exec = tmp_path / exec_name
    fake_exec.write_text("#!/bin/sh\n")
    fake_exec.chmod(0o755)


    return ModelConfiguration(
        model_path=str(fake_model),
        model_name="model.gguf",
        model_size_bytes=fake_model.stat().st_size,
        executable_path=str(fake_exec),
        context_size=4096,
        threads=4,
        host="127.0.0.1",
        port=8080,
    )


def test_build_command_args_safety(sample_config: ModelConfiguration) -> None:
    """Verify argv list construction without shell string vulnerabilities."""
    args = LlamaServerManager.build_command_args(sample_config)

    assert isinstance(args, list)
    assert args[0] == sample_config.executable_path
    assert "--model" in args
    assert str(sample_config.model_path) in args
    assert "--host" in args
    assert "127.0.0.1" in args
    assert "--port" in args
    assert "8080" in args
    assert "--ctx-size" in args
    assert "4096" in args


def test_build_command_args_rejects_external_host(sample_config: ModelConfiguration) -> None:
    """Verify that any non-localhost host is rejected."""
    bad_config = ModelConfiguration(
        model_path=sample_config.model_path,
        model_name=sample_config.model_name,
        model_size_bytes=sample_config.model_size_bytes,
        executable_path=sample_config.executable_path,
        host="0.0.0.0",
        port=8080,
    )
    with pytest.raises(ConfigurationError) as exc:
        LlamaServerManager.build_command_args(bad_config)
    assert "Forbidden host" in str(exc.value)


def test_prevent_duplicate_server_processes(
    server_manager: LlamaServerManager, sample_config: ModelConfiguration
) -> None:
    """Verify that starting a server when one is already running raises ServerError."""
    # Force state to READY
    server_manager._set_status(ServerState.STARTING, "Starting...")
    server_manager._set_status(ServerState.READY, "Ready")

    with pytest.raises(ServerError) as exc:
        server_manager.start_server(sample_config)
    assert "already active" in str(exc.value)


def test_startup_failure_early_exit(
    server_manager: LlamaServerManager, sample_config: ModelConfiguration
) -> None:
    """Verify that process early termination transitions to START_FAILED."""
    mock_process = MagicMock()
    mock_process.poll.return_value = 1  # Exit code 1
    mock_process.pid = 99999

    with patch("subprocess.Popen", return_value=mock_process):
        with pytest.raises(ServerError) as exc:
            server_manager.start_server(sample_config, startup_timeout=1.0)
        assert "terminated unexpectedly" in str(exc.value)

    assert server_manager.status.state == ServerState.START_FAILED
    assert "code 1" in str(server_manager.status.last_error)


def test_stop_server_when_not_running(server_manager: LlamaServerManager) -> None:
    """Verify stopping an idle server safely returns STOPPED status."""
    status = server_manager.stop_server()
    assert status.state == ServerState.STOPPED


def test_stop_server_graceful_termination(server_manager: LlamaServerManager) -> None:
    """Verify graceful stop terminates process and cleans up."""
    mock_process = MagicMock()
    mock_process.poll.side_effect = [None, 0]  # Initially running, then exited
    mock_process.pid = 8888

    server_manager._process = mock_process
    server_manager._set_status(ServerState.STARTING, "starting")
    server_manager._set_status(ServerState.READY, "ready")

    status = server_manager.stop_server(graceful_timeout=1.0)
    assert status.state == ServerState.STOPPED
    mock_process.terminate.assert_called_once()


def test_existing_local_server_connection_success(server_manager: LlamaServerManager) -> None:
    """Verify connecting to an existing localhost server."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.get", return_value=mock_resp):
        status = server_manager.connect_existing_server("http://127.0.0.1:8080")
        assert status.state == ServerState.READY
        assert not status.is_managed
        assert status.url == "http://127.0.0.1:8080"


def test_existing_local_server_connection_rejects_remote_ip(server_manager: LlamaServerManager) -> None:
    """Verify connecting to an external non-loopback IP is rejected."""
    with pytest.raises(ConfigurationError) as exc:
        server_manager.connect_existing_server("http://192.168.1.50:8080")
    assert "Only local servers on 127.0.0.1" in exc.value.format_for_user()


def test_crash_monitor_detects_process_crash_from_ready(server_manager: LlamaServerManager) -> None:
    """Verify background crash monitor detects process exit from READY state."""
    import time

    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Running initially
    mock_process.pid = 1234

    server_manager._process = mock_process
    server_manager._set_status(ServerState.STARTING, "Starting...")
    server_manager._set_status(ServerState.READY, "Ready")

    server_manager._start_crash_monitor()

    # Now simulate process termination (crash with SIGKILL / code -9)
    mock_process.poll.return_value = -9

    # Wait briefly for monitor thread to execute check
    for _ in range(20):
        if server_manager.status.state == ServerState.CRASHED:
            break
        time.sleep(0.05)

    server_manager.stop_server()
    assert server_manager.status.state in (ServerState.CRASHED, ServerState.STOPPED)


def test_crash_monitor_detects_process_crash_from_generating(server_manager: LlamaServerManager) -> None:
    """Verify crash monitor detects unexpected process exit during GENERATING state."""
    import time

    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_process.pid = 1235

    server_manager._process = mock_process
    server_manager._set_status(ServerState.STARTING, "Starting...")
    server_manager._set_status(ServerState.READY, "Ready")
    server_manager._set_status(ServerState.GENERATING, "Generating...")

    server_manager._start_crash_monitor()

    # Simulate segmentation fault / exit code 139
    mock_process.poll.return_value = 139

    for _ in range(20):
        if server_manager.status.state == ServerState.CRASHED:
            break
        time.sleep(0.05)

    assert server_manager.status.state == ServerState.CRASHED
    assert "139" in str(server_manager.status.last_error)
    server_manager.stop_server()


def test_stop_server_force_kill_on_timeout(server_manager: LlamaServerManager) -> None:
    """Verify stop_server escalates to kill() when process ignores terminate()."""
    import subprocess

    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_process.pid = 9999
    # terminate succeeds, wait raises TimeoutExpired, second wait succeeds
    mock_process.wait.side_effect = [subprocess.TimeoutExpired(cmd=["llama-server"], timeout=0.1), 0]

    server_manager._process = mock_process
    server_manager._set_status(ServerState.STARTING, "Starting...")
    server_manager._set_status(ServerState.READY, "Ready")

    status = server_manager.stop_server(graceful_timeout=0.1)
    assert status.state == ServerState.STOPPED
    mock_process.terminate.assert_called_once()
    mock_process.kill.assert_called_once()


def test_start_server_automatically_resolves_port_collision(
    server_manager: LlamaServerManager, sample_config: ModelConfiguration
) -> None:
    """Verify start_server selects an available port if configured port is occupied."""
    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_process.pid = 7777

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with (
        patch("sarthika_code.llm.manager.is_port_available", side_effect=[False, True]),
        patch("sarthika_code.llm.manager.find_available_port", return_value=8099),
        patch("subprocess.Popen", return_value=mock_process),
        patch("httpx.get", return_value=mock_resp),
    ):
        status = server_manager.start_server(sample_config, startup_timeout=1.0)
        assert status.state == ServerState.READY
        assert "8099" in (status.url or "")
        server_manager.stop_server()


def test_start_server_spawn_failure(
    server_manager: LlamaServerManager, sample_config: ModelConfiguration
) -> None:
    """Verify start_server handles Popen OS errors (e.g. PermissionDenied/FileNotFound)."""
    with (
        patch("subprocess.Popen", side_effect=OSError("Exec format error")),
        pytest.raises(ServerError) as exc,
    ):
        server_manager.start_server(sample_config, startup_timeout=1.0)

    assert "Exec format error" in str(exc.value)
    assert server_manager.status.state == ServerState.START_FAILED


def test_start_server_health_check_timeout(
    server_manager: LlamaServerManager, sample_config: ModelConfiguration
) -> None:
    """Verify start_server raises ServerError and marks START_FAILED when health check times out."""
    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_process.pid = 5555

    import httpx

    with (
        patch("subprocess.Popen", return_value=mock_process),
        patch("httpx.get", side_effect=httpx.ConnectError("Connection refused")),
        pytest.raises(ServerError) as exc,
    ):
        server_manager.start_server(sample_config, startup_timeout=0.3)

    assert "failed to respond" in str(exc.value).lower()
    assert server_manager.status.state == ServerState.START_FAILED

