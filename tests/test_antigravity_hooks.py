"""Tests for the Antigravity (AGY) hook adapter and drift gate."""

from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest
from engineering_principles.config import MUTATING_TOOLS
from engineering_principles.config import READ_TOOLS
from engineering_principles.dispatch import intercept_post_tool_use
from engineering_principles.dispatch import intercept_pre_tool_use
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


def _run_pre_tool_use(payload: dict) -> tuple[int, dict]:
    """Execute intercept_pre_tool_use and capture stdout JSON."""
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_pre_tool_use(payload)
    output = json.loads(buf.getvalue()) if buf.getvalue().strip() else {}
    return code, output


def _write_transcript(transcript_path: Path, requests: list[str]) -> None:
    """Write synthetic user turns with USER_REQUEST tags to transcript."""
    lines = []
    for req in requests:
        lines.append(
            json.dumps(
                {
                    "type": "USER_INPUT",
                    "content": f"<USER_REQUEST>\n{req}\n</USER_REQUEST>",
                }
            )
        )
    transcript_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def agy_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate hook state directory and set up AGY workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv(
        "ENGINEERING_PRINCIPLES_STATE_DIR", str(tmp_path / "state")
    )
    monkeypatch.delenv("GROK_SESSION_ID", raising=False)
    monkeypatch.delenv("GROK_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("ENGINEERING_PRINCIPLES_HOOK", raising=False)
    monkeypatch.delenv("GROK_HOOK_EVENT", raising=False)
    return workspace


@pytest.mark.parametrize(
    (
        "scenario",
        "file_exists",
        "requests",
        "expected_decision",
        "expected_reason_clause",
    ),
    [
        (
            "existing_without_phrase_denies",
            True,
            ["Please update the file"],
            "deny",
            "201(d)",
        ),
        (
            "existing_with_phrase_in_current_turn_allows",
            True,
            ["I allow full overwrite on existing.txt"],
            "allow",
            None,
        ),
        (
            "existing_with_phrase_in_prior_turn_only_denies",
            True,
            [
                "turn 1: allow full overwrite",
                "turn 2: please overwrite it now",
            ],
            "deny",
            "201(d)",
        ),
        (
            "brand_new_path_allows",
            False,
            [],
            "allow",
            None,
        ),
    ],
)
def test_agy_write_to_file_overwrite_gate(
    agy_workspace: Path,
    tmp_path: Path,
    scenario: str,
    file_exists: bool,
    requests: list[str],
    expected_decision: str,
    expected_reason_clause: str | None,
) -> None:
    """Verify write_to_file overwrite gate policies (§ 201(d)/(e))."""
    file = agy_workspace / "target.txt"
    if file_exists:
        file.write_text("initial content\n", encoding="utf-8")
    transcript = tmp_path / "transcript.jsonl"
    if requests:
        _write_transcript(transcript, requests)
    payload = _agy_payload(
        "write_to_file",
        {
            "TargetFile": str(file),
            "Overwrite": True,
            "CodeContent": "new content\n",
        },
        workspace_paths=[str(agy_workspace)],
        transcript_path=str(transcript),
    )
    _code, res = _run_pre_tool_use(payload)
    assert res.get("decision") == expected_decision
    if expected_reason_clause:
        assert expected_reason_clause in res.get("reason", "")


@pytest.mark.parametrize(
    (
        "scenario",
        "read_mode",
        "external_drift",
        "expected_decision",
        "expected_reason_clause",
    ),
    [
        (
            "uninspected_denies",
            None,
            False,
            "deny",
            "201(c)",
        ),
        (
            "partial_read_denies",
            "partial",
            False,
            "deny",
            "201(c)",
        ),
        (
            "full_read_clean_allows",
            "full",
            False,
            "allow",
            None,
        ),
        (
            "full_read_with_external_drift_denies",
            "full",
            True,
            "deny",
            "201(c)",
        ),
    ],
)
def test_agy_replace_file_content_read_gate(
    agy_workspace: Path,
    scenario: str,
    read_mode: str | None,
    external_drift: bool,
    expected_decision: str,
    expected_reason_clause: str | None,
) -> None:
    """Verify replace_file_content read-before-write invariants (§ 201(c))."""
    file = agy_workspace / "file.txt"
    file.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")
    if read_mode == "partial":
        view_payload = _agy_payload(
            "view_file",
            {"AbsolutePath": str(file), "StartLine": 1, "EndLine": 2},
            workspace_paths=[str(agy_workspace)],
        )
        intercept_post_tool_use(view_payload)
    elif read_mode == "full":
        view_payload = _agy_payload(
            "view_file",
            {"AbsolutePath": str(file)},
            workspace_paths=[str(agy_workspace)],
        )
        intercept_post_tool_use(view_payload)

    if external_drift:
        file.write_text("line 1 edited externally\n", encoding="utf-8")

    replace_payload = _agy_payload(
        "replace_file_content",
        {
            "TargetFile": str(file),
            "TargetContent": "line 1",
            "ReplacementContent": "new 1",
        },
        workspace_paths=[str(agy_workspace)],
    )
    _code, res = _run_pre_tool_use(replace_payload)
    assert res.get("decision") == expected_decision
    if expected_reason_clause:
        assert expected_reason_clause in res.get("reason", "")


def test_agy_allow_consecutive_replace_after_own_mutation(
    agy_workspace: Path,
) -> None:
    """Allow consecutive mutations when session successfully mutates."""
    file = agy_workspace / "file.txt"
    file.write_text("initial\n", encoding="utf-8")
    view_payload = _agy_payload(
        "view_file",
        {"AbsolutePath": str(file)},
        workspace_paths=[str(agy_workspace)],
    )
    intercept_post_tool_use(view_payload)
    file.write_text("mutated once\n", encoding="utf-8")
    post_payload = _agy_payload(
        "replace_file_content",
        {
            "TargetFile": str(file),
            "TargetContent": "initial",
            "ReplacementContent": "mutated once",
        },
        workspace_paths=[str(agy_workspace)],
    )
    intercept_post_tool_use(post_payload)
    second_payload = _agy_payload(
        "replace_file_content",
        {
            "TargetFile": str(file),
            "TargetContent": "mutated once",
            "ReplacementContent": "mutated twice",
        },
        workspace_paths=[str(agy_workspace)],
    )
    _code, res = _run_pre_tool_use(second_payload)
    assert res.get("decision") == "allow"


@pytest.mark.parametrize(
    ("scenario", "is_brain_dir"),
    [
        ("outside_workspace_exempt", False),
        ("artifact_directory_exempt", True),
    ],
)
def test_agy_boundary_exemptions(
    agy_workspace: Path,
    tmp_path: Path,
    scenario: str,
    is_brain_dir: bool,
) -> None:
    """Exempt artifactDirectoryPath and out-of-workspace paths."""
    if is_brain_dir:
        target_dir = tmp_path / "brain"
        target_dir.mkdir(parents=True, exist_ok=True)
        file = target_dir / "plan.md"
        file.write_text("plan\n", encoding="utf-8")
        payload = _agy_payload(
            "replace_file_content",
            {
                "TargetFile": str(file),
                "TargetContent": "plan",
                "ReplacementContent": "updated",
            },
            workspace_paths=[str(agy_workspace)],
        )
        payload["artifactDirectoryPath"] = str(target_dir)
    else:
        outside = tmp_path / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        payload = _agy_payload(
            "replace_file_content",
            {
                "TargetFile": str(outside),
                "TargetContent": "outside",
                "ReplacementContent": "changed",
            },
            workspace_paths=[str(agy_workspace)],
        )

    _code, res = _run_pre_tool_use(payload)
    assert res.get("decision") == "allow"
