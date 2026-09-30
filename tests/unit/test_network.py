"""Unit tests for network utility functions (port availability and loopback discovery)."""

from __future__ import annotations

import socket

from sarthika_code.utils.network import find_available_port, is_port_available


def test_is_port_available_free_port() -> None:
    """Verify is_port_available returns True for a freshly unbound port."""
    # Find a free ephemeral port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = int(s.getsockname()[1])

    # Once closed, the port should be available
    assert is_port_available(free_port, "127.0.0.1") is True


def test_is_port_available_bound_port() -> None:
    """Verify is_port_available returns False when a port is actively occupied."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        busy_port = int(s.getsockname()[1])

        # While socket is open and listening, it must report unavailable
        assert is_port_available(busy_port, "127.0.0.1") is False


def test_find_available_port_returns_open_port() -> None:
    """Verify find_available_port discovers an available loopback port."""
    port = find_available_port(preferred_port=29100)
    assert isinstance(port, int)
    assert 1024 <= port <= 65535
    assert is_port_available(port, "127.0.0.1") is True


def test_find_available_port_skips_occupied_port() -> None:
    """Verify find_available_port advances past busy ports to find the next free one."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        busy_port = int(s.getsockname()[1])

        discovered = find_available_port(preferred_port=busy_port, max_scan_attempts=5)
        assert discovered != busy_port
        assert is_port_available(discovered, "127.0.0.1") is True
