#!/usr/bin/env python3
"""CLI entry for resolving a context docs_root."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


if __name__ == "__main__":
    runpy.run_module("context_docs.resolve", run_name="__main__")
