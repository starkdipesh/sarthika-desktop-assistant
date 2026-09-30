# Sarthika Code

> **Private, local-first desktop AI coding assistant**

[![CI](https://github.com/your-username/sarthika-code/actions/workflows/tests.yml/badge.svg)](https://github.com/your-username/sarthika-code/actions/workflows/tests.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20(source)-lightgrey.svg)](docs/installation.md)
[![Privacy](https://img.shields.io/badge/privacy-100%25%20local-success.svg)](docs/privacy.md)

---

## 1. Mission Statement & Philosophy

**Sarthika Code** is a **private, local-first desktop AI coding assistant** engineered for software engineers, teams, and enterprises that require absolute source-code privacy. It runs user-selected quantized GGUF models directly on your local hardware via an embedded or user-supplied `llama-server` process.

* **Designed to run without a GPU**: Fully optimized for ordinary multi-core laptop and desktop CPUs.
* **No API key required for local inference**: Operates completely offline without external subscriptions, API tokens, credit cards, or accounts.
* **Zero Telemetry & Cloud Autonomy**: No telemetry, analytics beacons, external AI APIs, or remote telemetry servers exist in the codebase.
* **Safe & Non-Destructive**: Never executes generated code, shell commands, background daemons, or unauthorized write operations against your files or repositories.
* **Product Honesty**: Sarthika Code makes no claims of AGI, human-level intelligence, full developer autonomy, or bug-free code generation. It is a focused desktop tool that generates reviewable suggestions for developers who inspect and verify all code before use.

---

## 2. Core Features (Version 0.1)

* **Local GGUF Model Inference**: Connects directly to a locally managed `llama-server` process using high-performance C/C++ `llama.cpp` inference.
* **CPU-First Architecture**: Built-in threading profiles and context budgets tailored for modern 4-core, 6-core, and 8-core CPUs.
* **Task-Specific Workflows**:
  * **Explain Code**: High-level and line-by-line architectural explanations.
  * **Bug Analysis**: Root-cause analysis and reproduction steps for stack traces and logical errors.
  * **Refactor Code**: Clean code refactoring targeting readability, maintainability, and SOLID principles.
  * **Test Generation**: Comprehensive unit and integration test generation.
  * **Docstring & Type Annotations**: Clear docstrings and strict static type hints.
  * **Laravel Component Draft**: Standard Laravel controllers, models, migrations, and FormRequests.
  * **Python Component Draft**: Idiomatic Python classes, dataclasses, and functions.
  * **Implementation Planning**: Step-by-step technical execution plans before writing code.
* **Read-Only Context Management**: Attach explicit project files into conversation context with token counting and budget alerts.
* **Sensitive File & Binary Filtering**: Automatically blocks `.env`, SSH keys (`id_rsa`), certificates (`.pem`, `.key`), credentials (`credentials.json`), large files (>1 MB), and compiled binaries.
* **Dedicated Multiline Editor**: Built-in editor for drafting and formatting prompts and code snippets.
* **Persistent Local Conversations**: Local SQLite database storing chats and messages with instant search, rename, export (Markdown & JSON), and deletion.
* **Built-in Mock Provider**: Instant offline simulation mode for testing the UI, streaming, workflows, and failure recovery without loading a model.
* **Hardware & Process Diagnostics**: Real-time monitoring of CPU usage, RAM consumption, server process uptime, port status, and generation token rates.

---

## 3. Explicit Non-Features (What Sarthika Code Does NOT Do)

To ensure predictable security, zero remote data leakage, and system stability, Version 0.1 strictly excludes:

* ❌ **No Cloud AI APIs**: Never contacts OpenAI, Anthropic, Google, Groq, or any remote AI cloud endpoint.
* ❌ **No Autonomous Agent Loops**: Does not execute unconstrained autonomous task loops or autonomous tool calling.
* ❌ **No Terminal Execution**: Never executes shell scripts, command prompts, PowerShell commands, or terminal commands.
* ❌ **No Automated Code Modification**: Never silently edits, rewrites, patches, or overwrites files on your disk.
* ❌ **No Git Integration**: Never commits, stages, pushes, pulls, or branches Git repositories automatically.
* ❌ **No Web Browsing or Scraping**: Does not fetch web pages, search Google, or download live documentation.
* ❌ **No Vector Databases or Background Indexing**: Does not index your drive or build hidden vector embeddings.
* ❌ **No Accounts, Logins, or Subscriptions**: No sign-ups, no licensing servers, and no payment gateways.
* ❌ **No Telemetry or Tracking**: No usage statistics, error beacons, IP logging, or third-party SDKs.

---

## 4. Hardware Requirements

Sarthika Code is designed to run efficiently on standard consumer and workstation CPUs without a discrete GPU.

| Specification | Minimum Tier (Best-Effort) | Recommended Tier (Standard) | Optimal Tier (Workstation) |
| :--- | :--- | :--- | :--- |
| **Operating System** | Windows 10/11 (64-bit), Linux | Windows 10/11 (64-bit) | Windows 11 / Linux (64-bit) |
| **Processor** | 4-core modern CPU (x86_64) | 6-core / 8-core CPU (Intel i5/i7, AMD Ryzen 5/7) | 8+ cores (Ryzen 7/9, Intel i7/i9) |
| **Memory (RAM)** | **8 GB RAM** (Low-context mode) | **16 GB RAM** | **32 GB+ RAM** |
| **Default Context** | **2,048 tokens** | **4,096 tokens** | **8,192+ tokens** |
| **Expected Speed** | 4–8 tokens/second | 8–15 tokens/second | 15–30+ tokens/second |
| **Storage** | 5 GB free SSD space | 10 GB free SSD space | 20 GB+ free NVMe SSD space |
| **GPU Requirement** | **None** (CPU inference default) | **None** (CPU inference default) | Optional Vulkan/CUDA offload |

> **8 GB RAM Notice**: On 8 GB systems, close background browsers and resource-intensive applications during generation. Select a 1.5B or 3B model (such as `Qwen2.5-Coder-1.5B` or `3B` at `Q4_K_M`) and limit context to 2,048 tokens.

---

## 5. Privacy & Data Lifecycle Guarantee

* **100% Local Processing**: All token generation, prompt evaluation, and context formatting occur entirely inside the local `llama-server` process on `127.0.0.1`.
* **Zero Remote Network Calls**: Sarthika Code initiates zero outbound HTTP/HTTPS connections to remote hosts.
* **Local Storage Directory**:
  * **Windows**: `%LOCALAPPDATA%\SarthikaCode\`
  * **Linux**: `~/.local/share/sarthika-code/`
* **Artifacts on Disk**:
  * Database: `sarthika.db` (SQLite repository with WAL mode enabled).
  * Configuration: `settings.json` (model path, server port, context budget).
  * Logs: `logs/sarthika.log` (local rolling logs; sensitive file contents and prompt bodies are strictly redacted).
* **Data Deletion**: Deleting a conversation in the UI permanently removes it from the local database. Uninstalling the app and removing the data directory leaves zero traces behind.

---

## 6. Security Boundaries

Sarthika Code enforces strict read-only boundaries:

1. **Read-Only Context**: Files attached to conversations are read strictly into memory for prompt construction and never modified.
2. **Sensitive File Denylist**: Automatically ignores and blocks:
   * Secrets & environment files (`.env`, `.env.*`, `secrets.json`)
   * Private keys and certificates (`id_rsa`, `id_ed25519`, `*.pem`, `*.key`, `*.pfx`)
   * Credentials (`credentials.json`, `token.json`, `auth.json`)
   * Dependency directories (`node_modules/`, `vendor/`, `.git/`, `.venv/`)
3. **Binary File Prevention**: Inspects null bytes and encoding headers to prevent loading binary executables or compiled artifacts.
4. **File Size Hard Limits**: Individual file context is capped at 1 MB (configurable downwards) to prevent memory exhaustion.
5. **No Shell Execution**: The application has no privileges or subroutines to run commands, spawn background shells, or modify system files.

---

## 7. Installation Instructions

### Option A: Windows Installer (Recommended for Windows)
1. Download `SarthikaCode-Setup-0.1.0.exe` from the [GitHub Releases](https://github.com/your-username/sarthika-code/releases) page.
2. Run the installer and choose your installation directory (default: `%LOCALAPPDATA%\Programs\SarthikaCode`).
3. Launch **Sarthika Code** from the Start Menu or Desktop shortcut.

### Option B: Windows Standalone Portable Archive
1. Download `SarthikaCode-0.1.0-win64.zip` from [Releases](https://github.com/your-username/sarthika-code/releases).
2. Extract the archive to any folder on your computer.
3. Run `sarthika-code.exe`.

### Option C: Linux / Windows From Source
```bash
# 1. Clone repository
git clone https://github.com/your-username/sarthika-code.git
cd sarthika-code

# 2. Set up Python 3.11 virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# 3. Upgrade pip and install package
pip install --upgrade pip
pip install -e .

# 4. Launch Sarthika Code
python -m sarthika_code.main
```

*(Note: Linux standalone `.AppImage` and `.deb` packages are planned for v0.2. On Linux, running from source is currently supported.)*

---

## 8. Model Setup Instructions

Sarthika Code requires a quantized model in the **GGUF format** compatible with `llama.cpp`.

### Recommended Models for CPU Inference

| Model Name | Parameters | Quantization | Size on Disk | Min RAM | Best Suited For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen 2.5 Coder 3B Instruct** | 3.09B | `Q4_K_M` | ~1.9 GB | 8 GB | **Recommended default**: Fast, high accuracy, low RAM |
| **Qwen 2.5 Coder 1.5B Instruct** | 1.54B | `Q4_K_M` | ~1.0 GB | 8 GB | Low-spec laptops, background operation |
| **Qwen 2.5 Coder 7B Instruct** | 7.61B | `Q4_K_M` | ~4.7 GB | 16 GB | Deep refactoring, complex logic, comprehensive test suites |
| **DeepSeek Coder 1.3B Instruct** | 1.3B | `Q4_K_M` | ~0.9 GB | 8 GB | Ultra-fast completion on older hardware |
| **DeepSeek Coder 6.7B Instruct** | 6.7B | `Q4_K_M` | ~4.1 GB | 16 GB | Python and web stack architectural questions |
| **Llama 3.2 3B Instruct** | 3.21B | `Q4_K_M` | ~2.0 GB | 8 GB | General explanation and planning workflows |

### Where to Download Models
Download verified community GGUF weights directly from Hugging Face:
* [Qwen/Qwen2.5-Coder-3B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF)
* [Qwen/Qwen2.5-Coder-7B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF)
* [bartowski/Qwen2.5-Coder-3B-Instruct-GGUF](https://huggingface.co/bartowski/Qwen2.5-Coder-3B-Instruct-GGUF)

Store your downloaded `.gguf` files in a dedicated local directory (e.g., `C:\AI\models\` or `~/models/`).

---

## 9. llama-server Setup Instructions

Sarthika Code interacts with models via `llama-server` from the `llama.cpp` project.

1. **Obtain `llama-server`**:
   * **Windows**: Download the latest release from [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases) (e.g., `llama-bXXXX-bin-win-avx2-x64.zip` or `win-vulkan-x64.zip`). Extract `llama-server.exe`.
   * **Linux**: Download `llama-bXXXX-bin-ubuntu-x64.zip` or build from source using `cmake -B build && cmake --build build --config Release -t llama-server`.
2. **Configure in Sarthika Code**:
   * Open Sarthika Code.
   * Go to **Settings** (`Ctrl+,` or click the gear icon).
   * Set **llama-server Executable Path** to your `llama-server` / `llama-server.exe`.
   * Set **Model Path** to your downloaded `.gguf` file.
   * Configure port (default: `8080`), CPU threads (default: auto / physical cores), and context size (default: `4096`).
   * Click **Save Settings**. The application automatically initializes and manages the server lifecycle.

---

## 10. First-Launch Walkthrough

1. **First Launch**: When Sarthika Code starts for the first time, you are welcomed with the Onboarding Dialog.
2. **Select Mode**:
   * Choose **"Configure Local GGUF Model"** if you have a model ready.
   * Choose **"Explore in Mock Mode"** if you want to immediately test the UI and workflows without waiting for downloads.
3. **Start Chatting**:
   * Type your query in the prompt box and press `Enter` or click **Send**.
   * Use the **Workflows dropdown** above the input bar to pre-populate task-specific system guidelines.
   * Use the **Attach Context** button (`Ctrl+O`) to include relevant source files.
   * Streamed responses appear in real time with syntax highlighting and copy buttons.

---

## 11. Mock Mode (Zero-Model Testing)

To test Sarthika Code without downloading model weights or `llama-server`:

1. Open **Settings** (`Ctrl+,`).
2. Toggle the **Provider** setting from `llama.cpp Server` to `Mock Provider`.
3. Save settings.
4. You can now immediately send messages, attach files, test workflows, verify streaming cancellation, and inspect SQLite persistence with zero CPU overhead and zero downloads.

---

## 12. Local Benchmark Tooling & Methodology

Sarthika Code includes a standalone, zero-telemetry local benchmark tool to measure your hardware performance across 50 realistic coding tasks.

### Running Benchmarks
```bash
# Run the 50-task benchmark against your local llama-server
python scripts/benchmark_local.py --url http://127.0.0.1:8080 --model "Qwen2.5-Coder-3B"

# Run a quick 5-task benchmark in mock mode (useful for testing)
python scripts/benchmark_local.py --mock --limit 5
```

### Metrics Recorded
* **Time to First Token (TTFT)**: Latency in seconds before generation starts.
* **Tokens Per Second (TPS)**: Pure generation speed.
* **Hardware Profile**: OS, CPU architecture, core count, total RAM, and timestamp.
* **Output Destination**: Stored strictly locally in `benchmarks/benchmark_YYYYMMDD_HHMMSS.json`. Never transmitted remotely.

Detailed benchmark methodology is documented in [docs/benchmarks.md](docs/benchmarks.md).

---

## 13. Development & Testing

### Development Setup
```bash
# Install development dependencies
pip install -e ".[dev]"
```

### Running Test Suite
```bash
# Run full test suite (217+ unit and integration tests)
pytest -v

# Run with coverage report
pytest --cov=sarthika_code --cov-report=term-missing tests/

# Run code style and lint check
ruff check src tests scripts

# Run static type checking
mypy src
```

### Building Windows Release Binaries
On a Windows machine with Python 3.11:
```powershell
python scripts/build_release.py
```
Outputs portable directory and setup installer in `dist/`. Full instructions in [docs/windows_installation.md](docs/windows_installation.md).

---

## 14. Project Roadmap

* **Version 0.1 (Current)**: Local GGUF chat, 8 core workflows, read-only context attachment, sensitive-file filtering, SQLite persistence, mock provider, system diagnostics, Windows installer.
* **Version 0.2 (Planned)**: Linux standalone packaging (`.AppImage`, `.deb`), macOS Apple Silicon build, side-by-side code diff visualizer, prompt template customization.
* **Version 0.3 (Future)**: Fully local vector embedding indexer for multi-file workspace semantic search, multi-model side-by-side evaluation.

Read full details in [docs/roadmap.md](docs/roadmap.md).

---

## 15. Credits & Acknowledgments

Sarthika Code builds upon exceptional open-source foundations:
* **[llama.cpp](https://github.com/ggerganov/llama.cpp)**: Fast, memory-efficient LLM inference in C/C++ by Georgi Gerganov and the open-source community.
* **[PySide6](https://wiki.qt.io/Qt_for_Python)**: Official Python Qt bindings by The Qt Company.
* **[SQLAlchemy](https://www.sqlalchemy.org/)**: Robust SQL toolkit and Object Relational Mapper.
* **[httpx](https://www.python-httpx.org/)**: Next-generation HTTP client for Python.
* **[Ruff](https://astral.sh/ruff)**: Extremely fast Python linter by Astral.

---

## 16. Licenses & Community

* **Software License**: Licensed under the [Apache License 2.0](LICENSE).
* **Model Licenses**: Model weights carry their own distinct licenses (e.g., Apache 2.0 for Qwen, DeepSeek License for DeepSeek). See [MODEL_LICENSE_DISCLAIMER.md](MODEL_LICENSE_DISCLAIMER.md).
* **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for pull request guidelines and development standards.
* **Code of Conduct**: See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
* **Security Policy**: See [SECURITY.md](SECURITY.md) for responsible disclosure.

---

## 17. Mandatory Disclaimers

> **IMPORTANT NOTICE**:
> 1. Sarthika Code is experimental assistive software. It is **not** an artificial general intelligence (AGI) and does not possess human reasoning or autonomous decision-making capabilities.
> 2. Large language models frequently make errors, hallucinate non-existent APIs, introduce subtle logic bugs, or output insecure patterns.
> 3. **Always review, inspect, and test all generated code** before compiling, deploying, or incorporating it into production software systems.