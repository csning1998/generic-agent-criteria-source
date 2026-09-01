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
STATE_DIR = Path(f"/tmp/claude-gate-state-{os.getuid()}")

HARD_DENY_COMMAND_SUBSTRINGS = ("git push --force", "git push -f", "rm -rf")
NOTEBOOK_GLOBS = ("*.ipynb",)
EXEC_PHRASES = ("Approve", "Accept", "Agree", "Consent", "Permit", "Execute")

# Rule 401(f): flags the standalone pronoun form following a comment
# marker anywhere on the line, including a trailing comment after code,
# excluding demonstrative-adjective uses that modify a following noun.
BARE_IT_PATTERN = re.compile(r"(?:#|//).*\bit\b", re.IGNORECASE)
COMMENT_CHECK_SKIP_GLOBS = ("*.md", "*.mdx")


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


def match_path(scenarios: list[dict], file_path: str) -> dict | None:
    """Return the first scenario whose path_glob matches file_path's name."""
    name = Path(file_path).name
    for meta in scenarios:
        for pattern in meta.get("path_glob", []):
            if fnmatch.fnmatch(name, pattern):
                return meta
    return None


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


def marker(session_id: str, scenario_id: str) -> Path:
    """Return the session-scoped gate-state marker path for a scenario."""
    return STATE_DIR / session_id / scenario_id


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
    path = Path(transcript_path)
    if not path.exists():
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


def deny(reason: str, additional_context: str | None = None) -> NoReturn:
    """Emit a PreToolUse deny decision and exit."""
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
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }
    print(json.dumps(payload))
    sys.exit(0)


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


def find_bare_it_violation(text: str) -> str | None:
    """Return the first comment line containing a bare pronoun 'it', if any."""
    for line in text.splitlines():
        if BARE_IT_PATTERN.search(line):
            return line.strip()
    return None


def resulting_text(tool_input: dict, file_path: str) -> str:
    """Return the post-write text an Edit or Write call would produce.

    An Edit call's `new_string` alone omits unchanged surrounding text,
    which would miss a violation spanning the old/new boundary; this
    merges `new_string` into the on-disk file the same way Edit applies it.
    """
    if "new_string" not in tool_input:
        return tool_input.get("content", "")
    old_string = tool_input.get("old_string", "")
    new_string = tool_input.get("new_string", "")
    try:
        current = Path(file_path).read_text(encoding="utf-8")
    except OSError:
        return new_string
    if tool_input.get("replace_all"):
        return current.replace(old_string, new_string)
    return current.replace(old_string, new_string, 1)


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
    skip = COMMENT_CHECK_SKIP_GLOBS
    if not any(fnmatch.fnmatch(Path(file_path).name, g) for g in skip):
        write_text = resulting_text(tool_input, file_path)
        violation = find_bare_it_violation(write_text)
        if violation:
            deny(
                "401-f register: a comment line uses the bare pronoun "
                "'it' with no noun a cold reader can point to. Name "
                f"the concrete noun instead. Flagged line: {violation!r}"
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
    """Deny unless an EXEC_PHRASES token appears in the current user turn."""
    prompt_text = last_user_message(payload.get("transcript_path", ""))
    if not any(phrase in prompt_text for phrase in EXEC_PHRASES):
        deny(
            f"external-write.md: {reason} requires explicit execution "
            "authorization in the current user turn. Call AskUserQuestion now "
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
        # a known read-only pattern; an unmatched command, including an
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


def main() -> None:
    """Read the PreToolUse payload from stdin and dispatch by tool_name."""
    payload = json.load(sys.stdin)
    tool_name = payload.get("tool_name", "")
    scenarios = load_scenarios()
    if tool_name in ("Edit", "Write"):
        handle_edit_write(payload, scenarios)
    elif tool_name == "Bash":
        handle_bash(payload, scenarios)
    else:
        allow()


if __name__ == "__main__":
    main()
