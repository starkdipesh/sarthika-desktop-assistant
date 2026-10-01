#!/usr/bin/env bash
# ==============================================================================
# Sarthika Code — Universal One-Click Launcher (Linux / macOS)
# Automatically bootstraps environment, creates desktop shortcut, and runs app.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Helper for desktop notifications
notify_user() {
    if command -v notify-send &>/dev/null; then
        notify-send "Sarthika Code" "$1" 2>/dev/null || true
    fi
    echo "$1"
}

# 1. Locate or create Python virtual environment
if [ ! -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    echo "=================================================================="
    echo "Sarthika Code — First-Time Automatic Setup"
    echo "=================================================================="
    notify_user "Configuring environment on your computer... Please wait a moment."

    if command -v python3 &>/dev/null; then
        PY_BOOT="python3"
    elif command -v python &>/dev/null; then
        PY_BOOT="python"
    else
        echo "Error: Python 3 was not detected on your system."
        echo "Please install Python 3 from your package manager: sudo apt install python3"
        exit 1
    fi

    # Create virtual environment
    echo "• Creating local virtual environment in .venv..."
    if ! "$PY_BOOT" -m venv "$SCRIPT_DIR/.venv"; then
        echo "=================================================================="
        echo "Notice: On Ubuntu/Debian, the 'python3-venv' package may be required."
        echo "Please run: sudo apt install -y python3-venv python3-pip"
        echo "Then run ./run.sh again."
        echo "=================================================================="
        exit 1
    fi

    # Install package dependencies
    echo "• Installing dependencies (PySide6, SQLAlchemy, httpx)..."
    notify_user "Installing dependencies... This will take about 1-2 minutes."
    "$SCRIPT_DIR/.venv/bin/pip" install --upgrade pip --quiet
    if ! "$SCRIPT_DIR/.venv/bin/pip" install -e "$SCRIPT_DIR" --quiet; then
        echo "Failed to install dependencies."
        exit 1
    fi
    echo "• Setup completed successfully!"
    echo "=================================================================="
fi

PYTHON_EXEC="$SCRIPT_DIR/.venv/bin/python"

# 2. Register Linux Desktop shortcut in user application menu
DESKTOP_DIR="$HOME/.local/share/applications"
if [ -d "$DESKTOP_DIR" ]; then
    cat <<EOF > "$DESKTOP_DIR/sarthika-code.desktop"
[Desktop Entry]
Name=Sarthika Code
Comment=Private, local-first desktop AI coding assistant
Exec=$SCRIPT_DIR/run.sh
Icon=$SCRIPT_DIR/assets/icon.png
Terminal=false
Type=Application
Categories=Development;IDE;
StartupWMClass=SarthikaCode
EOF
    chmod +x "$DESKTOP_DIR/sarthika-code.desktop" 2>/dev/null || true
fi

# 3. Launch application
exec "$PYTHON_EXEC" "$SCRIPT_DIR/run.py" "$@"
