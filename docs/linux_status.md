# Sarthika Code — Linux Platform Status & Developer Guide

**Product Version:** 0.1.0  
**Current Status:** Pre-packaged Linux release (AppImage / Flatpak / .deb) is **PLANNED (Not Yet Packaged)**.

---

## 1. Platform Support Disclosure

Sarthika Code adopts strict truth-in-packaging:
* **Packaged Releases:** Version 0.1 focuses exclusively on a **Windows-first standalone package**. No pre-packaged Linux desktop binary (`.AppImage`, `.deb`, or Flatpak) is currently provided or claimed as an official release artifact.
* **Developer Mode:** Linux is fully supported for developers running from source via a virtual environment with Python 3.11+.

---

## 2. Developer Setup on Linux (Running From Source)

To run Sarthika Code on Linux (Ubuntu 22.04+, Fedora 38+, Debian 12+, Arch Linux):

### A. Install System Dependencies
PySide6 requires standard system graphics, font, and X11/Wayland libraries:

```bash
# On Debian / Ubuntu:
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    python3-venv \
    libgl1 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libfontconfig1 \
    libegl1 \
    libxcb-cursor0
```

### B. Set Up Python 3.11 Environment
```bash
# Clone the repository
git clone https://github.com/your-username/sarthika-code.git
cd sarthika-code

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install package in editable development mode
pip install --upgrade pip
pip install -e ".[dev]"
```

### C. Run the Application
```bash
# Launch GUI
python run.py

# Or launch module directly
python -m sarthika_code.main
```

---

## 3. Obtaining `llama-server` on Linux

Download the official Linux x86_64 binary from [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases):
```bash
mkdir -p ~/tools/llama-cpp
cd ~/tools/llama-cpp
# Extract official release archive
tar -xzf llama-<release>-bin-ubuntu-x64.tar.gz
chmod +x llama-server
```

In Sarthika Code, set the executable path to `~/tools/llama-cpp/llama-server`.

---

## 4. Linux Application Data Storage

On Linux, user application data adheres strictly to the XDG Base Directory specification:
* **Configuration & Database:** `~/.local/share/sarthika_code/` or `~/.config/sarthika_code/`
* **Log Files:** `~/.local/state/sarthika_code/sarthika_code.log`
