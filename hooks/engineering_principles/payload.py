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


def load_old_text(tool_input_data: dict[str, Any], path: str) -> str:
    """Return prior file text, or empty when missing or oversized."""
    value = tool_input_data.get("old_string")
    if isinstance(value, str) and value:
        return value
    target_content = tool_input_data.get("TargetContent")
    if isinstance(target_content, str) and target_content:
        return target_content
    chunks_list = tool_input_data.get("ReplacementChunks")
    if isinstance(chunks_list, list):
        old_chunks: list[str] = []
        for chunk in chunks_list:
            if isinstance(chunk, dict):
                t = chunk.get("TargetContent")
                if isinstance(t, str):
                    old_chunks.append(t)
        if old_chunks:
            return "\n".join(old_chunks)
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


def extract_latest_user_request(payload: dict[str, Any]) -> str:
    """Return the latest user request text from the payload or transcript."""
    direct = extract_prompt_text(payload)
    if direct:
        return direct
    transcript_path = payload.get("transcriptPath") or payload.get(
        "transcript_path"
    )
    if not transcript_path:
        return ""
    path = Path(str(transcript_path))
    if not path.is_file():
        return ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    user_request_re = re.compile(
        r"<USER_REQUEST>(.*?)</USER_REQUEST>", re.DOTALL | re.IGNORECASE
    )
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") in {"USER_INPUT", "user"}:
            content = event.get("content")
            if not isinstance(content, str):
                message = event.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
            if isinstance(content, str):
                match = user_request_re.search(content)
                if match:
                    return match.group(1).strip()
                return content.strip()
    return ""
