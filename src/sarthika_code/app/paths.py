"""OS-appropriate directory path management for Sarthika Code.

This module determines standard directories for application configuration,
persistent databases, runtime logs, and user exports across Windows, Linux,
and macOS. It strictly avoids storing user state inside the source repository.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    """Immutable representation of all runtime application directories."""

    config_dir: Path
    data_dir: Path
    database_dir: Path
    logs_dir: Path
    exports_dir: Path

    @property
    def database_file(self) -> Path:
        """Absolute path to the primary SQLite database file."""
        return self.database_dir / "sarthika.db"

    @property
    def log_file(self) -> Path:
        """Absolute path to the active rotating application log file."""
        return self.logs_dir / "sarthika.log"

    def ensure_directories(self) -> None:
        """Create all required application directories with safe permissions."""
        import contextlib

        for path in (
            self.config_dir,
            self.data_dir,
            self.database_dir,
            self.logs_dir,
            self.exports_dir,
        ):
            with contextlib.suppress(OSError):
                path.mkdir(parents=True, exist_ok=True)


def get_app_paths(base_override: Path | None = None) -> AppPaths:
    """Resolve OS-appropriate application paths.

    If base_override is provided, all application directories will be placed
    under that base path (used primarily for test isolation).

    Expected Windows Paths:
        - Config: %APPDATA%\\sarthika_code or %LOCALAPPDATA%\\sarthika_code\\config
        - Data: %LOCALAPPDATA%\\sarthika_code\\data
        - Database: %LOCALAPPDATA%\\sarthika_code\\data\\sarthika.db
        - Logs: %LOCALAPPDATA%\\sarthika_code\\logs\\sarthika.log
        - Exports: %USERPROFILE%\\Documents\\SarthikaCode\\exports

    Expected Linux / POSIX Paths:
        - Config: ~/.config/sarthika_code ($XDG_CONFIG_HOME)
        - Data: ~/.local/share/sarthika_code ($XDG_DATA_HOME)
        - Database: ~/.local/share/sarthika_code/sarthika.db
        - Logs: ~/.local/state/sarthika_code/logs ($XDG_STATE_HOME)
        - Exports: ~/Documents/SarthikaCode/exports
    """
    if base_override is not None:
        base = Path(base_override).resolve()
        return AppPaths(
            config_dir=base / "config",
            data_dir=base / "data",
            database_dir=base / "data",
            logs_dir=base / "logs",
            exports_dir=base / "exports",
        )

    # Check for environment variable override
    env_override = os.environ.get("SARTHIKA_HOME")
    if env_override:
        base = Path(env_override).resolve()
        return AppPaths(
            config_dir=base / "config",
            data_dir=base / "data",
            database_dir=base / "data",
            logs_dir=base / "logs",
            exports_dir=base / "exports",
        )

    app_name = "sarthika_code"
    home = Path.home()

    if sys.platform == "win32":
        # Windows standard paths
        local_app_data = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        roaming_app_data = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        user_profile = Path(os.environ.get("USERPROFILE", home))

        config_dir = roaming_app_data / app_name
        data_dir = local_app_data / app_name / "data"
        database_dir = data_dir
        logs_dir = local_app_data / app_name / "logs"
        exports_dir = user_profile / "Documents" / "SarthikaCode" / "exports"

    elif sys.platform == "darwin":
        # macOS standard paths
        app_support = home / "Library" / "Application Support" / app_name
        config_dir = app_support / "config"
        data_dir = app_support / "data"
        database_dir = data_dir
        logs_dir = home / "Library" / "Logs" / app_name
        exports_dir = home / "Documents" / "SarthikaCode" / "exports"

    else:
        # Linux and other POSIX (FreeDesktop XDG standards)
        xdg_config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        xdg_data_home = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share"))
        xdg_state_home = Path(os.environ.get("XDG_STATE_HOME", home / ".local" / "state"))

        config_dir = xdg_config_home / app_name
        data_dir = xdg_data_home / app_name
        database_dir = data_dir
        logs_dir = xdg_state_home / app_name / "logs"
        exports_dir = home / "Documents" / "SarthikaCode" / "exports"

    return AppPaths(
        config_dir=config_dir,
        data_dir=data_dir,
        database_dir=database_dir,
        logs_dir=logs_dir,
        exports_dir=exports_dir,
    )
