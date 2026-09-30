# Release Validation Checklist — Sarthika Code v0.1

**Target Release:** Version 0.1.0  
**Target Platform:** Windows 10/11 (64-bit) (Linux source release)

This checklist must be executed before creating a final release tag or publishing release assets (`.exe` or `.zip`).

---

## 1. Code Quality & Pre-Build Gates

- [ ] All tests pass locally and in CI:
  ```bash
  pytest -v
  ```
- [ ] Code formatting and linter pass with zero errors:
  ```bash
  ruff check src tests scripts
  ```
- [ ] Static type check completes cleanly:
  ```bash
  mypy src
  ```
- [ ] Zero `.gguf`, `.bin`, `.safetensors`, `.sqlite`, or `.env` files are tracked in Git:
  ```bash
  git status --ignored
  ```

---

## 2. Release Artifact Integrity

- [ ] Run release packaging build:
  ```powershell
  python scripts/build_release.py
  ```
- [ ] Verify `dist/SarthikaCode` does **NOT** contain:
  - Model weight files (`*.gguf`)
  - Server executable (`llama-server.exe`) unless explicitly designated
  - Private user databases (`*.db`, `*.sqlite`)
  - Log files or test artifacts
- [ ] Verify `dist/SarthikaCode` contains:
  - `SarthikaCode.exe`
  - `LICENSE` (Apache-2.0)
  - `README.md`
  - `docs/` folder
  - Icon metadata and valid version resource (`0.1.0.0`)

---

## 3. Fresh Environment / Clean VM Testing

- [ ] Test on a clean Windows machine without existing Python or virtual environment:
  - Extract `SarthikaCode-0.1.0-win64.zip`
  - Launch `SarthikaCode.exe`
  - Confirm Onboarding Dialog appears smoothly
  - Verify Taskbar icon and process name in Windows Task Manager
- [ ] Test Mock Mode:
  - Switch to Mock Mode
  - Submit prompts in multiple workflows
  - Verify streaming, syntax highlighting, and cancel button
- [ ] Test Local Model Configuration:
  - Configure path to user-downloaded `llama-server.exe` and `Qwen2.5-Coder-3B-Instruct.gguf`
  - Start server and submit a prompt
  - Verify real token streaming and generation metrics
- [ ] Test Context & Security Filters:
  - Attempt attaching `.env` and `id_rsa` -> confirm blocked
  - Attach valid code file -> confirm context preview and token counting
- [ ] Test Persistence & Clean Exit:
  - Close app and reopen -> confirm chat history and settings are preserved
  - Check Task Manager -> confirm no orphan `llama-server.exe` background processes remain

---

## 4. Release Asset Checklist

- [ ] `SarthikaCode-Setup-0.1.0.exe` (Inno Setup Installer)
- [ ] `SarthikaCode-0.1.0-win64.zip` (Portable Archive)
- [ ] Release Notes detailing features, non-features, and disclaimers
- [ ] SHA-256 checksums file (`SHA256SUMS.txt`)
