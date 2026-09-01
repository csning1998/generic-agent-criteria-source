#!/usr/bin/env python3
"""Executes post-tool verification for Claude Code based on scenario criteria.

Triggers post-execution evaluation following `Edit` or `Write` tool calls
matching target `path_glob` patterns. Injects scenario context files
defined in `load:` via `additionalContext` once per session per scenario,
instructing immediate file re-check and inline violation remediation.

Uses an isolated state-marker namespace (`STATE_PREFIX`) distinct from
`gate-check.py`'s, preventing state collisions between the two hooks.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from pathlib import Path


CRITERIA_DIR = Path.home() / ".agents" / "criteria"
STATE_DIR = Path(f"/tmp/claude-gate-state-{os.getuid()}")
STATE_PREFIX = "post-review"

# Mirrors gate-check.py's 401(f)/(d) static checks since a PreToolUse
# failure that raises no error would otherwise leave the write unverified.
BARE_IT_PATTERN = re.compile(r"(?:#|//).*\bit\b", re.IGNORECASE)
COMMA_SO_PATTERN = re.compile(r"^\s*(?:#|//).*,\s*so\b", re.IGNORECASE)
TEMPORAL_DEPENDENCY_PATTERN = re.compile(
    r"^\s*(?:#|//).*\b(this session|current session|mid-session|"
    r"has been observed|this task|current task|current fix|this fix|"
    r"currently|for now|as of now|at the moment|for the time being|"
    r"temporarily|recently|right now|nowadays)\b",
    re.IGNORECASE,
)
COMMENT_LINE_PATTERN = re.compile(r"^\s*(?:#|//)")
MAX_COMMENT_BLOCK_LINES = 3
COMMENT_CHECK_SKIP_GLOBS = ("*.md", "*.mdx")

ARRAY_KEYS = (
    "path_glob",
    "command_prefix",
    "readonly_command_glob",
    "command_glob",
)


def parse_frontmatter(path: Path) -> dict:
    """Parse the YAML-flow-style arrays used by hooks/criteria/*.md."""
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


def resolve_load_text(meta: dict) -> str:
    """Concatenate the referenced text of every file in meta's load list."""
    parts = []
    for rel in meta.get("load", []):
        ref_path = CRITERIA_DIR / rel
        if ref_path.exists():
            text = ref_path.read_text(encoding="utf-8")
            parts.append(f"=== {rel} ===\n{text}")
    return "\n\n".join(parts)


def marker(session_id: str, scenario_id: str) -> Path:
    """Return the state-marker path for session_id and scenario_id."""
    return STATE_DIR / session_id / f"{STATE_PREFIX}__{scenario_id}"


def already_surfaced(session_id: str, scenario_id: str) -> bool:
    """Return whether scenario_id was already surfaced this session."""
    return marker(session_id, scenario_id).exists()


def _ensure_private_dir(path: Path) -> None:
    """Make path a real 0o700 directory.

    Discards a pre-existing symlink or non-directory entry a predictable
    /tmp path could have collected.
    """
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        path.unlink()
    path.mkdir(mode=0o700, exist_ok=True)
    os.chmod(path, 0o700)


def mark_surfaced(session_id: str, scenario_id: str) -> None:
    """Record scenario_id as surfaced for session_id."""
    _ensure_private_dir(STATE_DIR)
    _ensure_private_dir(STATE_DIR / session_id)
    marker(session_id, scenario_id).touch(mode=0o600, exist_ok=True)


def emit(additional_context: str) -> None:
    """Print a PostToolUse hookSpecificOutput payload carrying context."""
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": additional_context,
        }
    }
    print(json.dumps(payload))


def find_register_violations(text: str) -> list[str]:
    """Return one description per mechanical register violation in text."""
    violations: list[str] = []
    lines = text.splitlines()
    block_len = 0
    for line in lines:
        stripped = line.strip()
        if BARE_IT_PATTERN.search(line):
            violations.append(
                f"bare pronoun 'it' with no antecedent noun: {stripped!r}"
            )
        if COMMA_SO_PATTERN.search(line):
            violations.append(f"comma-'so' causal connector: {stripped!r}")
        if TEMPORAL_DEPENDENCY_PATTERN.search(line):
            violations.append(
                f"temporal-dependency language in a comment: {stripped!r}"
            )
        if COMMENT_LINE_PATTERN.match(line) and stripped not in ("#", "//"):
            block_len += 1
            if block_len == MAX_COMMENT_BLOCK_LINES + 1:
                violations.append(
                    f"comment block exceeds {MAX_COMMENT_BLOCK_LINES} lines, "
                    f"starting near: {stripped!r}"
                )
        else:
            block_len = 0
    return violations


def main() -> None:
    """Run the PostToolUse register and scenario-load checks on stdin."""
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    if payload.get("tool_name") not in ("Edit", "Write"):
        return
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return

    skip = COMMENT_CHECK_SKIP_GLOBS
    if not any(fnmatch.fnmatch(Path(file_path).name, g) for g in skip):
        write_text = (
            tool_input.get("new_string") or tool_input.get("content") or ""
        )
        violations = find_register_violations(write_text)
        if violations:
            listed = "\n".join(f"- {v}" for v in violations)
            emit(
                "Register VIOLATION DETECTED (mechanical check, not "
                "advisory): fix every line below in the file now, "
                f"before any other action.\n{listed}"
            )
            return

    scenarios = load_scenarios()
    meta = match_path(scenarios, file_path)
    if meta is None:
        meta = next(
            (m for m in scenarios if m.get("id") == "local-mutate"), None
        )
    if meta is None:
        return

    session_id = payload.get("session_id", "unknown")
    scenario_id = meta["id"]
    file_name = Path(file_path).name

    if not already_surfaced(session_id, scenario_id):
        mark_surfaced(session_id, scenario_id)
        rules = resolve_load_text(meta)
        emit(
            f"Post-write self-review ({scenario_id} scenario) for "
            f"{file_name}. Re-read the rules below against the file you "
            "just wrote. Fix any violation directly in the file now; do "
            "not just acknowledge the violation.\n\n"
            f"{rules}"
        )
    else:
        emit(
            f"Post-write self-review ({scenario_id} scenario) for {file_name}. "
            f"Rules already surfaced this session for '{scenario_id}' — "
            "re-check this specific write against them and fix any violation "
            "directly, without re-reading the full text again."
        )


if __name__ == "__main__":
    main()
