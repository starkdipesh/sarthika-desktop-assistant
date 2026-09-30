"""Convenience root entrypoint for running Sarthika Code."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the 'src' directory is in sys.path
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from sarthika_code.main import main

if __name__ == "__main__":
    sys.exit(main())
