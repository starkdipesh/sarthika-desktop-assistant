#!/usr/bin/env bash
# ==============================================================================
# Sarthika Code — 1-Click Ubuntu Installer & Setup Script
# Installs application to ~/.local/share/sarthika-code, installs prerequisites,
# adds Desktop shortcut to App Launcher, and starts the application.
# ==============================================================================

set -e

INSTALL_DIR="$HOME/.local/share/sarthika-code"
REPO_URL="https://github.com/starkdipesh/sarthika-desktop-assistant.git"
DESKTOP_ENTRY="$HOME/.local/share/applications/sarthika-code.desktop"

echo "=================================================================="
echo "         Sarthika Code — 1-Click Installer for Ubuntu            "
echo "=================================================================="

# Helper notification
notify_status() {
    if command -v notify-send &>/dev/null; then
        notify-send "Sarthika Code" "$1" 2>/dev/null || true
    fi
    echo "• $1"
}

# 1. Check & Install System Prerequisites (python3, venv, git, curl)
echo "Step 1/4: Checking system requirements..."
MISSING_PKGS=()

if ! command -v git &>/dev/null; then
    MISSING_PKGS+=("git")
fi
if ! command -v python3 &>/dev/null; then
    MISSING_PKGS+=("python3" "python3-venv")
elif ! python3 -m ensurepip --version &>/dev/null; then
    MISSING_PKGS+=("python3-venv")
fi
if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null; then
    MISSING_PKGS+=("python3-pip")
fi

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo "The following system packages are required: ${MISSING_PKGS[*]}"
    echo "Installing missing packages with sudo (you may be asked for your password)..."
    sudo apt update -qq
    sudo apt install -y "${MISSING_PKGS[@]}"
fi

# 2. Setup Application Directory in hidden/system user space (~/.local/share/sarthika-code)
echo "Step 2/4: Setting up application files..."
if [ -d "$INSTALL_DIR/.git" ]; then
    notify_status "Updating existing Sarthika Code installation..."
    cd "$INSTALL_DIR"
    git pull --quiet || true
else
    notify_status "Downloading Sarthika Code..."
    rm -rf "$INSTALL_DIR"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR" --quiet
    cd "$INSTALL_DIR"
fi

# 3. Create isolated virtual environment & install requirements
echo "Step 3/4: Configuring Python environment and dependencies..."
notify_status "Configuring dependencies (takes 1-2 minutes on first run)..."

if [ ! -f "$INSTALL_DIR/.venv/bin/python" ]; then
    rm -rf "$INSTALL_DIR/.venv"
    python3 -m venv "$INSTALL_DIR/.venv"
fi

"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip --quiet
"$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR" --quiet

# 4. Create Desktop Shortcut for Ubuntu App Launcher
echo "Step 4/4: Registering Desktop launcher..."
mkdir -p "$HOME/.local/share/applications"

cat <<EOF > "$DESKTOP_ENTRY"
[Desktop Entry]
Name=Sarthika Code
Comment=Private, local-first desktop AI coding assistant
Exec=$INSTALL_DIR/run.sh
Icon=$INSTALL_DIR/assets/icon.png
Terminal=false
Type=Application
Categories=Development;IDE;Utility;
StartupWMClass=SarthikaCode
EOF

chmod +x "$DESKTOP_ENTRY"
chmod +x "$INSTALL_DIR/run.sh"

# Refresh desktop database if tool is present
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo "=================================================================="
echo "✅ Installation Complete!"
echo "• Sarthika Code has been installed in: $INSTALL_DIR"
echo "• You can find 'Sarthika Code' in your Ubuntu Applications menu."
echo "• Launching application now..."
echo "=================================================================="

notify_status "Installation complete! Launching Sarthika Code..."

# Launch application
exec "$INSTALL_DIR/run.sh" "$@"
