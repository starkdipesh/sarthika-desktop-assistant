@echo off
REM ==============================================================================
REM Sarthika Code — One-Click Launcher (Windows)
REM ==============================================================================

cd /d "%~dp0"

IF EXIST ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "run.py" %*
) ELSE IF EXIST ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "run.py" %*
) ELSE (
    python "run.py" %*
)
