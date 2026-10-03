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

# 1. Check & Install System Prerequisites (python3, python3-venv, python3-pip, git, curl, unzip)
echo "Step 1/4: Checking system requirements..."
MISSING_PKGS=()

for pkg in git curl unzip python3 python3-venv python3-pip; do
    if command -v dpkg &>/dev/null; then
        if ! dpkg -s "$pkg" &>/dev/null; then
            MISSING_PKGS+=("$pkg")
        fi
    elif ! command -v "$pkg" &>/dev/null; then
        MISSING_PKGS+=("$pkg")
    fi
done

# Extra check: ensure python3-venv / ensurepip module is genuinely operational
if command -v python3 &>/dev/null && ! python3 -m ensurepip --version &>/dev/null; then
    if [[ ! " ${MISSING_PKGS[*]} " =~ " python3-venv " ]]; then
        MISSING_PKGS+=("python3-venv")
    fi
fi

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo "The following system packages are required: ${MISSING_PKGS[*]}"
    echo "Installing missing packages with sudo (you may be asked for your password)..."
    if command -v sudo &>/dev/null; then
        sudo apt update -qq
        sudo apt install -y "${MISSING_PKGS[@]}"
    else
        apt update -qq
        apt install -y "${MISSING_PKGS[@]}"
    fi
fi

# 2. Setup Application Directory in hidden/system user space (~/.local/share/sarthika-code)
echo "Step 2/4: Setting up application files..."
if [ -d "$INSTALL_DIR" ]; then
    if [ -d "$INSTALL_DIR/.git" ] && git -C "$INSTALL_DIR" rev-parse --is-inside-work-tree &>/dev/null; then
        notify_status "Updating existing Sarthika Code installation..."
        cd "$INSTALL_DIR"
        git fetch origin main --quiet || true
        git reset --hard origin/main --quiet || true
        git clean -fd --quiet || true
    else
        notify_status "Cleaning up previously interrupted download..."
        rm -rf "$INSTALL_DIR"
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone --depth 1 "$REPO_URL" "$INSTALL_DIR" --quiet
        cd "$INSTALL_DIR"
    fi
else
    notify_status "Downloading Sarthika Code..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR" --quiet
    cd "$INSTALL_DIR"
fi

# 3. Create isolated virtual environment & install requirements
echo "Step 3/4: Configuring Python environment and dependencies..."
notify_status "Configuring dependencies (takes 1-2 minutes on first run)..."

# If previously terminated, broken, or incomplete, delete and start fresh
if [ ! -f "$INSTALL_DIR/.setup_complete" ] || [ ! -f "$INSTALL_DIR/.venv/bin/pip" ] || [ ! -f "$INSTALL_DIR/.venv/bin/python" ]; then
    echo "• Cleaning up any previous incomplete or terminated environment..."
    rm -rf "$INSTALL_DIR/.venv"
    rm -f "$INSTALL_DIR/.setup_complete"
    python3 -m venv "$INSTALL_DIR/.venv" || true
fi

# Fallback: if pip is still missing, attempt bootstrap with ensurepip
if [ ! -f "$INSTALL_DIR/.venv/bin/pip" ]; then
    "$INSTALL_DIR/.venv/bin/python" -m ensurepip --upgrade 2>/dev/null || true
fi

if [ ! -f "$INSTALL_DIR/.venv/bin/pip" ]; then
    echo "❌ Error: Virtual environment was created without pip."
    echo "Please install python3-venv by running:"
    echo "   sudo apt install -y python3-venv python3-pip"
    exit 1
fi

"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip --quiet
"$INSTALL_DIR/.venv/bin/pip" install --ignore-requires-python -e "$INSTALL_DIR" --quiet

# 3b. Install & Configure full local AI engine suite (llama-server and shared runtime libraries)
echo "Installing and configuring local AI engine runtime suite..."
BIN_DIR="$INSTALL_DIR/bin"
DATA_BIN_DIR="$HOME/.local/share/sarthika_code/bin"
mkdir -p "$BIN_DIR" "$DATA_BIN_DIR"

if [ ! -f "$BIN_DIR/llama-server" ] || [ ! -x "$BIN_DIR/llama-server" ] || [ ! -f "$BIN_DIR/libllama.so" ]; then
    echo "• Downloading pre-built engine runtime suite for Ubuntu..."
    LLAMA_ZIP="/tmp/llama-server-ubuntu.zip"
    LLAMA_URL="https://github.com/ggml-org/llama.cpp/releases/download/b4776/llama-b4776-bin-ubuntu-x64.zip"

    if curl -sSL --connect-timeout 15 --max-time 180 -o "$LLAMA_ZIP" "$LLAMA_URL"; then
        echo "• Extracting engine binaries and shared runtime libraries..."
        if command -v unzip &>/dev/null; then
            unzip -q -o -j "$LLAMA_ZIP" "build/bin/*" -d "$BIN_DIR" 2>/dev/null || unzip -q -o -j "$LLAMA_ZIP" "*llama*" -d "$BIN_DIR" 2>/dev/null || unzip -q -o "$LLAMA_ZIP" -d "$BIN_DIR" 2>/dev/null || true
        else
            python3 -c "
import zipfile, os, shutil
with zipfile.ZipFile('$LLAMA_ZIP') as z:
    for m in z.infolist():
        if m.is_dir():
            continue
        fname = os.path.basename(m.filename)
        if fname:
            with z.open(m) as src, open(os.path.join('$BIN_DIR', fname), 'wb') as dst:
                shutil.copyfileobj(src, dst)
" 2>/dev/null || true
        fi
        rm -f "$LLAMA_ZIP"
        if [ -f "$BIN_DIR/llama-server" ]; then
            chmod +x "$BIN_DIR"/* 2>/dev/null || true
            cp -f "$BIN_DIR"/* "$DATA_BIN_DIR"/ 2>/dev/null || true
            chmod +x "$DATA_BIN_DIR"/* 2>/dev/null || true
            echo "✅ Complete AI engine suite installed successfully in: $BIN_DIR"
        fi
    else
        echo "⚠️ Could not download pre-built engine suite automatically. It can be provided or configured in-app."
    fi
else
    echo "• Local AI engine suite is already installed."
    cp -f "$BIN_DIR"/* "$DATA_BIN_DIR"/ 2>/dev/null || true
    chmod +x "$BIN_DIR"/* "$DATA_BIN_DIR"/* 2>/dev/null || true
fi

# Mark setup as completely and successfully finished
touch "$INSTALL_DIR/.setup_complete"

# 4. Create Desktop Shortcut for Ubuntu App Launcher
echo "Step 4/4: Registering Desktop launcher and icon..."
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.local/share/icons/hicolor/256x256/apps"
mkdir -p "$HOME/.local/share/pixmaps"

# Install icon into standard system icon locations so GNOME finds it immediately
if [ -f "$INSTALL_DIR/assets/icon.png" ]; then
    cp "$INSTALL_DIR/assets/icon.png" "$HOME/.local/share/icons/hicolor/256x256/apps/sarthika-code.png"
    cp "$INSTALL_DIR/assets/icon.png" "$HOME/.local/share/pixmaps/sarthika-code.png"
    if command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
    fi
fi

# Clean up any stale or orphaned launchers pointing to incorrect paths (e.g. /var/www)
for f in "$HOME/.local/share/applications"/sarthika*.desktop "$HOME/Desktop"/sarthika*.desktop; do
    if [ -f "$f" ] && grep -q "/var/www" "$f" 2>/dev/null; then
        rm -f "$f"
    fi
done

cat <<EOF > "$DESKTOP_ENTRY"
[Desktop Entry]
Name=Sarthika Code
Comment=Private, local-first desktop AI coding assistant
Exec="$INSTALL_DIR/run.sh"
Path=$INSTALL_DIR
Icon=$HOME/.local/share/icons/hicolor/256x256/apps/sarthika-code.png
Terminal=false
Type=Application
Categories=Development;IDE;Utility;
StartupWMClass=SarthikaCode
EOF

chmod +x "$DESKTOP_ENTRY"
chmod +x "$INSTALL_DIR/run.sh"

# Also place on Desktop screen if ~/Desktop folder exists
if [ -d "$HOME/Desktop" ]; then
    cp "$DESKTOP_ENTRY" "$HOME/Desktop/sarthika-code.desktop"
    chmod +x "$HOME/Desktop/sarthika-code.desktop"
    if command -v gio &>/dev/null; then
        gio set "$HOME/Desktop/sarthika-code.desktop" metadata::trusted true 2>/dev/null || true
    fi
fi

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
