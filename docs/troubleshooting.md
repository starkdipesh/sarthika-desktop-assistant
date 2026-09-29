# Sarthika Code — Diagnostics & Troubleshooting Guide

This guide helps resolve common setup, process, and inference issues encountered while running Sarthika Code.

---

## 1. Common Server State Issues

### State: `START_FAILED`
* **Symptoms**: You click "Start Server" and the status switches to `STARTING`, then immediately to `START_FAILED`.
* **Possible Causes & Remedies**:
  1. **Invalid Executable Path**: Ensure the configured path points directly to `llama-server` (or `llama-server.exe` on Windows), not `llama-cli` or `main`.
  2. **Missing Execute Permissions (Linux)**: Run `chmod +x /path/to/llama-server`.
  3. **Missing C++ Runtime Libraries (Windows)**: Install the Microsoft Visual C++ Redistributable (x64) from Microsoft's official download site.
  4. **Corrupt GGUF Model**: Verify that the GGUF file downloaded completely and is not a corrupted download (file size should be ~1.9 GB for Qwen2.5-Coder 3B Q4_K_M).

### State: `CRASHED`
* **Symptoms**: The server runs briefly or crashes in the middle of token generation.
* **Possible Causes & Remedies**:
  1. **Out of Memory (OOM)**: The system ran out of RAM while allocating the context KV-cache. Reduce context size from 4096 to 2048 in Settings.
  2. **Incompatible CPU Instructions**: If running on an older CPU without AVX2 support, ensure you downloaded a non-AVX2 (or basic AVX) build of llama.cpp.
  3. **High Concurrency / Thread Count**: Setting thread count higher than physical CPU cores can cause contention. In Settings, reduce threads to `physical_cores - 1`.

### State: `UNAVAILABLE`
* **Symptoms**: The application reports that the local model server is unreachable.
* **Possible Causes & Remedies**:
  1. **Local Port Conflict**: Another local service is using port 8080. Sarthika Code automatically scans ports 8080–8099, but you can also configure a custom port in Settings.
  2. **Firewall / Antivirus Interference**: Local host firewalls (Windows Defender, UFW) occasionally block loopback socket creation. Verify that `127.0.0.1` traffic is permitted.

---

## 2. Diagnostics Screen & Logs

If problems persist, open the **Diagnostics** screen (`Ctrl+D` or click the status badge):
1. **View Server Status**: Inspect the current PID, active port, context size, and exact command arguments.
2. **Examine Application Logs**:
   * **Linux**: `~/.local/state/sarthika_code/logs/sarthika.log`
   * **Windows**: `%LOCALAPPDATA%\sarthika_code\logs\sarthika.log`
3. **Copy Diagnostics**: Click `[Copy Diagnostics]` to obtain a redacted summary suitable for issue reporting. Note: Sarthika Code automatically redacts personal usernames and file paths from the diagnostics output.

---

## 3. Offline Mock / Demo Mode

If you need to test the UI, check workflows, or verify conversation persistence without running a local model, enable **Offline Mock Mode** in the Welcome Screen or Settings:
* Generates realistic simulated token streams.
* Does not spawn `llama-server` or allocate system RAM for GGUF weights.
* Allows developers to verify UI stability independently from inference hardware.
