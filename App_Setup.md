# Sarthika Code — Zero-Friction Setup & Launch Guide

Sarthika Code is designed to be usable by **anyone**, including non-technical users who do not know how to use the terminal or Git.

---

## 1. Non-Technical / One-Click Launching

### On Windows
1. Simply double-click **`run.bat`** in Windows File Explorer.
2. If Python dependencies or `.venv` are missing, `run.bat` will **automatically create and configure everything for you**.
3. Sarthika Code will open directly.

### On Linux (Ubuntu / Debian / Fedora / Mint)
1. Double-click **`run.sh`** or execute it:
   ```bash
   ./run.sh
   ```
2. If `.venv` or dependencies are missing on the new computer, `run.sh` **automatically bootstraps Python, installs dependencies, and registers the desktop icon**.
3. **Application Menu Integration**:
   To make Sarthika Code appear in your Ubuntu Dash / application search menu with its official icon, run:
   ```bash
   cp sarthika-code.desktop ~/.local/share/applications/
   ```
   You can now pin **Sarthika Code** directly to your dock and start it with **one click**!

---

## 2. In-App One-Click AI Setup (No Terminal or Hugging Face Required)

When Sarthika Code opens for the first time:
1. The **Welcome & Setup Wizard** appears automatically.
2. Choose your preferred local model:
   - **Qwen 2.5 Coder 1.5B (Fast / 8 GB RAM)**: Ultra-lightweight (~986 MB).
   - **Qwen 2.5 Coder 3B (Recommended Standard)**: Balanced capability and accuracy (~1.93 GB).
3. Click **`[ 🚀 Download & Start Setup ]`**.
4. The application will:
   - Download the model with a live graphical progress bar, download speed, and ETA.
   - Automatically configure the paths and save settings.
   - Automatically launch the local inference engine.
5. The chat screen opens immediately — **ready to chat with zero manual configuration**!

---

## 3. Alternative Options
- **Offline Demo Mode**: Click `"Explore Offline Demo Mode"` on startup to test the app without downloading any model weights.
- **Manual Setup**: If you already have a `.gguf` file on your computer, click `"Select Existing File..."` to browse your disk directly.