"""Extract hook event fields from a JSON payload."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from engineering_principles.config import OLD_TEXT_MAX_BYTES


def normalize_event(payload: dict[str, Any]) -> str:
    """Return a lowercase event name with non-letters stripped."""
    raw = (
        os.environ.get("GROK_HOOK_EVENT")
        or payload.get("hookEventName")
        or payload.get("hook_event_name")
        or ""
    )
    return re.sub(r"[^a-z]", "", str(raw).lower())


def normalize_tool(payload: dict[str, Any]) -> str:
    """Return a lowercase tool name with non-letters stripped."""
    raw = payload.get("toolName") or payload.get("tool_name") or ""
    return re.sub(r"[^a-z]", "", str(raw).lower())


def extract_tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the tool input object, or an empty dict."""
    value = payload.get("toolInput") or payload.get("tool_input") or {}
    return value if isinstance(value, dict) else {}


def extract_prompt_text(payload: dict[str, Any]) -> str:
    """Return the owner prompt text when present."""
    for key in ("prompt", "userPrompt", "user_prompt", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def extract_file_path(tool_input_data: dict[str, Any]) -> str:
    """Return the target path from a tool input object."""
    for key in ("file_path", "target_file", "path", "notebook_path"):
        value = tool_input_data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def extract_new_text(tool_input_data: dict[str, Any]) -> str:
    """Return concatenated text that the tool is about to write."""
    chunks: list[str] = []
    for key in ("content", "contents", "new_string", "command"):
        value = tool_input_data.get(key)
        if isinstance(value, str):
            chunks.append(value)
    return "\n".join(chunks)


def load_old_text(tool_input_data: dict[str, Any], path: str) -> str:
    """Return prior file text, or empty when missing or oversized."""
    value = tool_input_data.get("old_string")
    if isinstance(value, str) and value:
        return value
    if not path:
        return ""
    candidate = Path(path).expanduser()
    try:
        if not candidate.is_file():
            return ""
        if candidate.stat().st_size > OLD_TEXT_MAX_BYTES:
            return ""
        return candidate.read_text(encoding="utf-8")
    except OSError:
        return ""


def extract_command(tool_input_data: dict[str, Any]) -> str:
    """Return a shell command string from tool input aliases."""
    for key in ("command", "cmd", "shell_command", "script"):
        value = tool_input_data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""
