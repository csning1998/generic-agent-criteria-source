#!/usr/bin/env python3
"""PreToolUse gate for Claude Code, materialized from criteria frontmatter.

Denies a matching Edit/Write/Bash call once per session and surfaces the
routed scenario's `load:` files as additionalContext, per
hooks/criteria/README.md Section 2. A retry of the same scenario within
the session passes through.
"""

from __future__ import annotations

import fnmatch
import json
import os
import sys
from pathlib import Path
from typing import NoReturn

from scenario_parser import find_most_specific_scenario
from scenario_parser import load_scenarios_from_dir
from scenario_parser import parse_frontmatter
from scenario_parser import parse_languages_entries


__all__ = [
    "find_most_specific_scenario",
    "load_scenarios",
    "parse_frontmatter",
    "parse_languages_entries",
]

CRITERIA_DIR = Path.home() / ".agents" / "criteria"
STATE_DIR: Path | None = None

HARD_DENY_COMMAND_SUBSTRINGS = ("git push --force", "git push -f", "rm -rf")
NOTEBOOK_GLOBS = ("*.ipynb",)
EXEC_PHRASES = (
    "Approve",
    "Accept",
    "Agree",
    "Consent",
    "Permit",
    "Execute",
    "去執行",
    "跑這個",
    "請執行",
    "執行吧",
)
WRITE_TOOLS = frozenset({"Edit", "Write", "StrReplace", "TabWrite"})
SHELL_TOOLS = frozenset({"Bash", "Shell"})
CURSOR_MCP_WRITE_MARKERS = (
    "save_note",
    "save_merge_request_review",
    "save_merge_request",
    "create_issue",
    "create_pull_request",
    "add_issue_comment",
    "add_comment_to_pending_review",
    "pull_request_review_write",
    "issue_write",
    "merge_pull_request",
    "accept_merge_request",
)


def load_scenarios() -> list[dict]:
    """Load every criteria scenario's frontmatter under CRITERIA_DIR."""
    return load_scenarios_from_dir(CRITERIA_DIR)


def find_matching_command_scenario(
    scenarios: list[dict], command: str
) -> dict | None:
    """Return the first scenario whose command_glob matches command."""
    for meta in scenarios:
        for pattern in meta.get("command_glob", []):
            if pattern in command:
                return meta
    return None


def render_scenario_bundle_text(meta: dict) -> str:
    """Concatenate the referenced text of every file in meta's load list."""
    parts = []
    for rel in meta.get("load", []):
        ref_path = CRITERIA_DIR / rel
        if ref_path.exists():
            parts.append(
                f"=== {rel} ===\n{ref_path.read_text(encoding='utf-8')}"
            )
    return "\n\n".join(parts)


def resolve_state_directory() -> Path:
    """Return the session marker tree for this materialized adapter."""
    if STATE_DIR is not None:
        return STATE_DIR
    label = "cursor" if is_cursor_runtime() else "claude"
    return Path(f"/tmp/{label}-gate-state-{os.getuid()}")


def resolve_marker_path(session_id: str, scenario_id: str) -> Path:
    """Return the session-scoped gate-state marker path for a scenario."""
    return resolve_state_directory() / session_id / scenario_id


def is_scenario_surfaced(session_id: str, scenario_id: str) -> bool:
    """Return whether scenario_id has already been surfaced this session."""
    return resolve_marker_path(session_id, scenario_id).exists()


def record_surfaced_scenario(session_id: str, scenario_id: str) -> None:
    """Record that scenario_id has been surfaced this session."""
    path = resolve_marker_path(session_id, scenario_id)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    path.touch(mode=0o600, exist_ok=True)


def extract_latest_user_prompt(transcript_path: str) -> str:
    """Extract and aggregate all user-attributable text within the turn."""
    if not transcript_path:
        return ""
    path = Path(transcript_path)
    if not path.is_file():
        return ""
    buffer: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "user":
            continue
        message = event.get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            buffer = [content]
            continue
        if not isinstance(content, list):
            continue
        has_real_text = any(
            isinstance(b, dict) and b.get("type") != "tool_result"
            for b in content
        )
        piece = "".join(_block_text(block) for block in content)
        if has_real_text:
            buffer = [piece]
        else:
            buffer.append(piece)
    return "".join(buffer)


def _block_text(block) -> str:
    if not isinstance(block, dict):
        return ""
    if block.get("type") == "tool_result":
        inner = block.get("content")
        if isinstance(inner, str):
            return inner
        if isinstance(inner, list):
            return "".join(_block_text(b) for b in inner)
        return ""
    return block.get("text", "")


def is_cursor_runtime() -> bool:
    """Return True when this file lives under a Cursor hooks directory."""
    return "/.cursor/" in Path(__file__).resolve().as_posix()


def deny(reason: str, additional_context: str | None = None) -> NoReturn:
    """Emit a PreToolUse deny decision and exit."""
    if is_cursor_runtime():
        message = reason
        if additional_context:
            message = reason + "\n\n" + additional_context
        print(
            json.dumps(
                {
                    "permission": "deny",
                    "agent_message": message,
                    "user_message": reason,
                }
            )
        )
        sys.exit(0)
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    if additional_context:
        payload["hookSpecificOutput"]["additionalContext"] = additional_context
    print(json.dumps(payload))
    sys.exit(0)


def allow() -> NoReturn:
    """Emit a PreToolUse allow decision and exit."""
    if is_cursor_runtime():
        print(json.dumps({"permission": "allow"}))
        sys.exit(0)
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }
    print(json.dumps(payload))
    sys.exit(0)


def ask(reason: str) -> NoReturn:
    """Emit Cursor native ask. Claude Code never takes this path."""
    print(
        json.dumps(
            {
                "permission": "ask",
                "user_message": reason,
                "agent_message": reason,
            }
        )
    )
    sys.exit(0)


def _tool_name_has_marker(lowered: str, marker: str) -> bool:
    """True when marker is a tool-id token, not a prefix of a longer token."""
    if not marker:
        return False
    start = 0
    while True:
        idx = lowered.find(marker, start)
        if idx == -1:
            return False
        end = idx + len(marker)
        if end < len(lowered) and (
            lowered[end].isalnum() or lowered[end] == "_"
        ):
            start = idx + 1
            continue
        if idx == 0:
            return True
        prev = lowered[idx - 1]
        if prev in "-:." or prev.isspace():
            return True
        if prev == "_" and (idx >= 2 and lowered[idx - 2] == "_"):
            return True
        if not (prev.isalnum() or prev == "_"):
            return True
        start = idx + 1


def is_cursor_mcp_external_write(tool_name: str) -> bool:
    """Return True for Cursor MCP tools which mutate GitLab or GitHub state."""
    if not is_cursor_runtime():
        return False
    lowered = tool_name.lower()
    return any(
        _tool_name_has_marker(lowered, marker)
        for marker in CURSOR_MCP_WRITE_MARKERS
    )


def enforce_scenario_context_injection(session_id: str, meta: dict) -> None:
    """Allow a scenario's 2nd call this session; deny and surface the 1st."""
    if is_scenario_surfaced(session_id, meta["id"]):
        allow()
    record_surfaced_scenario(session_id, meta["id"])
    deny(
        f"Routed scenario '{meta['id']}' per README.md Section 2; "
        "content surfaced below, retry the same call now.",
        render_scenario_bundle_text(meta),
    )


def intercept_edit_write(payload: dict, scenarios: list[dict]) -> None:
    """Gate an Edit/Write tool call against path_glob-routed scenarios."""
    session_id = payload.get("session_id", "unknown")
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if any(fnmatch.fnmatch(Path(file_path).name, g) for g in NOTEBOOK_GLOBS):
        deny(
            "notebook.md: disk mutation of .ipynb is prohibited in every case; "
            "use Literature Programming in-session instead."
        )
    meta = find_most_specific_scenario(scenarios, file_path)
    if meta is None:
        meta = next(
            (m for m in scenarios if m.get("id") == "local-mutate"), None
        )
    if meta is None:
        allow()
        return
    enforce_scenario_context_injection(session_id, meta)


def require_exec_phrase(payload: dict, reason: str) -> None:
    """Cursor ask covers PreToolUse without an AskUserQuestion transcript."""
    prompt_text = extract_latest_user_prompt(payload.get("transcript_path", ""))
    if any(phrase in prompt_text for phrase in EXEC_PHRASES):
        return
    message = (
        f"external-write.md: {reason} requires explicit execution "
        "authorization in the current user turn."
    )
    if is_cursor_runtime():
        ask(message + " Approve this tool call in the Cursor permission card.")
    deny(
        message + " Call AskUserQuestion now "
        "with an option whose label is exactly Approve "
        "(plus a Deny option), state what will run and that it is "
        "irreversible if applicable, then retry this call after the "
        "answer comes back. Do not wait for the owner to type the phrase "
        "unprompted."
    )


def intercept_bash(payload: dict, scenarios: list[dict]) -> None:
    """Gate a Bash tool call against the hard-deny list and command_glob."""
    session_id = payload.get("session_id", "unknown")
    command = payload.get("tool_input", {}).get("command", "")
    if any(bad in command for bad in HARD_DENY_COMMAND_SUBSTRINGS):
        deny("external-write.md: git push --force and rm -rf must never run.")

    ext_write = next(
        (m for m in scenarios if m.get("id") == "external-write"), None
    )
    if ext_write is not None and any(
        prefix in command for prefix in ext_write.get("command_prefix", [])
    ):
        # Allowlist model: a git/glab/gh invocation is authorized only against
        # a known read-only pattern. An unmatched command, including an
        # unenumerated write subcommand, requires the execution phrase.
        if any(
            p in command for p in ext_write.get("readonly_command_glob", [])
        ) and not any(p in command for p in ext_write.get("command_glob", [])):
            allow()
            return
        matched_pattern = next(
            (p for p in ext_write.get("command_glob", []) if p in command),
            "this git/glab/gh command (not on the read-only allowlist)",
        )
        require_exec_phrase(payload, f"'{matched_pattern}'")
        enforce_scenario_context_injection(session_id, ext_write)
        return

    meta = find_matching_command_scenario(scenarios, command)
    if meta is None:
        allow()
        return
    enforce_scenario_context_injection(session_id, meta)


def normalize_payload(raw: dict) -> dict:
    """Map Claude and Cursor PreToolUse envelopes onto one field set."""
    tool_name = str(
        raw.get("tool_name") or raw.get("toolName") or raw.get("tool") or ""
    )
    session_id = str(
        raw.get("session_id")
        or raw.get("conversation_id")
        or raw.get("conversationId")
        or "unknown"
    )
    tool_input = raw.get("tool_input") or raw.get("arguments") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    path = (
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("filePath")
        or ""
    )
    content = tool_input.get("content")
    if not isinstance(content, str):
        contents = tool_input.get("contents")
        content = contents if isinstance(contents, str) else ""
    command_text = tool_input.get("command") or raw.get("command") or ""
    normalized_input = dict(tool_input)
    if path:
        normalized_input["file_path"] = str(path)
    if content:
        normalized_input["content"] = content
    if isinstance(command_text, str) and command_text:
        normalized_input["command"] = command_text
    mapped = dict(raw)
    mapped["tool_name"] = tool_name
    mapped["session_id"] = session_id
    mapped["tool_input"] = normalized_input
    return mapped


def main() -> None:
    """Read the PreToolUse payload from stdin and dispatch by tool_name."""
    payload = normalize_payload(json.load(sys.stdin))
    tool_name = payload.get("tool_name", "")
    scenarios = load_scenarios()
    if tool_name in WRITE_TOOLS:
        intercept_edit_write(payload, scenarios)
    elif tool_name in SHELL_TOOLS:
        intercept_bash(payload, scenarios)
    elif is_cursor_mcp_external_write(tool_name):
        require_exec_phrase(payload, f"MCP tool '{tool_name}'")
        allow()
    else:
        allow()


if __name__ == "__main__":
    main()
