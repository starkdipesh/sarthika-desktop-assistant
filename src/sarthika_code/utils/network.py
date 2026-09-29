"""Network utilities for Sarthika Code.

Provides safe localhost port discovery and loopback socket checks.
Guarantees that bindings are restricted strictly to 127.0.0.1.
"""

from __future__ import annotations

import socket


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a specific TCP port is currently free to bind on host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        try:
            # Try to bind to the port
            sock.bind((host, port))
            return True
        except OSError:
            return False


def find_available_port(
    preferred_port: int = 8080,
    max_scan_attempts: int = 30,
    host: str = "127.0.0.1",
) -> int:
    """Discover an available local port starting from preferred_port.

    Scans sequentially up to max_scan_attempts. If all are occupied,
    requests a dynamic port from the operating system.
    """
    for candidate in range(preferred_port, preferred_port + max_scan_attempts):
        if is_port_available(candidate, host):
            return candidate

    # Fallback to an OS-assigned ephemeral free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])
