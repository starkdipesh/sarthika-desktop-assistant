@echo off
REM ==============================================================================
REM Sarthika Code — Universal One-Click Launcher (Windows)
REM Automatically bootstraps virtual environment and installs dependencies if needed.
REM ==============================================================================

cd /d "%~dp0"

IF NOT EXIST ".setup_complete" (
    echo ==================================================================
    echo Sarthika Code — First-Time Automatic Setup
    echo ==================================================================
    echo Configuring environment on your computer... Please wait a moment.
    
    SET "PY_CMD="
    python --version >nul 2>&1
    IF NOT ERRORLEVEL 1 (
        SET "PY_CMD=python"
    ) ELSE (
        py -3 --version >nul 2>&1
        IF NOT ERRORLEVEL 1 (
            SET "PY_CMD=py -3"
        )
    )

    IF "%PY_CMD%"=="" (
        echo Error: Python 3 was not detected on your system.
        echo Please install Python 3.11+ from https://www.python.org or Microsoft Store.
        pause
        exit /b 1
    )

    echo * Cleaning up any previous incomplete environment...
    IF EXIST ".venv" rmdir /s /q ".venv"
    IF EXIST ".setup_complete" del /f /q ".setup_complete"

    echo * Creating local virtual environment in .venv...
    %PY_CMD% -m venv .venv
    IF ERRORLEVEL 1 (
        echo Failed to create virtual environment.
        IF EXIST ".venv" rmdir /s /q ".venv"
        pause
        exit /b 1
    )

    echo * Installing dependencies (PySide6, SQLAlchemy, httpx)...
    .venv\Scripts\pip.exe install --upgrade pip --quiet
    .venv\Scripts\pip.exe install --ignore-requires-python -e . --quiet
    IF ERRORLEVEL 1 (
        echo Failed to install dependencies.
        IF EXIST ".venv" rmdir /s /q ".venv"
        pause
        exit /b 1
    )
    type nul > ".setup_complete"
    echo * Setup completed successfully!
    echo ==================================================================
)

IF EXIST ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "run.py" %*
) ELSE (
    ".venv\Scripts\python.exe" "run.py" %*
)
