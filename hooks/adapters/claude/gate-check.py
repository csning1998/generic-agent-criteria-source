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
import re
import shlex
import sys
import tempfile
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
# A relabel rewrites the label of the whole source tree and thereby revokes
# access from every container which mounts a path below the source (Sub-doc 61).
VOLUME_FLAG = r"""(?:^|\s)(?:-v(?:=|\s+)?|--volume(?:=|\s+))["']?"""
VOLUME_OPTIONS_PATTERN = re.compile(
    VOLUME_FLAG + r"""[^\s"':]*:[^\s"':]+:([^\s"']+)"""
)
MOUNT_RELABEL_PATTERN = re.compile(r"(?:^|\s)--mount(?:=|\s+)\S*\brelabel=")
RELABEL_VOLUME_OPTIONS = frozenset({"z", "Z"})
# A bind mount exposes a host label to the container label, which SELinux
# denies on an MCS mismatch and which tempts a relabel (Sub-doc 61).
CONTAINER_CLI_PATTERN = re.compile(r"\b(?:podman|docker|nerdctl|buildah)\b")
VOLUME_SOURCE_PATTERN = re.compile(VOLUME_FLAG + r"""([^\s"':]+):""")
BIND_MOUNT_PATTERN = re.compile(
    r"""(?:^|\s)--mount(?:=|\s+)["']?\S*\btype=bind\b"""
)
# kube play and compose read mounts from a file which the gate cannot inspect.
DECLARED_MOUNT_PATTERN = re.compile(
    r"\b(?:podman|docker)\s+(?:kube\s+play|play\s+kube|compose)\b"
    r"|\b(?:podman|docker)-compose\b"
)
# A label write, a policy change, or label=disable alters SELinux state on
# the owner host, which only the owner decides (Sub-doc 61).
SELINUX_WRITE_PATTERN = re.compile(
    r"(?:^\s*|[;&|(`{]\s*|\b(?:then|do|else)\s+"
    r"|\b(?:ba|z|da)?sh\s+(?:-\S+\s+)*[\"']\s*"
    r"|\b(?:sudo|doas|unshare|exec|xargs|env|nohup)\s+"
    r"(?:-\S+\s+)*)(?:\S*/)?"
    r"(?:chcon|restorecon|setfiles|chcat|semanage|setsebool|semodule)\b",
    re.MULTILINE,
)
LABEL_DISABLE_PATTERN = re.compile(
    r"""--security-opt(?:=|\s+)["']?(?:label[=:]disable|\S*\bspc_t)\b"""
)
HOST_PATH_PREFIXES = ("/", ".", "~", "$")
# The hook compares paths with these roots and never writes there.
# /tmp stays listed because TMPDIR may sit below /tmp.
TEMP_DIRECTORIES = (
    Path(tempfile.gettempdir()),
    Path("/tmp"),  # NOSONAR
    Path("/var/tmp"),  # NOSONAR
)
# Git treats config keys as case-insensitive, and every spelling counts.
HOOKS_PATH_OVERRIDE_PATTERN = re.compile(
    r"-c\s*[\"']?core\.hooksPath="
    r"|GIT_CONFIG_[A-Z0-9_]*=[^\n]*core\.hooksPath"
    r"|\bconfig\b(?:(?!--get)[^\n;&|])*\bcore\.hooksPath\b",
    re.IGNORECASE,
)
# A quoted separator and an abbreviation of --no-verify still reach git.
# An extra match is the safe direction for a deny gate.
NO_VERIFY_PATTERN = re.compile(r"\bgit\b[^\n]*\s--no-ve(?:rify|rif|ri|r)?\b")
COMMIT_TREE_PATTERN = re.compile(r"\bgit\b[^\n]*\bcommit-tree\b")
SHELL_SEPARATORS = frozenset({"&&", "||", ";", "|", "&"})
LINE_CONTINUATION = "\\\n"
COMMIT_VALUE_FLAGS = frozenset("mFcCt")
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
    harness = "cursor" if is_cursor_harness() else "claude"
    return _resolve_private_base() / f"{harness}-gate-state"


def _resolve_private_base() -> Path:
    """Return XDG_RUNTIME_DIR, or the user cache directory without it."""
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return Path(runtime)
    cache = os.environ.get("XDG_CACHE_HOME")
    return Path(cache) if cache else Path.home() / ".cache"


def _provision_private_dir(path: Path) -> None:
    """Make path a real 0o700 directory owned by the current user.

    Discards a pre-existing symlink or non-directory entry. Raises
    PermissionError for a directory of another user.
    """
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        path.unlink()
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.lstat().st_uid != os.getuid():
        raise PermissionError(f"{path} belongs to another user.")
    os.chmod(path, 0o700)


def resolve_marker_path(session_id: str, scenario_id: str) -> Path:
    """Return the session-scoped gate-state marker path for a scenario."""
    return resolve_state_directory() / session_id / scenario_id


def is_scenario_surfaced(session_id: str, scenario_id: str) -> bool:
    """Return whether scenario_id has already been surfaced this session."""
    return resolve_marker_path(session_id, scenario_id).exists()


def record_surfaced_scenario(session_id: str, scenario_id: str) -> None:
    """Record that scenario_id has been surfaced this session."""
    root = resolve_state_directory()
    _provision_private_dir(root)
    _provision_private_dir(root / session_id)
    resolve_marker_path(session_id, scenario_id).touch(
        mode=0o600, exist_ok=True
    )


def load_transcript_events(transcript_path: str) -> list[dict]:
    """Load JSON objects from a Claude Code transcript file."""
    if not transcript_path:
        return []
    path = Path(transcript_path)
    if not path.is_file():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def extract_latest_user_prompt(events: list[dict]) -> str:
    """Extract and aggregate all user-attributable text within the turn."""
    buffer: list[str] = []
    for event in events:
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
        piece = "".join(_extract_block_text(block) for block in content)
        if has_real_text:
            buffer = [piece]
        else:
            buffer.append(piece)
    return "".join(buffer)


def _extract_block_text(block) -> str:
    if not isinstance(block, dict):
        return ""
    if block.get("type") == "tool_result":
        inner = block.get("content")
        if isinstance(inner, str):
            return inner
        if isinstance(inner, list):
            return "".join(_extract_block_text(b) for b in inner)
        return ""
    return block.get("text", "")


def is_cursor_harness() -> bool:
    """Return True when this file lives under a Cursor hooks directory."""
    return "/.cursor/" in Path(__file__).resolve().as_posix()


def deny(reason: str, additional_context: str | None = None) -> NoReturn:
    """Emit a PreToolUse deny decision and exit."""
    if is_cursor_harness():
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
    if is_cursor_harness():
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


def _is_tool_name_marker(lowered: str, marker: str) -> bool:
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
    if not is_cursor_harness():
        return False
    lowered = tool_name.lower()
    return any(
        _is_tool_name_marker(lowered, marker)
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
    if is_temp_path(file_path):
        enforce_shell_bans(
            tool_input.get("content") or tool_input.get("new_string") or ""
        )
    meta = find_most_specific_scenario(scenarios, file_path)
    if meta is None:
        meta = next(
            (m for m in scenarios if m.get("id") == "local-mutate"), None
        )
    if meta is None:
        allow()
    enforce_scenario_context_injection(session_id, meta)


def deny_cursor_external_write(reason: str) -> NoReturn:
    """Deny a Cursor external execute act without a readable native signal."""
    deny(
        f"external-write.md: {reason} requires a Cursor native authorization "
        "signal which PreToolUse can read. AskQuestion selections and "
        "AskUserQuestion results are not that signal. Do not invoke "
        "AskQuestion. Do not retry this call as a substitute."
    )


def require_exec_phrase(payload: dict, reason: str) -> None:
    """Authorize an external execute act on a runtime-specific path."""
    if is_cursor_harness():
        deny_cursor_external_write(reason)
    events = load_transcript_events(payload.get("transcript_path") or "")
    prompt_text = extract_latest_user_prompt(events)
    if any(phrase in prompt_text for phrase in EXEC_PHRASES):
        return
    deny(
        f"external-write.md: {reason} requires explicit execution "
        "authorization in the current user turn. Call AskUserQuestion now "
        "with an option whose label is exactly Approve "
        "(plus a Deny option), state what will run and that it is "
        "irreversible if applicable, then retry this call after the "
        "answer comes back. Do not wait for the owner to type the phrase "
        "unprompted."
    )


def has_selinux_relabel_mount(command: str) -> bool:
    """Report whether a container mount in command requests a relabel."""
    if MOUNT_RELABEL_PATTERN.search(command):
        return True
    return any(
        RELABEL_VOLUME_OPTIONS.intersection(match.group(1).split(","))
        for match in VOLUME_OPTIONS_PATTERN.finditer(command)
    )


def has_host_bind_mount(text: str) -> bool:
    """Report whether a container command in text mounts a host path."""
    if not CONTAINER_CLI_PATTERN.search(text):
        return False
    if BIND_MOUNT_PATTERN.search(text) or DECLARED_MOUNT_PATTERN.search(text):
        return True
    return any(
        source.startswith(HOST_PATH_PREFIXES) or "/" in source
        for source in VOLUME_SOURCE_PATTERN.findall(text)
    )


def is_temp_path(file_path: str) -> bool:
    """Report whether file_path lies below a system temp directory."""
    target = Path(file_path).resolve()
    return any(
        target.is_relative_to(directory.resolve())
        for directory in TEMP_DIRECTORIES
    )


def emit_host_bind_mount_denial() -> NoReturn:
    """Deny a host bind mount from an agent command or agent-written script."""
    deny(
        "61-container-runtime-and-selinux.md: a host bind mount into a "
        "container, including a mount declared through kube play or compose, "
        "is prohibited in agent commands and agent-written scripts. "
        "Copy files into the container with podman create and podman cp."
    )


def has_selinux_state_write(text: str) -> bool:
    """Report whether text writes a label, alters policy, or disables labels."""
    return bool(
        SELINUX_WRITE_PATTERN.search(text) or LABEL_DISABLE_PATTERN.search(text)
    )


def has_commit_no_verify_flag(command: str) -> bool:
    """Report whether a git commit in command carries the short flag -n."""
    joined = command.replace(LINE_CONTINUATION, " ")
    return any(
        has_line_commit_no_verify_flag(line) for line in joined.splitlines()
    )


def parse_shell_tokens(line: str) -> list[str]:
    """Split one shell line, with operators as tokens of their own."""
    try:
        lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError:
        return line.split()


def inspect_short_flag_cluster(token: str) -> tuple[bool, bool]:
    """Return whether a flag cluster holds -n and takes the next token."""
    for index, flag in enumerate(token[1:]):
        if flag == "n":
            return True, False
        if flag in COMMIT_VALUE_FLAGS:
            return False, index == len(token) - 2
    return False, False


def has_line_commit_no_verify_flag(line: str) -> bool:
    """Report whether a git commit in one shell line carries the flag -n."""
    in_git = in_commit = skip_value = False
    for token in parse_shell_tokens(line):
        if token in SHELL_SEPARATORS:
            in_git = in_commit = skip_value = False
        elif skip_value:
            skip_value = False
        elif token.rsplit("/", 1)[-1] == "git":
            in_git, in_commit = True, False
        elif in_git and not in_commit and token == "commit":
            in_commit = True
        elif in_commit and token == "--":
            in_commit = False
        elif in_commit and token.startswith("-") and not token.startswith("--"):
            has_no_verify, skip_value = inspect_short_flag_cluster(token)
            if has_no_verify:
                return True
    return False


def has_git_hook_bypass(command: str) -> bool:
    """Report whether command swaps or skips the repository git hooks."""
    joined = command.replace(LINE_CONTINUATION, " ")
    return bool(
        HOOKS_PATH_OVERRIDE_PATTERN.search(joined)
        or NO_VERIFY_PATTERN.search(joined)
        or COMMIT_TREE_PATTERN.search(joined)
        or has_commit_no_verify_flag(joined)
    )


def enforce_shell_bans(text: str) -> None:
    """Deny shell text, a command or a temp script, which breaks a hard ban."""
    if any(bad in text for bad in HARD_DENY_COMMAND_SUBSTRINGS):
        deny("external-write.md: git push --force and rm -rf must never run.")
    if has_selinux_relabel_mount(text):
        deny(
            "61-container-runtime-and-selinux.md: the SELinux relabel options "
            ":z, :Z, and relabel= are globally prohibited on container mounts."
        )
    if has_host_bind_mount(text):
        emit_host_bind_mount_denial()
    if has_selinux_state_write(text):
        deny(
            "61-container-runtime-and-selinux.md: SELinux label writes, "
            "policy changes, label=disable, and spc_t are prohibited in agent "
            "commands and agent-written scripts. Report the needed label "
            "to the owner."
        )
    if has_git_hook_bypass(text):
        deny(
            "external-write.md: overriding core.hooksPath, skipping git hooks "
            "with --no-verify or -n, and committing through git commit-tree "
            "are prohibited."
        )


def intercept_bash(payload: dict, scenarios: list[dict]) -> None:
    """Gate a Bash tool call against the hard-deny list and command_glob."""
    session_id = payload.get("session_id", "unknown")
    command = payload.get("tool_input", {}).get("command", "")
    enforce_shell_bans(command)

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
