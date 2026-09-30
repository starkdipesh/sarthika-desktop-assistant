# Contributing to Sarthika Code

Thank you for your interest in contributing to Sarthika Code! Sarthika Code is a private, local-first desktop AI coding assistant built on Python, PySide6, and `llama.cpp`.

Please review this document before submitting issues, feature requests, or pull requests.

---

## 1. Core Principles & Non-Negotiables

Every contribution must honor our foundational architectural constraints:

1. **Local-First & Offline**: Sarthika Code operates 100% locally. Contributions that add telemetry, analytics beacons, remote AI APIs (e.g. OpenAI, Anthropic, Gemini), or remote cloud sync will not be accepted.
2. **CPU-Friendly Target**: The application targets standard laptops and desktops without dedicated GPUs. Memory usage, thread allocation, and context limits must remain respectful of 8 GB and 16 GB RAM configurations.
3. **Safety & Zero Auto-Execution**: Sarthika Code is an assistive drafting tool. It must **never** automatically execute model output, shell scripts, command prompts, background daemons, or silent write/patch operations against the user's project files.
4. **Architectural Separation**: Keep the PySide6 UI cleanly separated from application services, repositories, and domain models. Never place substantial business logic or network/subprocess calls inside UI widgets or button event handlers.
5. **No Model Bundling**: Never commit `.gguf`, `.bin`, `.safetensors`, `.sqlite`, `.db`, `.log`, or `.env` files to Git.

---

## 2. Development Environment Setup

### Prerequisites
* **Python 3.11+** (Python 3.11 is the primary supported release).
* **Git**.
* Optional: A local compiled `llama-server` binary and a quantized GGUF model (e.g. Qwen 2.5 Coder 3B) for manual end-to-end verification.

### Setup Instructions
```bash
# 1. Clone the repository
git clone https://github.com/your-username/sarthika-code.git
cd sarthika-code

# 2. Create a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1

# 3. Install in editable mode with development dependencies
pip install --upgrade pip
pip install -e ".[dev]"
```

---

## 3. Running Verification & Tests

Before opening a pull request, all automated checks must pass cleanly.

```bash
# 1. Lint and style checks
ruff check src tests scripts

# 2. Static type checks
mypy src

# 3. Unit and integration test suite
pytest -v

# 4. Local test coverage check
pytest --cov=sarthika_code --cov-report=term-missing tests/
```

*Note: Tests must not require an actual GGUF model file, actual `llama-server` binary, or network access. Use `MockLLMProvider` or mocked HTTP transport for test cases.*

---

## 4. Architectural Guidelines

* **UI Layer (`src/sarthika_code/ui/`)**: Responsible solely for presentation, widget layout, user interactions, and emitting Qt signals. Connects to Application Services.
* **Services Layer (`src/sarthika_code/services/`)**: Orchestrates business rules, coordinates chat sessions, context scanning, settings management, and diagnostics.
* **LLM Layer (`src/sarthika_code/llm/`)**: Manages `llama-server` subprocess lifecycles, streaming HTTP communication via `httpx`, and the `MockLLMProvider`.
* **Storage Layer (`src/sarthika_code/storage/`)**: Local SQLite persistence via SQLAlchemy 2.x repositories with WAL mode.
* **Prompts & Security (`src/sarthika_code/prompts/`, `src/sarthika_code/security/`)**: Workflow system prompts, context token budgeting, and sensitive/binary file filters.

---

## 5. Submitting Pull Requests

1. **Branch Naming**: Use descriptive branch names: `feature/short-description`, `fix/issue-description`, or `docs/update-description`.
2. **Commit Messages**: Write concise, imperative commit messages (e.g., `feat: add token count warning in context panel`).
3. **Fill Out PR Template**: Complete all sections in [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md).
4. **Preserve Privacy & Zero Telemetry**: Double check that no external URLs or tracking calls were added.
5. **Add Tests**: Include unit tests for every new feature or bug fix.

---

## 6. Questions & Discussions

Open an issue on GitHub to discuss planned changes or architectural proposals before undertaking large refactors.
