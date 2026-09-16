"""Detect baked workspace identifiers in skill-module files."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from engineering_principles.config import OLD_TEXT_MAX_BYTES
from engineering_principles.paths import is_self_path
from engineering_principles.state import load_state
from engineering_principles.state import persist_state
from engineering_principles.state import resolve_workspace_root


PLACEHOLDER_RE = re.compile(r"<[^>\n]+>")
PLACEHOLDER_TOKEN_RE = re.compile(r"^<[^>\n]+>$")
COLLECTION_UUID_RE = re.compile(
    r"collection://[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
HOME_PATH_RE = re.compile(r"(?:/home/|\$HOME/)[A-Za-z0-9._-]+")
OWNER_LOGIN_RE = re.compile(r"\bcsning1998\b")
NOTION_ID_PREFIX_RE = re.compile(r"\b316919d4\b", re.I)
TABLE_KEYS = frozenset(
    {
        "allowlist",
        "type_from_conv",
        "repo_area",
        "area_patterns",
        "old_area",
        "title_contains",
        "keep_exact",
        "keep_prefixes",
        "rename",
        "bang_adds",
    }
)
SCHEMA_KEYS = frozenset({"pattern", "label"})
WRITE_TARGET_RE = re.compile(
    r"(?:>>?|tee(?:\s+-a)?)\s+"
    r"(?:'([^']+)'|\"([^\"]+)\"|([^\s;|&]+))"
)
ECHO_RE = re.compile(
    r"^\s*echo(?:\s+-[neE]+)*\s+(?P<body>.*?)\s*(?:>>?|\|)",
    re.DOTALL,
)
PRINTF_RE = re.compile(
    r"^\s*printf\s+(?P<body>.*?)\s*(?:>>?|\|)",
    re.DOTALL,
)
HEREDOC_RE = re.compile(
    r"<<[-]?(['\"]?)(\w+)\1\n(.*?)(?:\n\2)(?:\n|$)",
    re.DOTALL,
)
PATH_TOKEN_RE = re.compile(r"'([^']*)'|\"([^\"]*)\"|([^\s;|&]+)")
SEGMENT_SPLIT_RE = re.compile(r"&&|\|\||[\n;]")
DENY_MESSAGE = (
    "skill-module contract: a module MUST be stateless. "
    "Remove baked identifier ({hit}). "
    "Collection IDs, group paths, mapping tables, and home paths "
    "belong in the layer JSON."
)


def is_skill_module_path(path: str) -> bool:
    """Return True when the path is under a skill-module directory."""
    posix = path.replace("\\", "/")
    return "/skill-module-" in posix or posix.startswith("skill-module-")


def _normalize_stripped(text: str) -> str:
    """Remove placeholder tokens so examples are not treated as state."""
    return PLACEHOLDER_RE.sub("", text)


def _is_placeholder_only(value: object) -> bool:
    """Return True when JSON value is empty or only placeholder tokens."""
    if value is None:
        return True
    if isinstance(value, str):
        return bool(PLACEHOLDER_TOKEN_RE.fullmatch(value.strip()))
    if isinstance(value, dict):
        if not value:
            return True
        for key, item in value.items():
            key_text = str(key).strip()
            key_ok = bool(PLACEHOLDER_TOKEN_RE.fullmatch(key_text)) or (
                key_text in SCHEMA_KEYS
            )
            if not key_ok or not _is_placeholder_only(item):
                return False
        return True
    if isinstance(value, list):
        return all(_is_placeholder_only(item) for item in value)
    return False


def _extract_json_values(text: str) -> list[object]:
    """Return JSON objects and arrays decoded from the original text."""
    decoder = json.JSONDecoder()
    values: list[object] = []
    index = 0
    length = len(text)
    while index < length:
        while index < length and text[index] not in "{[":
            index += 1
        if index >= length:
            break
        try:
            value, end = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            index += 1
            continue
        values.append(value)
        index = end
    return values


def _is_path_rename(value: object) -> bool:
    """Return True when a rename object is a from/to path pair."""
    if not isinstance(value, dict) or not value:
        return False
    return set(value) <= {"from", "to"}


def _find_filled_table_hit(value: object) -> str | None:
    """Return a mapping-table label when a JSON value bakes table data."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key not in TABLE_KEYS or _is_placeholder_only(item):
                continue
            if key == "rename" and _is_path_rename(item):
                continue
            return f"mapping table: {key}"
        for item in value.values():
            hit = _find_filled_table_hit(item)
            if hit:
                return hit
    elif isinstance(value, list):
        for item in value:
            hit = _find_filled_table_hit(item)
            if hit:
                return hit
    return None


def find_first_stateful_hit(text: str) -> str | None:
    """Return a deny snippet when module text bakes workspace state."""
    body = _normalize_stripped(text)
    for pattern, label in (
        (COLLECTION_UUID_RE, "collection UUID"),
        (HOME_PATH_RE, "absolute home path"),
        (OWNER_LOGIN_RE, "owner login"),
        (NOTION_ID_PREFIX_RE, "workspace id prefix"),
    ):
        match = pattern.search(body)
        if match:
            return f"{label}: {match.group(0)}"
    # Placeholder strip turns {"<key>": "<label>"} into {"": ""}.
    # JSONDecoder walks objects in the original text.
    for value in _extract_json_values(text):
        hit = _find_filled_table_hit(value)
        if hit:
            return hit
    return None


def derive_composed_module_text(
    content: str,
    before: str,
    old_string: str,
    new_string: str,
) -> str:
    """Return the file text the write would produce."""
    if content:
        return content
    if old_string and new_string and before and old_string in before:
        return before.replace(old_string, new_string, 1)
    if new_string:
        return new_string
    return ""


def _extract_path_token(match: re.Match[str]) -> str:
    """Return the captured path token from a PATH_TOKEN_RE match."""
    return match.group(1) or match.group(2) or match.group(3) or ""


def _extract_tokens(text: str) -> list[str]:
    """Return quoted or bare tokens from a shell fragment."""
    return [
        _extract_path_token(match)
        for match in PATH_TOKEN_RE.finditer(text or "")
    ]


def _has_sed_in_place(body: str) -> bool:
    """Return True when sed tokens include an -i flag."""
    return any(
        item == "-i" or item.startswith("-i") for item in _extract_tokens(body)
    )


def _extract_shell_segments(command: str) -> list[str]:
    """Split a command on &&, ||, semicolons, and newlines."""
    return [
        part.strip()
        for part in SEGMENT_SPLIT_RE.split(command or "")
        if part.strip()
    ]


def _extract_positional_args(tokens: list[str]) -> list[str]:
    """Return tokens after the command name, skipping short options."""
    return [item for item in tokens[1:] if not item.startswith("-")]


def extract_heredoc_bodies(command: str) -> list[str]:
    """Return heredoc bodies from a shell command."""
    return [match.group(3) for match in HEREDOC_RE.finditer(command or "")]


def extract_shell_write_payloads(command: str) -> list[str]:
    """Return text a shell write would put on disk."""
    blobs = extract_heredoc_bodies(command)
    for segment in _extract_shell_segments(command):
        tokens = _extract_tokens(segment)
        if not tokens:
            continue
        head = tokens[0]
        if head == "echo":
            match = ECHO_RE.search(segment)
            if match and match.group("body").strip():
                blobs.append(match.group("body").strip())
        elif head == "printf":
            match = PRINTF_RE.search(segment)
            if match and match.group("body").strip():
                blobs.append(match.group("body").strip())
        elif head == "sed" and _has_sed_in_place(segment):
            args = _extract_positional_args(tokens)
            if len(args) >= 2:
                blobs.extend(args[:-1])
    return blobs


def extract_shell_write_targets(command: str) -> list[str]:
    """Return skill-module destinations of redirect, tee, cp, mv, or sed -i."""
    raws: list[str] = []
    for match in WRITE_TARGET_RE.finditer(command or ""):
        raws.append(match.group(1) or match.group(2) or match.group(3) or "")
    for segment in _extract_shell_segments(command):
        tokens = _extract_tokens(segment)
        if not tokens:
            continue
        head = tokens[0]
        args = _extract_positional_args(tokens)
        if head in {"cp", "mv"} and args:
            raws.append(args[-1])
        elif head == "sed" and _has_sed_in_place(segment) and args:
            raws.append(args[-1])
    found: list[str] = []
    for raw in raws:
        if raw and is_skill_module_path(raw) and raw not in found:
            found.append(raw)
    return found


def find_module_stateless_reason(path: str, text: str) -> str | None:
    """Return a deny reason for a stateful skill-module write."""
    if not path or not is_skill_module_path(path):
        return None
    hit = find_first_stateful_hit(text)
    if hit is None:
        return None
    return DENY_MESSAGE.format(hit=hit)


def _is_path_in_scope(path: str, workspace: str) -> bool:
    """Return True when a path sits under workspaceRoot or ~/.grok."""
    candidate = Path(path).expanduser()
    if workspace:
        try:
            resolved = candidate.resolve()
            root = Path(workspace).expanduser().resolve()
        except OSError:
            return is_self_path(str(candidate))
        if resolved.is_relative_to(root):
            return True
    return is_self_path(str(candidate))


def load_module_file(path: str, workspace: str = "") -> str:
    """Return file text, or empty when missing, oversized, or out of scope."""
    candidate = Path(path).expanduser()
    if workspace and not _is_path_in_scope(str(candidate), workspace):
        return ""
    try:
        if not candidate.is_file():
            return ""
        if candidate.stat().st_size > OLD_TEXT_MAX_BYTES:
            return ""
        return candidate.read_text(encoding="utf-8")
    except OSError:
        return ""


def normalize_module_path(path: str) -> str:
    """Return an expanded path for session recording."""
    candidate = Path(path).expanduser()
    try:
        return str(candidate.resolve())
    except OSError:
        return str(candidate)


def resolve_skill_module_paths(
    path: str,
    text: str,
    cwd: str = "",
    workspace: str = "",
) -> list[str]:
    """Return skill-module paths named by a write target or a shell write."""
    found: list[str] = []
    root = Path(cwd).expanduser() if cwd else Path.cwd()
    candidates: list[str] = []
    if path and is_skill_module_path(path):
        candidates.append(path)
    candidates.extend(extract_shell_write_targets(text or ""))
    for raw in candidates:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        resolved = normalize_module_path(str(candidate))
        if resolved in found:
            continue
        if workspace and not _is_path_in_scope(resolved, workspace):
            continue
        if is_skill_module_path(resolved):
            found.append(resolved)
    return found


def record_skill_module_write(payload: dict[str, Any], path: str) -> None:
    """Record a skill-module path written in this session."""
    root = str(resolve_workspace_root(payload))
    if not _is_path_in_scope(path, root):
        return
    state = load_state(payload)
    writes = [str(item) for item in state.get("skill_module_writes", [])]
    resolved = normalize_module_path(path)
    if resolved not in writes:
        writes.append(resolved)
    state["skill_module_writes"] = writes
    persist_state(payload, state)


def find_dirty_skill_module_hits(
    payload: dict[str, Any],
) -> list[tuple[str, str]]:
    """Return recorded skill-module paths that still bake state."""
    state = load_state(payload)
    root = str(resolve_workspace_root(payload))
    hits: list[tuple[str, str]] = []
    for item in state.get("skill_module_writes") or []:
        path = str(item)
        hit = find_first_stateful_hit(load_module_file(path, root))
        if hit:
            hits.append((path, hit))
    return hits


def find_stop_stateless_reason(payload: dict[str, Any]) -> str | None:
    """Return a Stop block reason when a written module still has state."""
    reason_field = str(payload.get("reason") or "end_turn")
    if reason_field not in {"", "end_turn"}:
        return None
    hits = find_dirty_skill_module_hits(payload)
    if not hits:
        return None
    path, hit = hits[0]
    return (
        DENY_MESSAGE.format(hit=hit)
        + f" Rewrite {path} before ending the turn."
    )


def emit_post_write_scan(path: str, workspace: str = "") -> None:
    """Write a disk-scan finding to stderr after a skill-module mutation."""
    text = load_module_file(path, workspace)
    reason = find_module_stateless_reason(path, text)
    if reason:
        sys.stderr.write(reason + "\n")


module_stateless_reason = find_module_stateless_reason
