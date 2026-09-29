"""Main entrypoint for Sarthika Code desktop assistant.

Launches the application foundation with graceful error handling and shutdown.
"""

from __future__ import annotations

import sys

from sarthika_code.app.application import SarthikaApp
from sarthika_code.domain.errors import SarthikaError


def main() -> int:
    """Bootstrap and launch the Sarthika Code desktop application."""
    if "--version" in sys.argv:
        print("Sarthika Code v0.1.0 (Milestone 1 Foundation)")
        return 0

    try:
        app = SarthikaApp()
        return app.run()
    except SarthikaError as e:
        print(f"\n[Sarthika Code Error]\n{e.format_for_user()}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n[Unexpected Error] Could not start Sarthika Code: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
