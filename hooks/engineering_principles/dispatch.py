"""Hook event dispatch and process entry."""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from engineering_principles.config import MUTATING_TOOLS
from engineering_principles.config import READ_TOOLS
from engineering_principles.evaluate import find_write_deny_reason
from engineering_principles.evaluate import record_leave
from engineering_principles.evaluate import record_read
from engineering_principles.module_stateless import derive_composed_module_text
from engineering_principles.module_stateless import emit_post_write_scan
from engineering_principles.module_stateless import extract_shell_write_payloads
from engineering_principles.module_stateless import find_module_stateless_reason
from engineering_principles.module_stateless import find_stop_stateless_reason
from engineering_principles.module_stateless import record_skill_module_write
from engineering_principles.module_stateless import resolve_skill_module_paths
from engineering_principles.payload import extract_command
from engineering_principles.payload import extract_file_path
from engineering_principles.payload import extract_new_text
from engineering_principles.payload import extract_prompt_text
from engineering_principles.payload import extract_tool_input
from engineering_principles.payload import load_old_text
from engineering_principles.payload import normalize_event
from engineering_principles.payload import normalize_tool
from engineering_principles.state import is_hook_disabled
from engineering_principles.state import load_state
from engineering_principles.state import resolve_workspace_root


def deny(reason: str) -> int:
    """Print a deny decision and return exit code 2."""
    print(
        json.dumps({"decision": "deny", "reason": reason}, ensure_ascii=False)
    )
    return 2


def block_stop(reason: str) -> int:
    """Print a Stop block decision and return exit code 2."""
    print(
        json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False)
    )
    return 2


def allow(extra: dict[str, Any] | None = None) -> int:
    """Print an allow decision and return exit code 0."""
    body: dict[str, Any] = {"decision": "allow"}
    if extra:
        body.update(extra)
    print(json.dumps(body, ensure_ascii=False))
    return 0


def intercept_pre_tool_use(payload: dict[str, Any]) -> int:
    """Evaluate a PreToolUse payload and deny forbidden writes."""
    tool = normalize_tool(payload)
    tool_input_data = extract_tool_input(payload)
    path = extract_file_path(tool_input_data)
    text = extract_new_text(tool_input_data)
    command_text = extract_command(tool_input_data)
    before = load_old_text(tool_input_data, path)
    file_before = load_old_text({}, path)
    root = str(resolve_workspace_root(payload))
    cwd = str(payload.get("cwd") or root)

    if tool in READ_TOOLS and path:
        record_read(payload, path)
        return allow()

    if tool not in MUTATING_TOOLS:
        return allow()

    content = ""
    if isinstance(tool_input_data.get("content"), str):
        content = tool_input_data["content"]
    elif isinstance(tool_input_data.get("contents"), str):
        content = tool_input_data["contents"]
    old_string = tool_input_data.get("old_string")
    new_string = tool_input_data.get("new_string")
    scan = derive_composed_module_text(
        content,
        file_before,
        old_string if isinstance(old_string, str) else "",
        new_string if isinstance(new_string, str) else "",
    )
    blobs = [
        item
        for item in (scan, *extract_shell_write_payloads(command_text))
        if item
    ]
    for item in resolve_skill_module_paths(path, command_text, cwd, root):
        for blob in blobs:
            module_reason = find_module_stateless_reason(item, blob)
            if module_reason:
                return deny(module_reason)

    reason = find_write_deny_reason(
        payload, path, text, command_text, before=before
    )
    if reason:
        return deny(reason)
    return allow()


def intercept_post_tool_use(payload: dict[str, Any]) -> int:
    """Record reads and scan a skill-module file after a successful write."""
    tool = normalize_tool(payload)
    tool_input_data = extract_tool_input(payload)
    path = extract_file_path(tool_input_data)
    command_text = extract_command(tool_input_data)
    root = str(resolve_workspace_root(payload))
    cwd = str(payload.get("cwd") or root)
    if tool in READ_TOOLS and path:
        record_read(payload, path)
    if tool in MUTATING_TOOLS:
        for item in resolve_skill_module_paths(path, command_text, cwd, root):
            record_skill_module_write(payload, item)
            emit_post_write_scan(item, root)
    return 0


def intercept_stop(payload: dict[str, Any]) -> int:
    """Block the turn when a written skill-module file still bakes state."""
    reason = find_stop_stateless_reason(payload)
    if reason:
        return block_stop(reason)
    return 0


def intercept_user_prompt(payload: dict[str, Any]) -> int:
    """Record leave phrases. Inject no context."""
    prompt = extract_prompt_text(payload)
    if prompt:
        record_leave(payload, prompt)
    return 0


def intercept_session_start(payload: dict[str, Any]) -> int:
    """Create session state. Inject no context."""
    load_state(payload)
    return 0


def dispatch(payload: dict[str, Any]) -> int:
    """Route one hook payload to the matching handler."""
    if is_hook_disabled():
        return allow() if normalize_event(payload) == "pretooluse" else 0
    event = normalize_event(payload)
    if event == "pretooluse":
        return intercept_pre_tool_use(payload)
    if event == "posttooluse":
        return intercept_post_tool_use(payload)
    if event == "userpromptsubmit":
        return intercept_user_prompt(payload)
    if event == "sessionstart":
        return intercept_session_start(payload)
    if event in {"stop", "subagentstop"}:
        return intercept_stop(payload)
    return 0


def main() -> int:
    """Read stdin JSON and dispatch. Tests live in pytest."""
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"invalid hook payload: {exc}\n")
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        return dispatch(payload)
    except Exception as exc:  # noqa: BLE001
        event = normalize_event(payload)
        sys.stderr.write(f"engineering-principles hook error: {exc}\n")
        traceback.print_exc(file=sys.stderr)
        if event == "pretooluse" and normalize_tool(payload) in MUTATING_TOOLS:
            return deny(f"hook error while evaluating a write: {exc}")
        return 0
