@echo off
REM ==============================================================================
REM Sarthika Code — Universal One-Click Launcher (Windows)
REM Automatically bootstraps virtual environment and installs dependencies if needed.
REM ==============================================================================

cd /d "%~dp0"

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo ==================================================================
    echo Sarthika Code — First-Time Automatic Setup
    echo ==================================================================
    echo Configuring environment on your computer... Please wait a moment.
    
    python --version >nul 2>&1
    IF ERRORLEVEL 1 (
        echo Error: Python 3 was not detected on your system.
        echo Please install Python 3.11+ from https://www.python.org or Microsoft Store.
        pause
        exit /b 1
    )

    echo * Creating local virtual environment in .venv...
    python -m venv .venv
    IF ERRORLEVEL 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )

    echo * Installing dependencies (PySide6, SQLAlchemy, httpx)...
    .venv\Scripts\pip.exe install --upgrade pip --quiet
    .venv\Scripts\pip.exe install -e . --quiet
    IF ERRORLEVEL 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
    echo * Setup completed successfully!
    echo ==================================================================
)

IF EXIST ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "run.py" %*
) ELSE (
    ".venv\Scripts\python.exe" "run.py" %*
)
