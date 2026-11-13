#!/usr/bin/env python3
"""Backward-compatibility shim for check_free_games.py."""

import sys

from free_games_checker.app import main

if __name__ == "__main__":
    # If called without arguments from a script/sidecar, default to headless output
    if len(sys.argv) == 1:
        sys.argv.append("--headless")
    sys.exit(main())
