#!/usr/bin/env python3
"""PreToolUse gate for Claude Code, materialized from criteria frontmatter.

Denies a matching Edit/Write/Bash call once per session and surfaces the
routed scenario's `load:` files as additionalContext, per
hooks/criteria/00-routing.md Section 2. A retry of the same scenario within
the session passes through.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from pathlib import Path
from typing import NoReturn


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

ARRAY_KEYS = (
    "path_glob",
    "command_prefix",
    "readonly_command_glob",
    "command_glob",
)


def parse_frontmatter(path: Path) -> dict:
    """Parse the YAML-flow-style arrays used by hooks/criteria/*.md.

    Handles both single-line (`key: ["a", "b"]`) and multi-line
    (`key:` then `[` then one quoted item per line then `]`) forms,
    since criteria files use either depending on line length.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    data: dict = {
        "load": [],
        "path_glob": [],
        "command_glob": [],
        "command_prefix": [],
        "readonly_command_glob": [],
    }
    section = None
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("id:"):
            data["id"] = stripped.split(":", 1)[1].strip()
            section = None
            continue
        if stripped == "load:":
            section = "load"
            continue
        matched_key = next(
            (k for k in ARRAY_KEYS if stripped.startswith(k + ":")), None
        )
        if matched_key is not None:
            rest = stripped[len(matched_key) + 1 :].strip()
            data[matched_key] = re.findall(r'"([^"]+)"', rest)
            section = None if rest.endswith("]") else matched_key
            continue
        if stripped.startswith("- ") and section == "load":
            data["load"].append(stripped[2:].strip())
            continue
        if section in ARRAY_KEYS:
            data[section].extend(re.findall(r'"([^"]+)"', stripped))
            if stripped.endswith("]"):
                section = None
            continue
        if re.match(r"^[a-zA-Z_]+:", stripped):
            section = None
    if section in ARRAY_KEYS:
        print(
            f"gate-check.py: WARNING: {path} has an unclosed '{section}' "
            "array (no closing ']' found); whitelist entries may be missing.",
            file=sys.stderr,
        )
    return data


def load_scenarios() -> list[dict]:
    """Load every criteria scenario's frontmatter under CRITERIA_DIR."""
    if not CRITERIA_DIR.is_dir():
        return []
    scenarios = []
    for path in sorted(CRITERIA_DIR.glob("*.md")):
        meta = parse_frontmatter(path)
        if meta.get("id"):
            scenarios.append(meta)
    return scenarios


def _path_glob_specificity(pattern: str) -> int:
    """Score a path_glob pattern by its literal character count."""
    return sum(1 for char in pattern if char not in "*?")


def match_path(scenarios: list[dict], file_path: str) -> dict | None:
    """Return the scenario whose path_glob best matches file_path's name.

    When several scenarios match, the highest specificity score wins.
    A literal `merge-request.md` therefore beats a broad `*.md`.
    """
    name = Path(file_path).name
    best: dict | None = None
    best_score = -10_000
    for meta in scenarios:
        for pattern in meta.get("path_glob", []):
            if not fnmatch.fnmatch(name, pattern):
                continue
            score = _path_glob_specificity(pattern)
            if score > best_score:
                best_score = score
                best = meta
    return best


def match_command(scenarios: list[dict], command: str) -> dict | None:
    """Return the first scenario whose command_glob matches command."""
    for meta in scenarios:
        for pattern in meta.get("command_glob", []):
            if pattern in command:
                return meta
    return None


def resolve_load_text(meta: dict) -> str:
    """Concatenate the referenced text of every file in meta's load list."""
    parts = []
    for rel in meta.get("load", []):
        ref_path = CRITERIA_DIR / rel
        if ref_path.exists():
            parts.append(
                f"=== {rel} ===\n{ref_path.read_text(encoding='utf-8')}"
            )
    return "\n\n".join(parts)


def state_dir() -> Path:
    """Return the session marker tree for this materialized adapter."""
    if STATE_DIR is not None:
        return STATE_DIR
    label = "cursor" if cursor_protocol() else "claude"
    return Path(f"/tmp/{label}-gate-state-{os.getuid()}")


def marker(session_id: str, scenario_id: str) -> Path:
    """Return the session-scoped gate-state marker path for a scenario."""
    return state_dir() / session_id / scenario_id


def already_surfaced(session_id: str, scenario_id: str) -> bool:
    """Return whether scenario_id has already been surfaced this session."""
    return marker(session_id, scenario_id).exists()


def mark_surfaced(session_id: str, scenario_id: str) -> None:
    """Record that scenario_id has been surfaced this session."""
    path = marker(session_id, scenario_id)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    path.touch(mode=0o600, exist_ok=True)


def last_user_message(transcript_path: str) -> str:
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


def cursor_protocol() -> bool:
    """Return True when this file lives under a Cursor hooks directory."""
    return "/.cursor/" in Path(__file__).resolve().as_posix()


def deny(reason: str, additional_context: str | None = None) -> NoReturn:
    """Emit a PreToolUse deny decision and exit."""
    if cursor_protocol():
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
    if cursor_protocol():
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
    if not cursor_protocol():
        return False
    lowered = tool_name.lower()
    return any(
        _tool_name_has_marker(lowered, marker)
        for marker in CURSOR_MCP_WRITE_MARKERS
    )


def gate_once(session_id: str, meta: dict) -> None:
    """Allow a scenario's 2nd call this session; deny and surface the 1st."""
    if already_surfaced(session_id, meta["id"]):
        allow()
    mark_surfaced(session_id, meta["id"])
    deny(
        f"Routed scenario '{meta['id']}' per 00-routing.md Section 2; "
        "content surfaced below, retry the same call now.",
        resolve_load_text(meta),
    )


def handle_edit_write(payload: dict, scenarios: list[dict]) -> None:
    """Gate an Edit/Write tool call against path_glob-routed scenarios."""
    session_id = payload.get("session_id", "unknown")
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if any(fnmatch.fnmatch(Path(file_path).name, g) for g in NOTEBOOK_GLOBS):
        deny(
            "notebook.md: disk mutation of .ipynb is prohibited in every case; "
            "use Literature Programming in-session instead."
        )
    meta = match_path(scenarios, file_path)
    if meta is None:
        meta = next(
            (m for m in scenarios if m.get("id") == "local-mutate"), None
        )
    if meta is None:
        allow()
        return
    gate_once(session_id, meta)


def require_exec_phrase(payload: dict, reason: str) -> None:
    """Cursor ask covers PreToolUse without an AskUserQuestion transcript."""
    prompt_text = last_user_message(payload.get("transcript_path", ""))
    if any(phrase in prompt_text for phrase in EXEC_PHRASES):
        return
    message = (
        f"external-write.md: {reason} requires explicit execution "
        "authorization in the current user turn."
    )
    if cursor_protocol():
        ask(message + " Approve this tool call in the Cursor permission card.")
    deny(
        message + " Call AskUserQuestion now "
        "with an option whose label is exactly Approve "
        "(plus a Deny option), state what will run and that it is "
        "irreversible if applicable, then retry this call after the "
        "answer comes back. Do not wait for the owner to type the phrase "
        "unprompted."
    )


def handle_bash(payload: dict, scenarios: list[dict]) -> None:
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
        gate_once(session_id, ext_write)
        return

    meta = match_command(scenarios, command)
    if meta is None:
        allow()
        return
    gate_once(session_id, meta)


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
        handle_edit_write(payload, scenarios)
    elif tool_name in SHELL_TOOLS:
        handle_bash(payload, scenarios)
    elif is_cursor_mcp_external_write(tool_name):
        require_exec_phrase(payload, f"MCP tool '{tool_name}'")
        allow()
    else:
        allow()


if __name__ == "__main__":
    main()
