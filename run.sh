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
if [ ! -f "$SCRIPT_DIR/.setup_complete" ] || [ ! -f "$SCRIPT_DIR/.venv/bin/python" ] || [ ! -f "$SCRIPT_DIR/.venv/bin/pip" ]; then
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
    rm -rf "$SCRIPT_DIR/.venv"
    if ! "$PY_BOOT" -m venv "$SCRIPT_DIR/.venv" 2>/dev/null || [ ! -f "$SCRIPT_DIR/.venv/bin/pip" ]; then
        echo "=================================================================="
        echo "Notice: 'python3-venv' is missing or incomplete on your system."
        echo "Attempting to install python3-venv and python3-pip..."
        echo "=================================================================="
        if command -v sudo &>/dev/null; then
            sudo apt update && sudo apt install -y python3-venv python3-pip
            rm -rf "$SCRIPT_DIR/.venv"
            "$PY_BOOT" -m venv "$SCRIPT_DIR/.venv"
        fi
        
        if [ ! -f "$SCRIPT_DIR/.venv/bin/python" ] || [ ! -f "$SCRIPT_DIR/.venv/bin/pip" ]; then
            echo "=================================================================="
            echo "Error: Virtual environment could not be created with pip."
            echo "Please run this command once to enable Python apps on Ubuntu:"
            echo "   sudo apt install -y python3-venv python3-pip"
            echo "Then run ./run.sh again."
            echo "=================================================================="
            if command -v zenity &>/dev/null; then
                zenity --error --title="Sarthika Code Setup" --text="Missing Python package.\nPlease run in terminal:\nsudo apt install -y python3-venv python3-pip" 2>/dev/null || true
            fi
            exit 1
        fi
    fi

    # Install package dependencies
    echo "• Installing dependencies (PySide6, SQLAlchemy, httpx)..."
    notify_user "Installing dependencies... This will take about 1-2 minutes."

    "$SCRIPT_DIR/.venv/bin/pip" install --upgrade pip --quiet
    if ! "$SCRIPT_DIR/.venv/bin/pip" install --ignore-requires-python -e "$SCRIPT_DIR"; then
        echo "=================================================================="
        echo "Error: Failed to install application dependencies."
        echo "Please check your internet connection and try again."
        echo "=================================================================="
        rm -rf "$SCRIPT_DIR/.venv" 2>/dev/null || true
        exit 1
    fi
    touch "$SCRIPT_DIR/.setup_complete"
    echo "• Setup completed successfully!"
    echo "=================================================================="
fi

PYTHON_EXEC="$SCRIPT_DIR/.venv/bin/python"

if [ ! -f "$PYTHON_EXEC" ]; then
    echo "Error: Python environment is not initialized properly. Please re-run ./run.sh"
    exit 1
fi

# 2. Register Linux Desktop shortcut in user application menu
DESKTOP_DIR="$HOME/.local/share/applications"
if [ -d "$DESKTOP_DIR" ]; then
    mkdir -p "$HOME/.local/share/icons/hicolor/256x256/apps"
    mkdir -p "$HOME/.local/share/pixmaps"
    if [ -f "$SCRIPT_DIR/assets/icon.png" ]; then
        cp "$SCRIPT_DIR/assets/icon.png" "$HOME/.local/share/icons/hicolor/256x256/apps/sarthika-code.png" 2>/dev/null || true
        cp "$SCRIPT_DIR/assets/icon.png" "$HOME/.local/share/pixmaps/sarthika-code.png" 2>/dev/null || true
        if command -v gtk-update-icon-cache &>/dev/null; then
            gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
        fi
    fi

    cat <<EOF > "$DESKTOP_DIR/sarthika-code.desktop"
[Desktop Entry]
Name=Sarthika Code
Comment=Private, local-first desktop AI coding assistant
Exec="$SCRIPT_DIR/run.sh"
Path=$SCRIPT_DIR
Icon=$HOME/.local/share/icons/hicolor/256x256/apps/sarthika-code.png
Terminal=false
Type=Application
Categories=Development;IDE;Utility;
StartupWMClass=SarthikaCode
EOF
    chmod +x "$DESKTOP_DIR/sarthika-code.desktop" 2>/dev/null || true

    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi
fi

# 3. Launch application
exec "$PYTHON_EXEC" "$SCRIPT_DIR/run.py" "$@"
