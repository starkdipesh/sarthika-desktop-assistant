#!/usr/bin/env bash
# ==============================================================================
# Helper to create a clean, portable distribution zip for Ubuntu / Linux users
# Excludes .venv, git history, cache files, and private databases.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR" || exit 1

OUTPUT_ZIP="sarthika-code-ubuntu.zip"
echo "Creating clean portable distribution: $OUTPUT_ZIP ..."

# Remove old zip if exists
rm -f "$OUTPUT_ZIP"

# Zip required project files only
zip -q -r "$OUTPUT_ZIP" \
    src/ \
    assets/ \
    docs/ \
    pyproject.toml \
    README.md \
    LICENSE \
    run.py \
    run.sh \
    run.bat \
    install.sh \
    sarthika-code.desktop \
    App_Setup.md \
    -x "*.pyc" "__pycache__/*" "*/__pycache__/*" "*.gguf" "*.sqlite*" "*.db" ".venv/*" ".git/*"

if [ -f "$OUTPUT_ZIP" ]; then
    SIZE=$(du -h "$OUTPUT_ZIP" | cut -f1)
    echo "=================================================================="
    echo "SUCCESS: $OUTPUT_ZIP created ($SIZE)"
    echo "You can now share this zip file directly with other Ubuntu users!"
    echo "=================================================================="
else
    echo "Failed to create zip file. Make sure 'zip' is installed."
fi
