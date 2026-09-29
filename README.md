# Sarthika Code

> **A private, local AI coding assistant that runs entirely on your computer.**

[![CI](https://github.com/your-username/sarthika-code/actions/workflows/tests.yml/badge.svg)](https://github.com/your-username/sarthika-code/actions/workflows/tests.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

---

## 1. Product Mission & Philosophy

Sarthika Code is a **local-first desktop AI coding assistant** designed for software developers who value absolute source-code privacy and want AI-assisted development without recurring costs, accounts, or telemetry.

* **100% Local-First**: No cloud inference, no remote servers, no telemetry, no tracking, and no external AI APIs.
* **CPU-Friendly**: Optimized to run on ordinary laptops without requiring expensive dedicated GPUs.
* **Safe & Non-Destructive**: Never executes shell commands, never writes to your project files, and never makes unauthorized Git operations.
* **Honest Product Reality**: Sarthika Code is not AGI and not an autonomous engineer. It is an assistive desktop tool designed to generate reviewable suggestions that you verify and test.

---

## 2. Core Features (Version 0.1)

* **Local GGUF Inference**: Connects directly to a locally managed `llama-server` process using `llama.cpp`.
* **Standard Model Support**: Optimized for the **Qwen2.5-Coder 3B Instruct** model (`Q4_K_M` quantization).
* **Curated Workflows**: Specialized task flows for *Explain Code*, *Debug Code*, *Refactor Code*, *Generate Unit Tests*, *Laravel Component Draft*, *Python Component Draft*, and *Implementation Planning*.
* **Dedicated Code Editor**: Multiline code workspace with language syntax awareness and context metrics.
* **Explicit Read-Only Context**: Attach source code files with full user visibility. Automatic screening blocks sensitive files (`.env`, `credentials.json`, `id_rsa`, `node_modules`).
* **Persistent Local Conversations**: Local SQLite conversation storage with instant search, rename, delete, and Markdown/JSON export.
* **Offline Mock / Demo Mode**: Built-in mock provider for testing the UI, streaming, and workflows without requiring model weights.
* **System Diagnostics**: Real-time monitoring of CPU, RAM, server status, process uptime, and token generation speed.

---

## 3. What Sarthika Code Is NOT (Non-Features)

To preserve security, stability, and privacy, Version 0.1 explicitly excludes:
* Cloud AI API integrations (OpenAI, Anthropic, Gemini, Groq)
* Autonomous agentic loops and unconstrained replanning
* Background web browsing or external documentation fetching
* Vector databases, embeddings, and automatic repository RAG
* Terminal execution, shell commands, or automated package installations
* Automated file rewriting or code patching
* Automated Git operations (commit, push, branch)
* User accounts, logins, telemetry, or analytics beacons

---

## 4. Hardware Guidance

| Configuration | Support Tier | Default Context | Expected Speed | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **8 GB RAM (No GPU)** | **Best-Effort** | **2048 tokens** | 5–10 tokens/s | Low-memory mode. Close browser and heavy apps during inference. |
| **16 GB RAM (No GPU)**| **Recommended** | **4096 tokens** | 8–15 tokens/s | Comfortable experience for standard development tasks. |
| **32 GB+ RAM / GPU**  | **Optimal** | **8192+ tokens** | 15–30+ tokens/s | Extended context support with high-performance prompt evaluation. |

---

## 5. Quickstart & Installation

See [docs/installation.md](docs/installation.md) for full operating system instructions.

### 1. Prerequisites
* Python 3.11+ (Primary supported version: 3.11)
* Pre-compiled `llama-server` binary from [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases)
* Quantized GGUF model: `qwen2.5-coder-3b-instruct-q4_k_m.gguf` (~1.9 GB)

### 2. Development Setup
```bash
# Clone the repository
git clone https://github.com/your-username/sarthika-code.git
cd sarthika-code

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install package in editable mode with development dependencies
pip install --upgrade pip
pip install -e ".[dev]"
```

### 3. Launching Application
```bash
python -m sarthika_code.main
```

---

## 6. Architecture & Documentation

Comprehensive architectural and user documentation is available in the `docs/` directory:

* [System Architecture Specification](docs/architecture.md)
* [Product Roadmap & Milestones](docs/roadmap.md)
* [Privacy Policy & Guarantee](docs/privacy.md)
* [Product Realities & Limitations](docs/limitations.md)
* [Installation Guide](docs/installation.md)
* [Troubleshooting & Diagnostics](docs/troubleshooting.md)
* [Benchmarking Methodology & 50-Task Dataset](docs/benchmarks.md)

---

## 7. Testing & Code Quality

```bash
# Run linter checks
ruff check src tests

# Run type checker
mypy src

# Run unit and integration tests
pytest -v
```

---

## 8. Licenses & Disclaimers

* **Application Code**: Licensed under the [Apache License 2.0](LICENSE).
* **llama.cpp**: Licensed under the MIT License by Georgi Gerganov and contributors.
* **Model Weights**: Qwen2.5-Coder weights are licensed by the Qwen team under the Apache 2.0 License. Model weights are never bundled with this repository.
* **Disclaimer**: Generated code may contain inaccuracies, syntax errors, or security flaws. Always inspect and test generated code prior to production use.