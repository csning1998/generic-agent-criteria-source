"""Antigravity PreToolUse gate-check adapter.

Materialized from criteria frontmatter and hard-deny rules.
"""

from __future__ import annotations


def normalize_payload(raw: dict) -> dict:
    """Map Antigravity PreToolUse envelope onto unified field set."""
    raise NotImplementedError


def load_transcript_events(transcript_path: str) -> list[dict]:
    """Load JSON objects from an Antigravity transcript.jsonl file."""
    raise NotImplementedError


def extract_latest_user_prompt(events: list[dict]) -> str:
    """Extract user prompt text from latest USER_INPUT event."""
    raise NotImplementedError


def deny(reason: str, additional_context: str | None = None) -> None:
    """Emit an Antigravity PreToolUse deny decision."""
    raise NotImplementedError


def allow() -> None:
    """Emit an Antigravity PreToolUse allow decision."""
    raise NotImplementedError


def force_ask(reason: str) -> None:
    """Emit an Antigravity PreToolUse force_ask decision."""
    raise NotImplementedError


def intercept_run_command(payload: dict, scenarios: list[dict]) -> None:
    """Gate a run_command tool call against hard-deny and criteria."""
    raise NotImplementedError
