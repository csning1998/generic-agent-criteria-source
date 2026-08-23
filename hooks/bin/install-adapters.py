#!/usr/bin/env python3
"""CLI entry for harness adapter materialization."""

from __future__ import annotations

import sys
from pathlib import Path


_HOOKS_ROOT = Path(__file__).resolve().parent.parent
if str(_HOOKS_ROOT) not in sys.path:
    sys.path.insert(0, str(_HOOKS_ROOT))

from adapter_install.install import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
