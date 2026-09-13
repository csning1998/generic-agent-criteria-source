#!/usr/bin/env python3
"""Cursor PreToolUse gate for skill-module baked-state writes."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _hooks_root() -> Path:
    """Return the Grok hooks tree that holds engineering_principles."""
    home = Path.home()
    grok = home / ".grok" / "hooks"
    if (grok / "engineering_principles").is_dir():
        return grok
    return Path(__file__).resolve().parents[2]


_HOOKS = _hooks_root()
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from engineering_principles.module_stateless import (  # noqa: E402
    is_skill_module_path,
)
from engineering_principles.module_stateless import (  # noqa: E402
    module_stateless_reason,
)


def _path_and_text(payload: dict) -> tuple[str, str]:
    tool_input = payload.get("tool_input") or payload.get("arguments") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    path = str(
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("filePath")
        or ""
    )
    content = tool_input.get("content")
    if not isinstance(content, str):
        contents = tool_input.get("contents")
        content = contents if isinstance(contents, str) else ""
    new_string = tool_input.get("new_string")
    if isinstance(new_string, str) and new_string:
        content = new_string if not content else content
    return path, content if isinstance(content, str) else ""


def main() -> None:
    """Deny Cursor writes that bake state into a skill-module path."""
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"permission": "allow"}))
        return
    path, text = _path_and_text(payload)
    if not path or not is_skill_module_path(path):
        print(json.dumps({"permission": "allow"}))
        return
    reason = module_stateless_reason(path, text)
    if reason:
        print(
            json.dumps(
                {
                    "permission": "deny",
                    "user_message": reason,
                    "agent_message": reason,
                }
            )
        )
        return
    print(json.dumps({"permission": "allow"}))


if __name__ == "__main__":
    main()
