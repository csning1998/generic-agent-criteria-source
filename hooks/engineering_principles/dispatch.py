"""Hook event dispatch and process entry."""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from engineering_principles.config import GREEN_AUTH_RE
from engineering_principles.config import MAX_STOP_CONTINUATIONS
from engineering_principles.config import MUTATING_TOOLS
from engineering_principles.config import READ_TOOLS
from engineering_principles.config import STOP_BYPASS_TERMINATION_REASONS
from engineering_principles.evaluate import find_drift_gate_reason
from engineering_principles.evaluate import find_write_deny_reason
from engineering_principles.evaluate import record_leave
from engineering_principles.evaluate import record_mutation
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
from engineering_principles.payload import load_latest_user_request_record
from engineering_principles.payload import load_old_text
from engineering_principles.payload import normalize_event
from engineering_principles.payload import normalize_tool
from engineering_principles.state import is_hook_disabled
from engineering_principles.state import load_state
from engineering_principles.state import persist_state
from engineering_principles.state import resolve_workspace_root
from engineering_principles.tdd_gate import find_tdd_stop_block_reason
from engineering_principles.tdd_gate import find_tdd_write_deny_reason
from engineering_principles.tdd_gate import record_tdd_post_tool
from engineering_principles.tdd_gate import record_tdd_prompt_authorization


def is_antigravity_payload(payload: dict[str, Any]) -> bool:
    """Return True if payload originates from an Antigravity harness."""
    return bool(payload.get("conversationId") or payload.get("workspacePaths"))


def deny(reason: str, exit_code: int = 2) -> int:
    """Print a deny decision and return the specified exit code."""
    print(
        json.dumps({"decision": "deny", "reason": reason}, ensure_ascii=False)
    )
    return exit_code


def block_stop(reason: str, is_agy: bool = False) -> int:
    """Print a Stop decision: continue for AGY (code 0) or block (code 2)."""
    decision = "continue" if is_agy else "block"
    print(
        json.dumps({"decision": decision, "reason": reason}, ensure_ascii=False)
    )
    return 0 if is_agy else 2


def allow(extra: dict[str, Any] | None = None) -> int:
    """Print an allow decision and return exit code 0."""
    body: dict[str, Any] = {"decision": "allow"}
    if extra:
        body.update(extra)
    print(json.dumps(body, ensure_ascii=False))
    return 0


def _derive_chunks_module_text(chunks: list[Any], file_before: str) -> str:
    """Derive composite module text from multi-replace chunks."""
    result = file_before
    accumulated: list[str] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        target = chunk.get("TargetContent") or chunk.get("old_string") or ""
        repl = chunk.get("ReplacementContent") or chunk.get("new_string") or ""
        if isinstance(repl, str) and repl:
            accumulated.append(repl)
        if (
            isinstance(target, str)
            and isinstance(repl, str)
            and target
            and target in result
        ):
            result = result.replace(target, repl, 1)
    if result != file_before:
        return result
    return "\n".join(accumulated)


def _extract_module_scan_text(
    tool_input_data: dict[str, Any], file_before: str
) -> str:
    """Derive composite module text from tool input strings."""
    content = (
        tool_input_data.get("content")
        or tool_input_data.get("contents")
        or tool_input_data.get("CodeContent")
        or tool_input_data.get("Content")
    )
    content_str = content if isinstance(content, str) else ""
    old_str = (
        tool_input_data.get("old_string")
        or tool_input_data.get("TargetContent")
        or tool_input_data.get("Target")
    )
    new_str = (
        tool_input_data.get("new_string")
        or tool_input_data.get("ReplacementContent")
        or tool_input_data.get("Replacement")
    )
    base_text = derive_composed_module_text(
        content_str,
        file_before,
        old_str if isinstance(old_str, str) else "",
        new_str if isinstance(new_str, str) else "",
    )
    if base_text:
        return base_text
    chunks = tool_input_data.get("ReplacementChunks")
    if isinstance(chunks, list):
        return _derive_chunks_module_text(chunks, file_before)
    return ""


def _find_module_stateless_violation(
    tool_input_data: dict[str, Any],
    path: str,
    command_text: str,
    file_before: str,
    cwd: str,
    root: str,
) -> str | None:
    """Return deny reason if modifying a skill module violates statelessness."""
    scan = _extract_module_scan_text(tool_input_data, file_before)
    blobs = [
        item
        for item in (scan, *extract_shell_write_payloads(command_text))
        if item
    ]
    for item in resolve_skill_module_paths(path, command_text, cwd, root):
        for blob in blobs:
            reason = find_module_stateless_reason(item, blob)
            if reason:
                return reason
    return None


def _extract_nested_texts(value: Any) -> list[str]:
    """Collect string leaves recursively from dicts and lists."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        items: list[str] = []
        for child in value.values():
            items.extend(_extract_nested_texts(child))
        return items
    if isinstance(value, list):
        items = []
        for child in value:
            items.extend(_extract_nested_texts(child))
        return items
    return []


def find_ask_question_deny_reason(payload: dict[str, Any]) -> str | None:
    """Block ask_question attempts to solicit or substitute green auth."""
    if normalize_tool(payload) != "askquestion":
        return None
    state = load_state(payload)
    stage = str(state.get("tdd_stage") or "idle")
    if stage not in {
        "red_pending_verification",
        "red_verified",
        "premature_green",
    }:
        return None
    combined = "\n".join(_extract_nested_texts(extract_tool_input(payload)))
    if not combined:
        return None
    if "授權轉綠" in combined or GREEN_AUTH_RE.search(combined):
        return (
            "TDD gate (§ 202): ask_question MUST NOT solicit or substitute "
            "for green authorization. Present failing red test output in "
            "response prose and wait for explicit chat authorization."
        )
    return None


def _resolve_pre_tool_exit_code(payload: dict[str, Any]) -> int:
    """Return 0 for Antigravity payloads and 2 for standard harnesses."""
    is_agy = bool(
        payload.get("conversationId") or payload.get("workspacePaths")
    )
    return 0 if is_agy else 2


def intercept_pre_tool_use(payload: dict[str, Any]) -> int:
    """Evaluate a PreToolUse payload and deny forbidden writes."""
    tool = normalize_tool(payload)
    tool_input_data = extract_tool_input(payload)
    path = extract_file_path(tool_input_data)
    if tool in READ_TOOLS and path:
        record_read(payload, path)
        return allow()

    ask_deny = find_ask_question_deny_reason(payload)
    if ask_deny:
        return deny(ask_deny, exit_code=_resolve_pre_tool_exit_code(payload))

    if tool not in MUTATING_TOOLS:
        return allow()

    exit_code = _resolve_pre_tool_exit_code(payload)
    drift_reason = find_drift_gate_reason(payload, path)
    if drift_reason:
        return deny(drift_reason, exit_code=exit_code)

    root = str(resolve_workspace_root(payload))
    cwd = str(payload.get("cwd") or root)
    command_text = extract_command(tool_input_data)
    file_before = load_old_text({}, path)
    module_reason = _find_module_stateless_violation(
        tool_input_data, path, command_text, file_before, cwd, root
    )
    if module_reason:
        return deny(module_reason, exit_code=exit_code)

    text = extract_new_text(tool_input_data)
    tdd_reason = find_tdd_write_deny_reason(payload, path, text)
    if tdd_reason:
        return deny(tdd_reason, exit_code=exit_code)

    before = load_old_text(tool_input_data, path)
    reason = find_write_deny_reason(
        payload, path, text, command_text, before=before
    )
    if reason:
        return deny(reason, exit_code=exit_code)
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
        if path:
            record_mutation(payload, path)
        for item in resolve_skill_module_paths(path, command_text, cwd, root):
            record_skill_module_write(payload, item)
            emit_post_write_scan(item, root)
    record_tdd_post_tool(payload, tool, path, command_text)
    return 0


def _clear_stop_loop_state(payload: dict[str, Any]) -> None:
    """Clear Stop continuation loop counters when a turn finishes or clears."""
    state = load_state(payload)
    if state.get("stop_block_count") or state.get("last_stop_block_reason"):
        state["stop_block_count"] = 0
        state["last_stop_block_reason"] = ""
        persist_state(payload, state)


def intercept_stop(payload: dict[str, Any]) -> int:
    """Block turn when statelessness or TDD requirements are not met."""
    termination_reason = str(payload.get("terminationReason") or "").strip()
    if termination_reason in STOP_BYPASS_TERMINATION_REASONS or (
        bool(termination_reason) and termination_reason != "NO_TOOL_CALL"
    ):
        _clear_stop_loop_state(payload)
        return 0

    is_agy = is_antigravity_payload(payload)
    reason = find_stop_stateless_reason(payload) or find_tdd_stop_block_reason(
        payload
    )
    if not reason:
        _clear_stop_loop_state(payload)
        return 0

    state = load_state(payload)
    _prompt, turn_key = load_latest_user_request_record(payload)
    if turn_key and turn_key != state.get("last_stop_turn_key"):
        state["stop_block_count"] = 0
        state["last_stop_block_reason"] = ""
        state["last_stop_turn_key"] = turn_key
    continuation_active = bool(
        payload.get("continuationActive") or payload.get("stop_hook_active")
    )
    block_count = int(state.get("stop_block_count") or 0)
    same_reason_repeat = continuation_active and (
        reason == state.get("last_stop_block_reason")
    )
    if same_reason_repeat or block_count >= MAX_STOP_CONTINUATIONS:
        return 0

    state["stop_block_count"] = block_count + 1
    state["last_stop_block_reason"] = reason
    if turn_key:
        state["last_stop_turn_key"] = turn_key
    persist_state(payload, state)
    return block_stop(reason, is_agy=is_agy)


def intercept_user_prompt(payload: dict[str, Any]) -> int:
    """Record leave phrases, auth, and reset Stop loop counters."""
    transcript_prompt, turn_key = load_latest_user_request_record(payload)
    prompt = extract_prompt_text(payload) or transcript_prompt
    state = load_state(payload)
    if (
        state.get("stop_block_count")
        or state.get("last_stop_block_reason")
        or (turn_key and turn_key != state.get("last_stop_turn_key"))
        or (prompt and prompt != state.get("last_prompt"))
    ):
        state["stop_block_count"] = 0
        state["last_stop_block_reason"] = ""
        if turn_key:
            state["last_stop_turn_key"] = turn_key
        if prompt:
            state["last_prompt"] = prompt
        persist_state(payload, state)
    if prompt:
        record_leave(payload, prompt)
        record_tdd_prompt_authorization(payload, prompt, turn_key=turn_key)
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
    if event in {"userpromptsubmit", "preinvocation"}:
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
            return deny(
                f"hook error while evaluating a write: {exc}",
                exit_code=_resolve_pre_tool_exit_code(payload),
            )
        return 0
