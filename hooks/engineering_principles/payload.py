"""Extract hook event fields from a JSON payload."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from engineering_principles.config import OLD_TEXT_MAX_BYTES


def normalize_event(payload: dict[str, Any]) -> str:
    """Return a lowercase event name with non-letters stripped."""
    raw = (
        os.environ.get("GROK_HOOK_EVENT")
        or payload.get("hookEventName")
        or payload.get("hook_event_name")
        or ""
    )
    return re.sub(r"[^a-z]", "", str(raw).lower())


def normalize_tool(payload: dict[str, Any]) -> str:
    """Return a lowercase tool name with non-letters stripped."""
    tool_call = payload.get("toolCall")
    raw = (
        payload.get("toolName")
        or payload.get("tool_name")
        or (tool_call.get("name") if isinstance(tool_call, dict) else "")
        or ""
    )
    return re.sub(r"[^a-z]", "", str(raw).lower())


def extract_tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the tool input object, or an empty dict."""
    tool_call = payload.get("toolCall")
    value = (
        payload.get("toolInput")
        or payload.get("tool_input")
        or (tool_call.get("args") if isinstance(tool_call, dict) else {})
        or {}
    )
    return value if isinstance(value, dict) else {}


def extract_prompt_text(payload: dict[str, Any]) -> str:
    """Return the owner prompt text when present."""
    for key in ("prompt", "userPrompt", "user_prompt", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def extract_file_path(tool_input_data: dict[str, Any]) -> str:
    """Return the target path from a tool input object."""
    for key in (
        "file_path",
        "target_file",
        "path",
        "notebook_path",
        "TargetFile",
        "AbsolutePath",
    ):
        value = tool_input_data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def extract_new_text(tool_input_data: dict[str, Any]) -> str:
    """Return concatenated text that the tool is about to write."""
    chunks: list[str] = []
    for key in (
        "content",
        "contents",
        "new_string",
        "command",
        "CodeContent",
        "ReplacementContent",
    ):
        value = tool_input_data.get(key)
        if isinstance(value, str):
            chunks.append(value)
    chunks_list = tool_input_data.get("ReplacementChunks")
    if isinstance(chunks_list, list):
        for chunk in chunks_list:
            if isinstance(chunk, dict):
                repl = chunk.get("ReplacementContent")
                if isinstance(repl, str):
                    chunks.append(repl)
    return "\n".join(chunks)


def _extract_replacement_chunks_old_text(
    tool_input_data: dict[str, Any],
) -> str:
    """Extract prior text from TargetContent in ReplacementChunks."""
    chunks_list = tool_input_data.get("ReplacementChunks")
    if not isinstance(chunks_list, list):
        return ""
    old_chunks = [
        chunk["TargetContent"]
        for chunk in chunks_list
        if isinstance(chunk, dict)
        and isinstance(chunk.get("TargetContent"), str)
    ]
    return "\n".join(old_chunks)


def _load_file_within_limit(path: str) -> str:
    """Read existing file text if within OLD_TEXT_MAX_BYTES."""
    if not path:
        return ""
    candidate = Path(path).expanduser()
    try:
        if not candidate.is_file():
            return ""
        if candidate.stat().st_size > OLD_TEXT_MAX_BYTES:
            return ""
        return candidate.read_text(encoding="utf-8")
    except OSError:
        return ""


def load_old_text(tool_input_data: dict[str, Any], path: str) -> str:
    """Return prior file text, or empty when missing or oversized."""
    for key in ("old_string", "TargetContent"):
        value = tool_input_data.get(key)
        if isinstance(value, str) and value:
            return value
    chunks_text = _extract_replacement_chunks_old_text(tool_input_data)
    if chunks_text:
        return chunks_text
    return _load_file_within_limit(path)


def extract_command(tool_input_data: dict[str, Any]) -> str:
    """Return a shell command string from tool input aliases."""
    for key in (
        "command",
        "cmd",
        "shell_command",
        "script",
        "CommandLine",
    ):
        value = tool_input_data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


USER_REQUEST_RE = re.compile(
    r"<USER_REQUEST>(.*?)</USER_REQUEST>", re.DOTALL | re.IGNORECASE
)


def _extract_event_content(event: dict[str, Any]) -> str:
    """Extract string content from a transcript event dict."""
    if event.get("type") not in {"USER_INPUT", "user"}:
        return ""
    content = event.get("content")
    if isinstance(content, str):
        return content
    message = event.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return message["content"]
    return ""


def _parse_transcript_line(line: str) -> str:
    """Return user request text from a single transcript line if present."""
    text = line.strip()
    if not text:
        return ""
    try:
        event = json.loads(text)
    except json.JSONDecodeError:
        return ""
    if not isinstance(event, dict):
        return ""
    content = _extract_event_content(event)
    if not content:
        return ""
    match = USER_REQUEST_RE.search(content)
    return match.group(1).strip() if match else content.strip()


def _load_transcript_lines(transcript_path: Any) -> list[str]:
    """Read lines from transcript path, returning empty on error."""
    if not transcript_path:
        return []
    path = Path(str(transcript_path))
    if not path.is_file():
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def extract_latest_user_request(payload: dict[str, Any]) -> str:
    """Return the latest user request text from the payload or transcript."""
    direct = extract_prompt_text(payload)
    if direct:
        return direct
    transcript_path = payload.get("transcriptPath") or payload.get(
        "transcript_path"
    )
    for line in reversed(_load_transcript_lines(transcript_path)):
        result = _parse_transcript_line(line)
        if result:
            return result
    return ""
