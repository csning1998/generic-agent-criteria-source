"""Session state persistence for the IaC collaboration hook."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
from pathlib import Path
from typing import Any


def is_hook_disabled() -> bool:
    """Return True when the owner disabled the hook for this process."""
    return os.environ.get("ENGINEERING_PRINCIPLES_HOOK", "1") == "0"


def resolve_state_root() -> Path:
    """Return the directory that holds per-session JSON state files."""
    return Path(
        os.environ.get(
            "ENGINEERING_PRINCIPLES_STATE_DIR",
            str(Path.home() / ".grok" / "hooks" / "state"),
        )
    )


def extract_session_id(payload: dict[str, Any]) -> str:
    """Return a stable session key, or a distinct ephemeral id."""
    value = (
        os.environ.get("GROK_SESSION_ID")
        or payload.get("sessionId")
        or payload.get("session_id")
    )
    if value:
        return str(value)
    return f"ephemeral-{os.getpid()}-{secrets.token_hex(8)}"


def resolve_workspace_root(payload: dict[str, Any]) -> Path:
    """Return the workspace root carried on the hook payload."""
    raw = (
        os.environ.get("GROK_WORKSPACE_ROOT")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or payload.get("workspaceRoot")
        or payload.get("workspace_root")
        or payload.get("cwd")
        or os.getcwd()
    )
    return Path(str(raw)).expanduser()


def resolve_state_path(payload: dict[str, Any]) -> Path:
    """Return the JSON path for this session and workspace pair."""
    workspace = resolve_workspace_root(payload)
    digest = hashlib.sha256(
        str(workspace.resolve()).encode("utf-8")
    ).hexdigest()[:16]
    key = f"{extract_session_id(payload)}__{digest}"
    return resolve_state_root() / f"{key}.json"


def derive_empty_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a fresh state document for this payload."""
    return {
        "version": 2,
        "session_id": extract_session_id(payload),
        "workspace_root": str(resolve_workspace_root(payload)),
        "read_paths": [],
        "generic_leave": False,
        "generic_leave_modules": [],
        "guest_sql_leave": False,
        "last_prompt": "",
        "skill_module_writes": [],
    }


def load_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Load session state, or return an empty document."""
    path = resolve_state_path(payload)
    if not path.is_file():
        return derive_empty_state(payload)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return derive_empty_state(payload)
    if not isinstance(data, dict):
        return derive_empty_state(payload)
    merged = derive_empty_state(payload)
    merged.update(data)
    if not isinstance(merged.get("read_paths"), list):
        merged["read_paths"] = []
    if not isinstance(merged.get("generic_leave_modules"), list):
        merged["generic_leave_modules"] = []
    if not isinstance(merged.get("skill_module_writes"), list):
        merged["skill_module_writes"] = []
    return merged


def persist_state(payload: dict[str, Any], state: dict[str, Any]) -> None:
    """Atomically write session state to disk."""
    path = resolve_state_path(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
        os.replace(tmp_name, path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise
