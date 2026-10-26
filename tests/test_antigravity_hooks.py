"""Tests for the Antigravity (AGY) hook adapter and drift gate."""

from __future__ import annotations

from pathlib import Path

import pytest
from engineering_principles.config import MUTATING_TOOLS
from engineering_principles.config import READ_TOOLS
from engineering_principles.payload import extract_command
from engineering_principles.payload import extract_file_path
from engineering_principles.payload import extract_new_text
from engineering_principles.payload import extract_tool_input
from engineering_principles.payload import load_old_text
from engineering_principles.payload import normalize_tool
from engineering_principles.state import extract_session_id
from engineering_principles.state import resolve_workspace_root


def _agy_payload(
    tool_name: str,
    tool_args: dict,
    *,
    conversation_id: str = "conv-agy-123",
    workspace_paths: list[str] | None = None,
    transcript_path: str = "/tmp/transcript_full.jsonl",
) -> dict:
    """Build an Antigravity PreToolUse payload shape."""
    return {
        "conversationId": conversation_id,
        "workspacePaths": workspace_paths or ["/home/user/project"],
        "transcriptPath": transcript_path,
        "artifactDirectoryPath": (
            "/home/user/.gemini/antigravity-ide/brain/conv-agy-123"
        ),
        "modelName": "gemini-2.5-pro",
        "stepIdx": 1,
        "toolCall": {
            "name": tool_name,
            "args": tool_args,
        },
    }


def test_agy_tools_registered_in_config() -> None:
    """AGY tool names must be in MUTATING_TOOLS and READ_TOOLS."""
    assert {
        "writetofile",
        "replacefilecontent",
        "multireplacefilecontent",
        "runcommand",
    }.issubset(MUTATING_TOOLS)
    assert "viewfile" in READ_TOOLS


def test_agy_payload_adapter_write_to_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extract Antigravity write_to_file arguments and session metadata."""
    monkeypatch.delenv("GROK_SESSION_ID", raising=False)
    monkeypatch.delenv("GROK_WORKSPACE_ROOT", raising=False)
    payload = _agy_payload(
        "write_to_file",
        {
            "TargetFile": "/workspace/main.py",
            "Overwrite": True,
            "CodeContent": "print('hello')\n",
        },
        conversation_id="conv-456",
        workspace_paths=["/workspace"],
    )
    assert normalize_tool(payload) == "writetofile"
    tool_input = extract_tool_input(payload)
    assert tool_input["TargetFile"] == "/workspace/main.py"
    assert extract_file_path(tool_input) == "/workspace/main.py"
    assert extract_new_text(tool_input) == "print('hello')\n"
    assert extract_session_id(payload) == "conv-456"
    assert resolve_workspace_root(payload) == Path("/workspace")


def test_agy_payload_adapter_replace_file_content() -> None:
    """Extract Antigravity replace_file_content target and replacement text."""
    payload = _agy_payload(
        "replace_file_content",
        {
            "TargetFile": "/workspace/lib.py",
            "TargetContent": "def old(): pass",
            "ReplacementContent": "def new(): pass",
            "StartLine": 10,
            "EndLine": 20,
        },
    )
    assert normalize_tool(payload) == "replacefilecontent"
    tool_input = extract_tool_input(payload)
    assert extract_file_path(tool_input) == "/workspace/lib.py"
    assert extract_new_text(tool_input) == "def new(): pass"
    assert load_old_text(tool_input, "/workspace/lib.py") == "def old(): pass"


def test_agy_payload_adapter_multi_replace_file_content() -> None:
    """Extract Antigravity multi_replace_file_content chunks."""
    payload = _agy_payload(
        "multi_replace_file_content",
        {
            "TargetFile": "/workspace/lib.py",
            "ReplacementChunks": [
                {
                    "TargetContent": "chunk1_old",
                    "ReplacementContent": "chunk1_new",
                    "StartLine": 1,
                    "EndLine": 3,
                },
                {
                    "TargetContent": "chunk2_old",
                    "ReplacementContent": "chunk2_new",
                    "StartLine": 10,
                    "EndLine": 12,
                },
            ],
        },
    )
    assert normalize_tool(payload) == "multireplacefilecontent"
    tool_input = extract_tool_input(payload)
    assert extract_file_path(tool_input) == "/workspace/lib.py"
    new_text = extract_new_text(tool_input)
    assert "chunk1_new" in new_text
    assert "chunk2_new" in new_text
    old_text = load_old_text(tool_input, "/workspace/lib.py")
    assert "chunk1_old" in old_text
    assert "chunk2_old" in old_text


def test_agy_payload_adapter_view_file() -> None:
    """Extract Antigravity view_file absolute path."""
    payload = _agy_payload(
        "view_file",
        {
            "AbsolutePath": "/workspace/docs/spec.md",
            "StartLine": 1,
            "EndLine": 50,
        },
    )
    assert normalize_tool(payload) == "viewfile"
    tool_input = extract_tool_input(payload)
    assert extract_file_path(tool_input) == "/workspace/docs/spec.md"


def test_agy_payload_adapter_run_command() -> None:
    """Extract Antigravity run_command command line string."""
    payload = _agy_payload(
        "run_command",
        {
            "CommandLine": "git diff --staged",
            "Cwd": "/workspace",
            "WaitMsBeforeAsync": 2000,
        },
    )
    assert normalize_tool(payload) == "runcommand"
    tool_input = extract_tool_input(payload)
    assert extract_command(tool_input) == "git diff --staged"
