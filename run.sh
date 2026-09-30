#!/usr/bin/env bash
# ==============================================================================
# Sarthika Code — One-Click Launcher (Linux / macOS)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Check for virtual environment python
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_EXEC="$SCRIPT_DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_EXEC="python3"
elif command -v python &>/dev/null; then
    PYTHON_EXEC="python"
else
    echo "Error: Python 3 was not found on your system."
    exit 1
fi

# Launch application
exec "$PYTHON_EXEC" "$SCRIPT_DIR/run.py" "$@"
