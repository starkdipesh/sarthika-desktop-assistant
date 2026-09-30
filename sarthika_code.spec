# -*- mode: python ; coding: utf-8 -*-
"""Deterministic PyInstaller specification for Sarthika Code (Windows-first release).

Invariants:
- Standalone desktop application bundle (onedir mode for optimal startup time)
- Zero bundled GGUF models or weight files
- Zero bundled llama-server binaries (user downloads & configures separately)
- Zero bundled user databases, logs, or credentials
- Includes UI assets (SVG/ICO), documentation, and Apache-2.0 license
"""

import os
import sys
from pathlib import Path

block_cipher = None

REPO_ROOT = Path.cwd()

# Define required static data files
datas = [
    (str(REPO_ROOT / "assets"), "assets"),
    (str(REPO_ROOT / "LICENSE"), "."),
    (str(REPO_ROOT / "README.md"), "."),
]

# Hidden imports required by dynamic reflection or plugins
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "sqlalchemy.dialects.sqlite",
    "httpx",
    "anyio",
    "asyncio",
]

# Explicitly exclude heavy or unnecessary packages
excludes = [
    "tkinter",
    "unittest",
    "pytest",
    "IPython",
    "matplotlib",
    "numpy",
    "scipy",
    "torch",
    "transformers",
]

# Check version file
version_file = str(REPO_ROOT / "scripts" / "windows_version_info.txt")
if not os.path.exists(version_file) or sys.platform != "win32":
    version_file = None

icon_path = str(REPO_ROOT / "assets" / "icon.ico")
if not os.path.exists(icon_path):
    icon_path = None

a = Analysis(
    [str(REPO_ROOT / "src" / "sarthika_code" / "main.py")],
    pathex=[str(REPO_ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Safety check: Verify no model weights or private databases were picked up
forbidden_extensions = {".gguf", ".bin", ".safetensors", ".sqlite", ".sqlite3", ".db", ".env"}
for dest_name, src_path, _ in a.datas:
    ext = Path(src_path).suffix.lower()
    name = Path(src_path).name.lower()
    if ext in forbidden_extensions or name.startswith(".env"):
        raise ValueError(f"CRITICAL SAFETY VIOLATION: Forbidden file '{src_path}' in packaging datas!")

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SarthikaCode",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=version_file,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SarthikaCode",
)
