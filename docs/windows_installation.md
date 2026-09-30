# Sarthika Code — Windows Installation & Setup Guide

**Product Version:** 0.1.0  
**Target Platform:** Windows 10 / Windows 11 (64-bit, x86_64)

This guide explains how to install and run the pre-packaged standalone Windows release of **Sarthika Code**, configure the external `llama-server` engine, and select a local GGUF model.

---

## 1. System Requirements & Assumptions

* **Operating System**: Windows 10 (64-bit, Version 1909+) or Windows 11 (64-bit).
* **Processor**: Modern x86_64 multi-core CPU supporting AVX2 instructions (Intel Core i5/i7 8th Gen+, AMD Ryzen 3000+).
* **RAM**:
  * **16 GB RAM** (Recommended for comfortable development with 4096 context window).
  * **8 GB RAM** (Supported in best-effort / low-context mode with 2048 context window).
* **Disk Space**: ~500 MB for Sarthika Code application + ~2 GB for the local 3B GGUF model.
* **Python Runtime**: **NOT required for end users.** The packaged release bundles a self-contained runtime environment.

---

## 2. Installation & Running

1. Download the release package: `SarthikaCode-0.1.0-win64.zip`.
2. Extract the archive into your preferred installation directory, for example:
   ```text
   C:\Users\<YourUsername>\AppData\Local\Programs\SarthikaCode\
   ```
   *(or `C:\SarthikaCode\`)*
3. Double-click **`SarthikaCode.exe`** to launch the assistant.
4. *(Optional)* Right-click `SarthikaCode.exe` and select **Pin to Start** or **Pin to taskbar** for easy access.

---

## 3. Configuring `llama-server` (External Engine)

For Version 0.1, Sarthika Code deliberately **does not bundle `llama-server` binaries** in the installer to respect upstream release packaging, licensing clarity, and security boundaries.

### How to download `llama-server.exe`:
1. Go to the official [llama.cpp GitHub Releases](https://github.com/ggerganov/llama.cpp/releases).
2. Download the pre-built Windows AVX2 package:
   ```text
   llama-<version>-bin-win-avx2-x64.zip
   ```
3. Extract the zip into a local directory, such as `C:\tools\llama-cpp\`.
4. Inside the extracted folder, you will find `llama-server.exe`.

---

## 4. Selecting Your Local GGUF Model

Sarthika Code v0.1 is optimized for **Qwen2.5-Coder 3B Instruct** in 4-bit quantization:

1. Download `qwen2.5-coder-3b-instruct-q4_k_m.gguf` (~1.9 GB) from a verified open-source repository (e.g. HuggingFace: `Qwen/Qwen2.5-Coder-3B-Instruct-GGUF` or `bartowski/Qwen2.5-Coder-3B-Instruct-GGUF`).
2. Save the `.gguf` file to a permanent folder, such as:
   ```text
   C:\models\qwen2.5-coder-3b-instruct-q4_k_m.gguf
   ```
3. In Sarthika Code:
   * On first launch, the **Model Setup Dialog** will appear automatically.
   * Click **Browse Executable** and select `C:\tools\llama-cpp\llama-server.exe`.
   * Click **Browse Model** and select `C:\models\qwen2.5-coder-3b-instruct-q4_k_m.gguf`.
   * Select your Context Size (`2048` for 8 GB RAM systems, `4096` for 16 GB systems).
   * Click **Start Server & Test Connection**.
   * When the status indicator displays **Model Ready**, click **Save & Apply**.

> [!TIP]
> If you do not yet have a GGUF model downloaded, you can click **Enable Mock Mode** during onboarding or in the status bar to explore the entire UI, syntax highlighter, and chat workflows offline.

---

## 5. Application Data & Storage Locations

All user conversations, settings, and diagnostic logs are stored strictly on your local disk in your Windows user profile:

* **Database & Config Directory:**
  ```text
  %LOCALAPPDATA%\sarthika_code\
  (e.g., C:\Users\<YourUsername>\AppData\Local\sarthika_code\)
  ```
* **Database File:**
  ```text
  %LOCALAPPDATA%\sarthika_code\sarthika_code.db
  ```
* **Log File:**
  ```text
  %LOCALAPPDATA%\sarthika_code\sarthika_code.log
  ```

---

## 6. How to Uninstall / Remove the Application

Sarthika Code does not install hidden background services, system drivers, or registry hooks:

1. Close the application.
2. Delete the application folder where you extracted `SarthikaCode.exe`.
3. *(Optional full data erasure)* To completely erase your chats and local settings, delete the `%LOCALAPPDATA%\sarthika_code\` directory.

---

## 7. Reporting Issues & Diagnostics

If you encounter an issue or server failure:
1. Open Sarthika Code.
2. From the menu bar, navigate to **Help -> Diagnostics & Logs**.
3. Ensure **Redact Private Paths** is checked (this replaces sensitive home paths with `~`).
4. Click **Copy Report** and paste the diagnostic report into your GitHub issue.
