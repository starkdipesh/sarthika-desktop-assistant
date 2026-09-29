# Sarthika Code — Installation & Setup Guide

This guide details how to install Sarthika Code, configure `llama.cpp` (`llama-server`), and obtain the recommended local GGUF model.

---

## 1. System Requirements

### Minimum Requirements (Low-Memory Mode)
* **OS**: Windows 10/11 (64-bit) or modern Linux distribution (Ubuntu 22.04+, Fedora 38+, Debian 12+)
* **Processor**: x86_64 CPU supporting AVX2 instructions (most CPUs manufactured after 2014)
* **RAM**: 8 GB RAM (best-effort; context window restricted to 2048)
* **Disk Space**: ~4 GB free disk space (application files + 3B GGUF model)

### Recommended Configuration
* **OS**: Windows 11 (64-bit) or Ubuntu 24.04 LTS
* **Processor**: Modern quad-core or octa-core CPU (Intel Core i5/i7 11th Gen+, AMD Ryzen 5000+)
* **RAM**: 16 GB RAM or higher
* **Disk Space**: 10 GB+ SSD storage

---

## 2. Setting Up Python Environment (Development Setup)

Sarthika Code supports **Python 3.11** as its primary supported target (compatible with Python >= 3.11).

```bash
# Clone the repository
git clone https://github.com/your-username/sarthika-code.git
cd sarthika-code

# Create a virtual environment using Python 3.11
python3.11 -m venv .venv

# Activate the virtual environment
# On Linux / macOS:
source .venv/bin/activate
# On Windows PowerShell:
# .venv\Scripts\Activate.ps1

# Upgrade pip and install development dependencies
pip install --upgrade pip
pip install -e ".[dev]"
```

---

## 3. Obtaining `llama-server`

Sarthika Code communicates with `llama-server`, the HTTP inference engine provided by `llama.cpp`.

### Option A: Pre-built Binaries (Recommended)
1. Navigate to the official [llama.cpp GitHub Releases](https://github.com/ggerganov/llama.cpp/releases).
2. Download the latest release asset for your operating system:
   * **Windows**: `llama-<release>-bin-win-avx2-x64.zip`
   * **Linux**: `llama-<release>-bin-ubuntu-x64.tar.gz`
3. Extract the archive into a permanent folder (e.g. `C:\tools\llama-cpp\` or `~/tools/llama-cpp/`).
4. Note the path to `llama-server` (`llama-server.exe` on Windows).

### Option B: Building from Source
```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build -DLLAMA_NATIVE=ON
cmake --build build --config Release -j
# The binary will be located in build/bin/llama-server
```

---

## 4. Downloading the Recommended Model

Sarthika Code v0.1 is optimized for **Qwen2.5-Coder 3B Instruct** in 4-bit quantization (`Q4_K_M`).

* **Model Filename**: `qwen2.5-coder-3b-instruct-q4_k_m.gguf`
* **File Size**: ~1.9 GB
* **Download Source**: Download directly from trusted open-source HuggingFace model repositories (e.g. `Qwen/Qwen2.5-Coder-3B-Instruct-GGUF` or `bartowski/Qwen2.5-Coder-3B-Instruct-GGUF`).

> [!IMPORTANT]
> Save the `.gguf` file to a folder outside of this git repository (e.g. `~/models/` or `C:\models\`). Never commit model files to version control.

---

## 5. First Launch & Setup

1. Launch Sarthika Code:
   ```bash
   python -m sarthika_code.main
   ```
2. On first launch, the Welcome Screen will prompt you for:
   * **llama-server Executable Path**: Browse to your downloaded `llama-server` binary.
   * **Model File Path**: Browse to your `qwen2.5-coder-3b-instruct-q4_k_m.gguf` file.
   * **Context Size**: Choose `2048` (for 8 GB systems) or `4096` (for 16 GB systems).
3. Click **Start Server & Test Connection**.
4. Once the status badge turns green (`Model Ready`), you are ready to begin using curated workflows.
