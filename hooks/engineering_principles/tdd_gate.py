"""Test-Driven Development (TDD) gate and state machine enforcement (§ 202)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def is_tdd_test_path(path: str) -> bool:
    """Return True if path matches TDD test globs."""
    return False


def is_tdd_production_path(path: str, workspace_root: Path) -> bool:
    """Return True if path is a governed production file under workspace."""
    return False


def is_scaffolding_only_text(text: str) -> bool:
    """Return True if text only contains stubs or type declarations."""
    return False


def record_tdd_prompt_authorization(
    payload: dict[str, Any], prompt: str
) -> None:
    """Record owner green authorization if prompt matches GREEN_AUTH_RE."""
    return None


def find_tdd_write_deny_reason(
    payload: dict[str, Any], path: str, text: str
) -> str | None:
    """Return deny reason if writing production code violates TDD stages."""
    return None


def record_tdd_post_tool(
    payload: dict[str, Any], tool: str, path: str, command: str
) -> None:
    """Record test modifications, test runner executions, and linter runs."""
    return None


def find_tdd_stop_block_reason(payload: dict[str, Any]) -> str | None:
    """Return stop reason when turn concludes without meeting TDD checks."""
    return None
