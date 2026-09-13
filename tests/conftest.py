"""Pytest path setup for hook and skill scripts."""

import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "hooks"))
sys.path.insert(0, str(_ROOT / "hooks/adapters/claude"))
sys.path.insert(0, str(_ROOT / "skills/skill-module-gitlab-mr-labels/scripts"))
sys.path.insert(0, str(_ROOT / "skills/skill-update-antigravity/scripts"))
