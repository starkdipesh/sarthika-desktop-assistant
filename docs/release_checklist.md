# Sarthika Code — Release Validation Checklist

**Release Candidate Version:** 0.1.0  
**Target Platform:** Windows 10/11 (64-bit)

Before publishing or distributing any release artifact (`SarthikaCode-0.1.0-win64.zip`), the release engineer or maintainer must verify and check off every item on this list in a clean test environment.

---

### Phase 1: Artifact Integrity & Safety Verification

- [ ] **1. No Model Weights Bundled:**
  - Verify `dist/SarthikaCode` contains zero `.gguf`, `.bin`, `.safetensors`, or model weight files.
  - Command: `dir /s /b *.gguf` (must return zero results).
- [ ] **2. No Private User Data Bundled:**
  - Verify package contains zero `.sqlite`, `.sqlite3`, `.db`, `.log`, or `.env*` files.
- [ ] **3. No Bundled `llama-server` Executables:**
  - Verify package does NOT bundle `llama-server.exe` (must remain separately downloaded by user in Version 0.1).
- [ ] **4. License & Notices Included:**
  - Verify root of package includes `LICENSE` (Apache-2.0) and `README.md`.
- [ ] **5. Package Size Sanity:**
  - Uncompressed package size should be reasonable for a PySide6 GUI runtime (~150 MB – 250 MB).
  - Compressed zip archive should be under 100 MB.

---

### Phase 2: Fresh-Machine / Clean-Environment Launch

- [ ] **6. Clean Launch Without Existing Configuration:**
  - Launch `SarthikaCode.exe` on a test machine (or clean VM) where `%LOCALAPPDATA%\sarthika_code` does not exist.
  - Verify application starts without crashes or missing DLL warnings.
  - Verify the **Welcome / Onboarding Dialog** appears cleanly.
- [ ] **7. No Model Configured State:**
  - Verify status badge displays `NO MODEL` (or `STOPPED`) with appropriate guidance.
  - Verify user is not blocked from exploring the UI or menus.
- [ ] **8. Application Metadata & Icon:**
  - Verify application window taskbar icon shows the official Sarthika Code icon (`icon.ico`).
  - In Windows Task Manager and File Properties, verify:
    - Product Name: `Sarthika Code`
    - Version: `0.1.0.0`
    - Publisher: `Sarthika Code Contributors`

---

### Phase 3: Offline Mock Mode & Workflow Verification

- [ ] **9. One-Click Mock Mode Enablement:**
  - Click **Mock Mode** toggle in the status bar or header.
  - Verify status updates to `Offline Mock Mode`.
- [ ] **10. Conversational Turns in Mock Mode:**
  - Send message: `"Write a Python binary search function"`.
  - Verify tokens stream smoothly into the chat pane without UI freezing.
  - Verify syntax highlighter correctly colors code blocks.
- [ ] **11. Workflow Selection:**
  - Switch between workflows (`Explain Code`, `Refactor Code`, `Write Unit Tests`, `Debug & Fix`).
  - Verify system prompts and badges update accordingly.
- [ ] **12. Generation Cancellation:**
  - Send a prompt and immediately click **Stop / Cancel**.
  - Verify stream halts immediately and message status records `[Generation stopped by user]`.

---

### Phase 4: Model Setup & Persistence

- [ ] **13. Model Setup Validation:**
  - Open **Settings -> Model Setup**.
  - Test selecting a non-.gguf file (verify it is rejected with clear error).
  - Test selecting a valid `llama-server.exe` and `qwen2.5-coder-3b-instruct-q4_k_m.gguf`.
  - Verify connection test and health check indicator.
- [ ] **14. Settings Persistence:**
  - Save settings, close `SarthikaCode.exe`, and relaunch.
  - Verify configured paths and generation settings (temperature, top-p, context size) remain saved in SQLite.
- [ ] **15. Project Context Security Filter:**
  - Attempt attaching a `.env` file or `.key` file.
  - Verify the security scanner blocks attachment with `SensitiveFileError`.
  - Attach a valid `.py` file and verify token budget calculation.

---

### Phase 5: Clean Exit & Log Verification

- [ ] **16. Safe Logging:**
  - Open `%LOCALAPPDATA%\sarthika_code\sarthika_code.log`.
  - Verify logs do not contain raw passwords, API keys, or unredacted user home paths.
- [ ] **17. Clean Termination:**
  - Close the main window.
  - Check Windows Task Manager to verify `SarthikaCode.exe` exits cleanly.
  - Verify any child `llama-server.exe` subprocess is terminated without leaving orphan background processes.
