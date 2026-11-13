"""Tests for the Antigravity (AGY) hook adapter and drift gate."""

from __future__ import annotations

import json
import subprocess
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest
from engineering_principles.config import MUTATING_TOOLS
from engineering_principles.config import READ_TOOLS
from engineering_principles.dispatch import intercept_post_tool_use
from engineering_principles.dispatch import intercept_pre_tool_use
from engineering_principles.dispatch import intercept_stop
from engineering_principles.payload import extract_command
from engineering_principles.payload import extract_file_path
from engineering_principles.payload import extract_new_text
from engineering_principles.payload import extract_prompt_text
from engineering_principles.payload import extract_tool_input
from engineering_principles.payload import load_old_text
from engineering_principles.payload import normalize_tool
from engineering_principles.state import extract_session_id
from engineering_principles.state import load_state
from engineering_principles.state import persist_state
from engineering_principles.state import resolve_workspace_root
from engineering_principles.tdd_gate import find_tdd_stop_block_reason
from engineering_principles.tdd_gate import find_tdd_write_deny_reason
from engineering_principles.tdd_gate import is_git_dirty_path
from engineering_principles.tdd_gate import is_scaffolding_only_text
from engineering_principles.tdd_gate import is_tdd_production_path
from engineering_principles.tdd_gate import is_tdd_test_path
from engineering_principles.tdd_gate import record_tdd_post_tool
from engineering_principles.tdd_gate import record_tdd_prompt_authorization


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


@pytest.mark.parametrize(
    ("tool_name", "tool_args"),
    [
        (
            "write_to_file",
            {
                "CodeContent": (
                    "TABLE = {'title_contains':"
                    " 'collection://12345678-1234-1234-1234-123456789abc'}\n"
                ),
                "Overwrite": True,
            },
        ),
        (
            "replace_file_content",
            {
                "TargetContent": "pass",
                "ReplacementContent": (
                    "TABLE = {'title_contains':"
                    " 'collection://12345678-1234-1234-1234-123456789abc'}\n"
                ),
            },
        ),
        (
            "multi_replace_file_content",
            {
                "ReplacementChunks": [
                    {
                        "TargetContent": "pass",
                        "ReplacementContent": (
                            "TABLE = {'title_contains':"
                            " 'collection://12345678-1234-1234-1234-123456789abc'}\n"
                        ),
                    }
                ],
            },
        ),
    ],
)
def test_agy_skill_module_stateless_denial(
    agy_workspace: Path,
    tool_name: str,
    tool_args: dict,
) -> None:
    """Deny stateful content when AGY tools write to skill modules."""
    skill_dir = agy_workspace / "skills" / "skill-module-test" / "scripts"
    skill_dir.mkdir(parents=True, exist_ok=True)
    target = skill_dir / "tool.py"
    target.write_text("pass\n", encoding="utf-8")

    view_payload = _agy_payload(
        "view_file",
        {"AbsolutePath": str(target)},
        workspace_paths=[str(agy_workspace)],
    )
    intercept_post_tool_use(view_payload)

    args = dict(tool_args)
    args["TargetFile"] = str(target)
    payload = _agy_payload(
        tool_name,
        args,
        workspace_paths=[str(agy_workspace)],
    )
    payload["prompt"] = "allow full overwrite"
    code, res = _run_pre_tool_use(payload)
    assert code == 0
    assert res.get("decision") == "deny"
    assert "a module MUST be stateless" in res.get("reason", "")


def test_main_pre_tool_use_exception_uses_resolved_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Main delegates exit code selection to _resolve_pre_tool_exit_code."""
    from engineering_principles.dispatch import main

    payload = _agy_payload(
        "write_to_file",
        {"TargetFile": "/workspace/main.py", "CodeContent": "boom"},
    )
    monkeypatch.setattr(
        "engineering_principles.dispatch.dispatch",
        lambda _p: (_ for _ in ()).throw(
            RuntimeError("simulated dispatch error")
        ),
    )
    monkeypatch.setenv("GROK_HOOK_EVENT", "PreToolUse")
    monkeypatch.setattr("sys.stdin", StringIO(json.dumps(payload)))
    code = main()
    assert code == 0
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res.get("decision") == "deny"
    assert "hook error while evaluating a write" in res.get("reason", "")


def test_config_antigravity2_tools_registered_in_tool_sets() -> None:
    """AGY 2.0 tool names writefile, editfile in MUTATING, readfile in READ."""
    assert {"writefile", "editfile"}.issubset(MUTATING_TOOLS)
    assert "readfile" in READ_TOOLS


def test_normalize_tool_read_file_returns_readfile() -> None:
    """Normalize tool name read_file to readfile."""
    payload = _agy_payload("read_file", {"Path": "/workspace/README.md"})
    assert normalize_tool(payload) == "readfile"


def test_extract_file_path_read_file_returns_path_field() -> None:
    """Extract Path parameter from Antigravity 2.0 read_file tool input."""
    payload = _agy_payload("read_file", {"Path": "/workspace/README.md"})
    tool_input = extract_tool_input(payload)
    assert extract_file_path(tool_input) == "/workspace/README.md"


def test_extract_new_text_write_file_returns_content_field() -> None:
    """Extract Content parameter from Antigravity 2.0 write_file tool input."""
    payload = _agy_payload(
        "write_file", {"Path": "/workspace/main.py", "Content": "print(1)\n"}
    )
    tool_input = extract_tool_input(payload)
    assert extract_file_path(tool_input) == "/workspace/main.py"
    assert extract_new_text(tool_input) == "print(1)\n"


def test_extract_new_text_edit_file_returns_replacement_field() -> None:
    """Extract Replacement parameter from edit_file tool input."""
    payload = _agy_payload(
        "edit_file",
        {
            "Path": "/workspace/main.py",
            "Target": "old",
            "Replacement": "new",
        },
    )
    tool_input = extract_tool_input(payload)
    assert extract_file_path(tool_input) == "/workspace/main.py"
    assert extract_new_text(tool_input) == "new"
    assert load_old_text(tool_input, "/workspace/main.py") == "old"


@pytest.mark.parametrize(
    ("raw_input", "expected_extracted"),
    [
        ("<USER_REQUEST>\n請更新檔案\n</USER_REQUEST>", "請更新檔案"),
        (
            "<USER_REQUEST>\nPlease update the file\n</USER_REQUEST>",
            "Please update the file",
        ),
        (
            "plain English prompt without tags",
            "plain English prompt without tags",
        ),
    ],
)
def test_extract_prompt_text_last_user_input_returns_clean_request(
    raw_input: str, expected_extracted: str
) -> None:
    """Extract lastUserInput from payload and strip tags in any language."""
    payload = {"lastUserInput": raw_input}
    assert extract_prompt_text(payload) == expected_extracted


@pytest.mark.parametrize(
    (
        "scenario",
        "file_exists",
        "append_mode",
        "requests",
        "expected_decision",
        "expected_reason_clause",
    ),
    [
        (
            "existing_without_phrase_denies",
            True,
            False,
            ["Please update the file"],
            "deny",
            "201(d)",
        ),
        (
            "existing_with_phrase_allows",
            True,
            False,
            ["allow full overwrite on target.txt"],
            "allow",
            None,
        ),
        (
            "brand_new_path_allows",
            False,
            False,
            [],
            "allow",
            None,
        ),
    ],
)
def test_evaluate_write_file_overwrite_gate_enforces_verdict(
    agy_workspace: Path,
    tmp_path: Path,
    scenario: str,
    file_exists: bool,
    append_mode: bool,
    requests: list[str],
    expected_decision: str,
    expected_reason_clause: str | None,
) -> None:
    """Verify write_file overwrite gate policies (§ 201(d)/(e))."""
    file = agy_workspace / "target.txt"
    if file_exists:
        file.write_text("initial content\n", encoding="utf-8")
    transcript = tmp_path / "transcript.jsonl"
    if requests:
        _write_transcript(transcript, requests)
    payload = _agy_payload(
        "write_file",
        {
            "Path": str(file),
            "Overwrite": True,
            "Append": append_mode,
            "Content": "new content\n",
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
            "partial_read_with_byte_offset_denies",
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
def test_evaluate_edit_file_read_gate_enforces_verdict(
    agy_workspace: Path,
    scenario: str,
    read_mode: str | None,
    external_drift: bool,
    expected_decision: str,
    expected_reason_clause: str | None,
) -> None:
    """Verify edit_file read-before-write invariants (§ 201(c))."""
    file = agy_workspace / "file.txt"
    file.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")
    if read_mode == "partial":
        read_payload = _agy_payload(
            "read_file",
            {"Path": str(file), "ByteOffset": 10},
            workspace_paths=[str(agy_workspace)],
        )
        intercept_post_tool_use(read_payload)
    elif read_mode == "full":
        read_payload = _agy_payload(
            "read_file",
            {"Path": str(file)},
            workspace_paths=[str(agy_workspace)],
        )
        intercept_post_tool_use(read_payload)

    if external_drift:
        file.write_text("line 1 edited externally\n", encoding="utf-8")

    edit_payload = _agy_payload(
        "edit_file",
        {
            "Path": str(file),
            "Target": "line 1",
            "Replacement": "new 1",
        },
        workspace_paths=[str(agy_workspace)],
    )
    _code, res = _run_pre_tool_use(edit_payload)
    assert res.get("decision") == expected_decision
    if expected_reason_clause:
        assert expected_reason_clause in res.get("reason", "")


def test_evaluate_skill_module_stateless_edit_file_flags_violation(
    agy_workspace: Path,
) -> None:
    """Deny stateful content when edit_file writes to a skill module."""
    skill_dir = agy_workspace / "skills" / "skill-module-test" / "scripts"
    skill_dir.mkdir(parents=True, exist_ok=True)
    target = skill_dir / "tool.py"
    target.write_text("pass\n", encoding="utf-8")

    read_payload = _agy_payload(
        "read_file",
        {"Path": str(target)},
        workspace_paths=[str(agy_workspace)],
    )
    intercept_post_tool_use(read_payload)

    edit_payload = _agy_payload(
        "edit_file",
        {
            "Path": str(target),
            "Target": "pass",
            "Replacement": "HOME = '/home/alice/data'\n",
        },
        workspace_paths=[str(agy_workspace)],
    )
    code, res = _run_pre_tool_use(edit_payload)
    assert code == 0
    assert res.get("decision") == "deny"
    assert "a module MUST be stateless" in res.get("reason", "")


def test_dispatch_intercept_stop_under_antigravity_returns_continue_decision(
    agy_workspace: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Stop hook blocks under AGY with decision continue and exit code 0."""
    skill_dir = agy_workspace / "skills" / "skill-module-test" / "scripts"
    skill_dir.mkdir(parents=True, exist_ok=True)
    target = skill_dir / "tool.py"
    target.write_text("HOME = '/home/alice/data'\n", encoding="utf-8")

    post_payload = _agy_payload(
        "write_file",
        {"Path": str(target), "Content": "HOME = '/home/alice/data'\n"},
        workspace_paths=[str(agy_workspace)],
    )
    intercept_post_tool_use(post_payload)

    stop_payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    code = intercept_stop(stop_payload)
    assert code == 0
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res.get("decision") == "continue"
    assert "MUST be stateless" in res.get("reason", "")


def test_is_tdd_test_path_matching_patterns_returns_true() -> None:
    """Return True for test file paths matching TDD test patterns."""
    assert is_tdd_test_path("tests/test_foo.py") is True
    assert is_tdd_test_path("pkg/service_test.go") is True
    assert is_tdd_test_path("src/components/button.test.ts") is True
    assert is_tdd_test_path("src/components/button.spec.tsx") is True


def test_is_tdd_test_path_non_matching_patterns_returns_false() -> None:
    """Return False for production and configuration paths."""
    assert is_tdd_test_path("src/components/button.tsx") is False
    assert is_tdd_test_path("pkg/service.go") is False
    assert is_tdd_test_path("lib/core.py") is False
    assert is_tdd_test_path("pyproject.toml") is False


def test_is_tdd_production_path_source_files_returns_true(
    tmp_path: Path,
) -> None:
    """Return True for production source files under workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    prod_file = workspace / "core.py"
    prod_file.write_text("x = 1\n", encoding="utf-8")
    assert is_tdd_production_path(str(prod_file), workspace) is True


def test_is_tdd_production_path_test_and_doc_files_returns_false(
    tmp_path: Path,
) -> None:
    """Return False for test files, doc files, and type definition files."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    test_file = workspace / "tests" / "test_core.py"
    assert is_tdd_production_path(str(test_file), workspace) is False
    doc_file = workspace / "README.md"
    assert is_tdd_production_path(str(doc_file), workspace) is False
    dts_file = workspace / "types.d.ts"
    assert is_tdd_production_path(str(dts_file), workspace) is False


def test_is_scaffolding_only_text_empty_stubs_returns_true() -> None:
    """Return True for empty function stubs and type declarations."""
    stub_python = "def compute_total(x: int) -> int:\n    pass\n"
    assert is_scaffolding_only_text(stub_python) is True
    stub_raises = (
        "def compute_total(x: int) -> int:\n    raise NotImplementedError\n"
    )
    assert is_scaffolding_only_text(stub_raises) is True


def test_is_scaffolding_only_text_business_logic_returns_false() -> None:
    """Return False for control flow and algorithmic implementation."""
    logic = (
        "def compute_total(x: int) -> int:\n"
        "    if x > 10:\n"
        "        return x * 2\n"
        "    return x\n"
    )
    assert is_scaffolding_only_text(logic) is False


def test_find_tdd_write_deny_reason_red_pending_without_auth_denies_logic_write(
    agy_workspace: Path,
) -> None:
    """Deny non-scaffolding writes when in red_pending_verification stage."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "red_pending_verification"
    persist_state(payload, state)

    prod_file = agy_workspace / "service.py"
    prod_file.write_text("# existing\n", encoding="utf-8")
    logic_code = "def calc():\n    return 42\n"
    reason = find_tdd_write_deny_reason(payload, str(prod_file), logic_code)
    assert reason is not None
    assert "202(a)(1)" in reason


def test_find_tdd_write_deny_reason_red_pending_allows_scaffolding_stub(
    agy_workspace: Path,
) -> None:
    """Allow scaffolding stub writes in red_pending_verification stage."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "red_pending_verification"
    persist_state(payload, state)

    prod_file = agy_workspace / "service.py"
    prod_file.write_text("# existing\n", encoding="utf-8")
    stub_code = "def calc():\n    pass\n"
    reason = find_tdd_write_deny_reason(payload, str(prod_file), stub_code)
    assert reason is None


def test_find_tdd_write_deny_reason_green_authorized_allows_logic_write(
    agy_workspace: Path,
) -> None:
    """Allow business logic writes when stage is green_authorized."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "green_authorized"
    persist_state(payload, state)

    prod_file = agy_workspace / "service.py"
    prod_file.write_text("# existing\n", encoding="utf-8")
    logic_code = "def calc():\n    return 42\n"
    reason = find_tdd_write_deny_reason(payload, str(prod_file), logic_code)
    assert reason is None


def test_find_tdd_stop_block_reason_red_pending_verification_blocks_stop(
    agy_workspace: Path,
) -> None:
    """Block Stop when modified tests have not been executed."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "red_pending_verification"
    state["tdd_modified_tests"] = ["tests/test_foo.py"]
    persist_state(payload, state)

    reason = find_tdd_stop_block_reason(payload)
    assert reason is not None
    assert "202(b)(1)" in reason


def test_find_tdd_stop_block_reason_premature_green_execution_blocks_stop(
    agy_workspace: Path,
) -> None:
    """Block Stop when tests pass without prior failure (premature green)."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "premature_green"
    persist_state(payload, state)

    reason = find_tdd_stop_block_reason(payload)
    assert reason is not None
    assert "202(b)(4)" in reason


def test_find_tdd_stop_block_reason_red_verified_without_lint_blocks_stop(
    agy_workspace: Path,
) -> None:
    """Block Stop when failing tests are verified but linter has not passed."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "red_verified"
    state["tdd_lint_verified"] = False
    persist_state(payload, state)

    reason = find_tdd_stop_block_reason(payload)
    assert reason is not None
    assert "202(d)" in reason


def test_find_tdd_stop_block_reason_red_verified_with_lint_returns_none(
    agy_workspace: Path,
) -> None:
    """Allow Stop when tests failed with assertion and linter passed."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "red_verified"
    state["tdd_lint_verified"] = True
    persist_state(payload, state)

    reason = find_tdd_stop_block_reason(payload)
    assert reason is None


def test_find_tdd_stop_block_reason_green_authorized_without_tests_blocks_stop(
    agy_workspace: Path,
) -> None:
    """Block Stop in green stage when production mutated but tests unpassed."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "green_authorized"
    state["tdd_prod_mutated_in_green"] = True
    state["tdd_tests_passed_in_green"] = False
    persist_state(payload, state)

    reason = find_tdd_stop_block_reason(payload)
    assert reason is not None
    assert "202(e)" in reason


def test_find_tdd_stop_block_reason_green_with_tests_and_lint_returns_none(
    agy_workspace: Path,
) -> None:
    """Allow Stop in green stage when both tests and linter passed."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "green_authorized"
    state["tdd_prod_mutated_in_green"] = True
    state["tdd_tests_passed_in_green"] = True
    state["tdd_lint_verified"] = True
    persist_state(payload, state)

    reason = find_tdd_stop_block_reason(payload)
    assert reason is None


def test_record_tdd_post_tool_test_mutation_transitions_stage_to_red_pending(
    agy_workspace: Path,
) -> None:
    """Transition stage to red_pending when test file is mutated."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    record_tdd_post_tool(
        payload, "editfile", str(agy_workspace / "tests/test_x.py"), ""
    )
    state = load_state(payload)
    assert state.get("tdd_stage") == "red_pending_verification"
    assert "tests/test_x.py" in str(state.get("tdd_modified_tests", []))


@pytest.mark.parametrize(
    "phrase",
    [
        "測試已經通過紅燈，可以轉綠",
        "proceed to green",
        "authorize green now",
    ],
)
def test_record_tdd_prompt_authorization_green_phrase_advances_stage_to_green(
    agy_workspace: Path,
    phrase: str,
) -> None:
    """Advance tdd_stage to green_authorized on prompt authorization phrase."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "red_verified"
    persist_state(payload, state)

    record_tdd_prompt_authorization(payload, phrase)
    updated = load_state(payload)
    assert updated.get("tdd_stage") == "green_authorized"


def test_is_scaffolding_only_text_docstring_with_keywords_returns_true() -> (
    None
):
    """Docstrings containing control keywords remain valid scaffolding stubs."""
    stub = (
        "def calculate_tax(amount: int) -> int:\n"
        '    """Compute tax for the given case and return amount."""\n'
        "    pass\n"
    )
    assert is_scaffolding_only_text(stub) is True


def test_find_tdd_write_deny_reason_premature_green_denies_logic_write(
    agy_workspace: Path,
) -> None:
    """Deny non-scaffolding writes when in premature_green stage."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "premature_green"
    persist_state(payload, state)

    prod_file = agy_workspace / "service.py"
    prod_file.write_text("# existing\n", encoding="utf-8")
    logic_code = "def calc():\n    return 42\n"
    reason = find_tdd_write_deny_reason(payload, str(prod_file), logic_code)
    assert reason is not None
    assert "202(a)(1)" in reason


def test_record_tdd_green_stage_order_independent_completion(
    agy_workspace: Path,
) -> None:
    """Linter before test runner also resets green stage to idle."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "green_authorized"
    state["tdd_prod_mutated_in_green"] = True
    persist_state(payload, state)

    # Linter runs first
    record_tdd_post_tool(payload, "runcommand", "", "ruff check .")
    mid_state = load_state(payload)
    assert mid_state["tdd_stage"] == "green_authorized"
    assert mid_state["tdd_lint_verified"] is True

    # Test runner runs second
    record_tdd_post_tool(payload, "runcommand", "", "pytest")
    final_state = load_state(payload)
    assert final_state["tdd_stage"] == "idle"
    assert final_state["tdd_modified_tests"] == []


def test_record_tdd_green_stage_requires_prod_mutation_before_idle(
    agy_workspace: Path,
) -> None:
    """Tests and linter before prod mutation do not reset stage to idle."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "green_authorized"
    state["tdd_prod_mutated_in_green"] = False
    persist_state(payload, state)

    record_tdd_post_tool(payload, "runcommand", "", "pytest")
    record_tdd_post_tool(payload, "runcommand", "", "ruff check .")
    updated = load_state(payload)
    assert updated["tdd_stage"] == "green_authorized"


def test_record_tdd_test_and_linter_failure_resets_pass_flags() -> None:
    """Subsequent test or linter failure resets green verified flags."""
    from engineering_principles.tdd_gate import record_tdd_linter
    from engineering_principles.tdd_gate import record_tdd_test_runner

    state = {
        "tdd_stage": "green_authorized",
        "tdd_tests_passed_in_green": True,
        "tdd_lint_verified": True,
    }
    record_tdd_test_runner(state, "green_authorized", has_error=True)
    assert state["tdd_tests_passed_in_green"] is False

    record_tdd_linter(state, "green_authorized", has_error=True)
    assert state["tdd_lint_verified"] is False


def test_intercept_post_tool_use_transcript_nonzero_exit_marks_red_verified(
    agy_workspace: Path,
    tmp_path: Path,
) -> None:
    """Detect failing run_command exit code from transcript without error."""
    test_file = agy_workspace / "tests" / "test_sample.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_x():\n    assert False\n", encoding="utf-8")

    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "step_index": 5,
                "type": "PLANNER_RESPONSE",
                "status": "DONE",
                "tool_calls": [
                    {
                        "name": "run_command",
                        "args": {"CommandLine": "uv run pytest -q"},
                    }
                ],
            }
        )
        + "\n"
        + json.dumps(
            {
                "step_index": 6,
                "type": "GENERIC",
                "status": "DONE",
                "content": (
                    "Command exited with code 1.\n\nCommand output:\n1 failed\n"
                ),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    edit_post = _agy_payload(
        "edit_file",
        {"Path": str(test_file)},
        workspace_paths=[str(agy_workspace)],
        transcript_path=str(transcript),
    )
    intercept_post_tool_use(edit_post)

    cmd_post = _agy_payload(
        "run_command",
        {"CommandLine": "uv run pytest -q"},
        workspace_paths=[str(agy_workspace)],
        transcript_path=str(transcript),
    )
    cmd_post["stepIdx"] = 5
    intercept_post_tool_use(cmd_post)

    updated = load_state(cmd_post)
    assert updated["tdd_stage"] == "red_verified"


def test_intercept_post_tool_use_transcript_nonzero_exit_keeps_green_unpassed(
    agy_workspace: Path,
    tmp_path: Path,
) -> None:
    """Do not mark green tests passed when transcript shows non-zero exit."""
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "step_index": 8,
                "type": "GENERIC",
                "status": "DONE",
                "content": (
                    "Command exited with code 1.\n\n"
                    "Command output:\n1 failed, 2 passed\n"
                ),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    payload = _agy_payload(
        "run_command",
        {"CommandLine": "uv run pytest -q"},
        workspace_paths=[str(agy_workspace)],
        transcript_path=str(transcript),
    )
    payload["stepIdx"] = 7
    state = load_state(payload)
    state["tdd_stage"] = "green_authorized"
    state["tdd_prod_mutated_in_green"] = True
    persist_state(payload, state)

    intercept_post_tool_use(payload)
    updated = load_state(payload)
    assert updated["tdd_tests_passed_in_green"] is False
    assert updated["tdd_stage"] == "green_authorized"


def test_record_tdd_post_tool_composite_and_chained_commands_track_components(
    agy_workspace: Path,
    tmp_path: Path,
) -> None:
    """Verify wrapper script lint flag and chained ruff failure isolation."""
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "step_index": 4,
                "type": "GENERIC",
                "status": "DONE",
                "content": (
                    "Command exited with code 1.\n\n"
                    "Command output:\nE501 Line too long (84 > 80)\n"
                ),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    payload = _agy_payload(
        "run_command",
        {"CommandLine": "uv run ruff check . && uv run pytest -q"},
        workspace_paths=[str(agy_workspace)],
        transcript_path=str(transcript),
    )
    payload["stepIdx"] = 3
    state = load_state(payload)
    state["tdd_stage"] = "red_pending_verification"
    persist_state(payload, state)

    intercept_post_tool_use(payload)
    after_ruff_err = load_state(payload)
    assert after_ruff_err["tdd_stage"] == "red_pending_verification"
    assert after_ruff_err["tdd_lint_verified"] is False

    state["tdd_stage"] = "green_authorized"
    state["tdd_prod_mutated_in_green"] = True
    state["tdd_lint_verified"] = False
    state["tdd_tests_passed_in_green"] = False
    persist_state(payload, state)

    record_tdd_post_tool(payload, "runcommand", "", "./pytest.sh")
    after_wrapper = load_state(payload)
    assert after_wrapper["tdd_lint_verified"] is True
    assert after_wrapper["tdd_stage"] == "idle"


def test_intercept_stop_user_canceled_allows_termination_without_continue(
    agy_workspace: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Allow immediate stop when terminationReason is USER_CANCELED."""
    payload = _agy_payload("", {}, workspace_paths=[str(agy_workspace)])
    state = load_state(payload)
    state["tdd_stage"] = "premature_green"
    persist_state(payload, state)

    stop_payload = {
        **_agy_payload("", {}, workspace_paths=[str(agy_workspace)]),
        "hookEventName": "Stop",
        "terminationReason": "USER_CANCELED",
    }
    code = intercept_stop(stop_payload)
    assert code == 0
    assert capsys.readouterr().out.strip() == ""


def test_intercept_stop_continuation_repeat_reason_breaks_loop(
    agy_workspace: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Allow stop when same block reason repeats under continuationActive."""
    from engineering_principles.dispatch import dispatch

    transcript = tmp_path / "transcript.jsonl"
    _write_transcript(transcript, ["Fix failing test"])

    base = _agy_payload(
        "",
        {},
        workspace_paths=[str(agy_workspace)],
        transcript_path=str(transcript),
    )
    state = load_state(base)
    state["tdd_stage"] = "premature_green"
    persist_state(base, state)

    first = {
        **base,
        "hookEventName": "Stop",
        "terminationReason": "NO_TOOL_CALL",
        "continuationActive": False,
    }
    assert intercept_stop(first) == 0
    first_out = json.loads(capsys.readouterr().out)
    assert first_out.get("decision") == "continue"

    second = {
        **base,
        "hookEventName": "Stop",
        "terminationReason": "NO_TOOL_CALL",
        "continuationActive": True,
    }
    assert intercept_stop(second) == 0
    assert capsys.readouterr().out.strip() == ""

    _write_transcript(transcript, ["Fix failing test", "Run again"])
    dispatch(
        {
            **base,
            "hookEventName": "PreInvocation",
            "lastUserInput": "<USER_REQUEST>\nRun again\n</USER_REQUEST>",
        }
    )
    third = {
        **base,
        "hookEventName": "Stop",
        "terminationReason": "NO_TOOL_CALL",
        "continuationActive": False,
    }
    assert intercept_stop(third) == 0
    third_out = json.loads(capsys.readouterr().out)
    assert third_out.get("decision") == "continue"


def test_is_git_dirty_path_nested_repo_clean_file_returns_false(
    tmp_path: Path,
) -> None:
    """Resolve nested git root cleanly when parent workspace is non-git."""
    parent_ws = tmp_path / "parent_ws"
    repo = parent_ws / "sub" / "repo"
    test_file = repo / "tests" / "test_demo.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)

    assert is_git_dirty_path(str(test_file), parent_ws) is False


@pytest.mark.parametrize(
    ("questions_arg", "expected_decision"),
    [
        (
            [
                {
                    "question": "是否授權進入綠燈階段？",
                    "options": ["授權轉綠（可以轉綠）", "維持紅燈"],
                }
            ],
            "deny",
        ),
        (
            [
                {
                    "question": "請確認設定檔案路徑為 dev 還是 staging？",
                    "options": ["dev", "staging"],
                }
            ],
            "allow",
        ),
    ],
)
def test_intercept_pre_tool_use_ask_question_green_solicitation_denies(
    agy_workspace: Path,
    questions_arg: list[dict],
    expected_decision: str,
) -> None:
    """Deny ask_question soliciting green authorization in non-idle TDD."""
    payload = _agy_payload(
        "ask_question",
        {"questions": questions_arg},
        workspace_paths=[str(agy_workspace)],
    )
    state = load_state(payload)
    state["tdd_stage"] = "red_verified"
    persist_state(payload, state)

    _code, res = _run_pre_tool_use(payload)
    assert res.get("decision") == expected_decision
    if expected_decision == "deny":
        assert "202" in res.get("reason", "")


@pytest.mark.parametrize(
    "prompt",
    [
        "對話框跳出的 prompt 不能取代「可以轉綠」的代理輸出",
        "不要轉綠",
        "現在可以轉綠嗎？",
        "do not proceed to green",
    ],
)
def test_record_tdd_prompt_authorization_non_affirmative_ignores_transition(
    agy_workspace: Path,
    tmp_path: Path,
    prompt: str,
) -> None:
    """Ignore negated, quoted, or interrogative mentions of green phrases."""
    transcript = tmp_path / "transcript.jsonl"
    _write_transcript(transcript, [prompt])
    payload = _agy_payload(
        "",
        {},
        workspace_paths=[str(agy_workspace)],
        transcript_path=str(transcript),
    )
    state = load_state(payload)
    state["tdd_stage"] = "red_verified"
    persist_state(payload, state)

    record_tdd_prompt_authorization(payload, prompt)
    assert load_state(payload)["tdd_stage"] == "red_verified"

    prod_file = agy_workspace / "service.py"
    prod_file.write_text("# prod\n", encoding="utf-8")
    deny_reason = find_tdd_write_deny_reason(
        payload, str(prod_file), "def run():\n    return 1\n"
    )
    assert deny_reason is not None


def test_find_tdd_write_deny_reason_consumed_auth_key_denies_second_cycle(
    agy_workspace: Path,
    tmp_path: Path,
) -> None:
    """Consumed green authorization must not auto-authorize a subsequent red."""
    transcript = tmp_path / "transcript.jsonl"
    _write_transcript(transcript, ["可以轉綠"])
    prod_file = agy_workspace / "service.py"
    prod_file.write_text("# prod\n", encoding="utf-8")
    test_file = agy_workspace / "tests" / "test_service.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        "def test_one():\n    assert False\n", encoding="utf-8"
    )

    payload = _agy_payload(
        "edit_file",
        {"Path": str(prod_file)},
        workspace_paths=[str(agy_workspace)],
        transcript_path=str(transcript),
    )
    state = load_state(payload)
    state["tdd_stage"] = "red_verified"
    persist_state(payload, state)

    assert (
        find_tdd_write_deny_reason(
            payload, str(prod_file), "def calc():\n    return 1\n"
        )
        is None
    )
    record_tdd_post_tool(payload, "editfile", str(prod_file), "")
    record_tdd_post_tool(payload, "runcommand", "", "pytest")
    record_tdd_post_tool(payload, "runcommand", "", "ruff check .")
    assert load_state(payload)["tdd_stage"] == "idle"

    record_tdd_post_tool(payload, "editfile", str(test_file), "")
    assert load_state(payload)["tdd_stage"] == "red_pending_verification"
    second_reason = find_tdd_write_deny_reason(
        payload, str(prod_file), "def calc2():\n    return 2\n"
    )
    assert second_reason is not None
    assert "202(a)(1)" in second_reason


def test_dispatch_pre_invocation_records_prompt_and_resets_stop_counter(
    agy_workspace: Path,
) -> None:
    """PreInvocation records last_prompt and clears prior stop_block_count."""
    from engineering_principles.dispatch import dispatch

    payload = {
        **_agy_payload("", {}, workspace_paths=[str(agy_workspace)]),
        "hookEventName": "PreInvocation",
        "lastUserInput": "<USER_REQUEST>\n請調整文件\n</USER_REQUEST>",
    }
    state = load_state(payload)
    state["stop_block_count"] = 2
    state["last_stop_block_reason"] = "prior reason"
    persist_state(payload, state)

    assert dispatch(payload) == 0
    updated = load_state(payload)
    assert updated["last_prompt"] == "請調整文件"
    assert updated["stop_block_count"] == 0


def test_load_command_outcome_handles_parallel_tool_calls_offset(
    tmp_path: Path,
) -> None:
    """Resolve GENERIC step beyond step_idx+1 when parallel calls occur."""
    from engineering_principles.payload import load_command_execution_outcome

    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "step_index": 10,
                        "type": "PLANNER_RESPONSE",
                        "tool_calls": [
                            {
                                "name": "read_file",
                                "arguments": {"Path": "/tmp/a.py"},
                            },
                            {
                                "name": "run_command",
                                "arguments": {
                                    "CommandLine": "uv run pytest tests/x.py"
                                },
                            },
                        ],
                    }
                ),
                json.dumps(
                    {
                        "step_index": 11,
                        "type": "GENERIC",
                        "status": "DONE",
                        "content": "Shown lines 1-10",
                    }
                ),
                json.dumps(
                    {
                        "step_index": 12,
                        "type": "GENERIC",
                        "status": "DONE",
                        "content": "Command exited with code 1.\n1 failed",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    payload = {
        **_agy_payload(
            "run_command",
            {"CommandLine": "uv run pytest tests/x.py"},
            transcript_path=str(transcript),
        ),
        "stepIdx": 10,
    }
    has_error, output_text = load_command_execution_outcome(payload)
    assert has_error is True
    assert "Command exited with code 1." in output_text


def test_load_command_outcome_matches_specific_parallel_run_command(
    tmp_path: Path,
) -> None:
    """Match the specific parallel run_command instead of taking the last."""
    from engineering_principles.payload import load_command_execution_outcome

    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "step_index": 20,
                        "type": "PLANNER_RESPONSE",
                        "tool_calls": [
                            {
                                "name": "run_command",
                                "arguments": {
                                    "CommandLine": "uv run ruff check ."
                                },
                            },
                            {
                                "name": "run_command",
                                "arguments": {
                                    "CommandLine": "uv run pytest tests/x.py"
                                },
                            },
                        ],
                    }
                ),
                json.dumps(
                    {
                        "step_index": 21,
                        "type": "GENERIC",
                        "status": "DONE",
                        "content": (
                            "Command exited with code 0.\nAll checks passed!"
                        ),
                    }
                ),
                json.dumps(
                    {
                        "step_index": 22,
                        "type": "GENERIC",
                        "status": "DONE",
                        "content": "Command exited with code 1.\n1 failed",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    lint_payload = {
        **_agy_payload(
            "run_command",
            {"CommandLine": "uv run ruff check ."},
            transcript_path=str(transcript),
        ),
        "stepIdx": 20,
    }
    lint_err, lint_out = load_command_execution_outcome(lint_payload)
    assert lint_err is False
    assert "All checks passed!" in lint_out

    test_payload = {
        **_agy_payload(
            "run_command",
            {"CommandLine": "uv run pytest tests/x.py"},
            transcript_path=str(transcript),
        ),
        "stepIdx": 20,
    }
    test_err, test_out = load_command_execution_outcome(test_payload)
    assert test_err is True
    assert "1 failed" in test_out


def test_pre_invocation_same_turn_preserves_stop_block_count(
    agy_workspace: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Same-turn PreInvocation continuations must not wipe stop_block_count."""
    from engineering_principles.dispatch import dispatch

    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"step_index": 1, "type": "USER_INPUT", "content": "測"})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.argv", ["ep"])
    test_file = agy_workspace / "tests" / "test_loop.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_x():\n    assert False\n", encoding="utf-8")

    pre_inv = {
        **_agy_payload("", {}, workspace_paths=[str(agy_workspace)]),
        "hookEventName": "PreInvocation",
        "transcriptPath": str(transcript),
        "lastUserInput": "測",
    }
    assert dispatch(pre_inv) == 0

    state = load_state(pre_inv)
    state["tdd_stage"] = "premature_green"
    state["tdd_modified_tests"] = [str(test_file)]
    persist_state(pre_inv, state)

    stop_first = {
        **_agy_payload("", {}, workspace_paths=[str(agy_workspace)]),
        "hookEventName": "Stop",
        "transcriptPath": str(transcript),
        "terminationReason": "NO_TOOL_CALL",
        "continuationActive": False,
    }
    assert dispatch(stop_first) == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "continue"
    assert load_state(pre_inv)["stop_block_count"] == 1

    # Antigravity fires PreInvocation again on the same turn before continuing.
    assert dispatch(pre_inv) == 0
    assert load_state(pre_inv)["stop_block_count"] == 1

    stop_second = {**stop_first, "continuationActive": True}
    assert dispatch(stop_second) == 0
    assert capsys.readouterr().out == ""

    transcript.write_text(
        transcript.read_text(encoding="utf-8")
        + json.dumps({"step_index": 5, "type": "USER_INPUT", "content": "新"})
        + "\n",
        encoding="utf-8",
    )
    pre_next = {**pre_inv, "lastUserInput": "新"}
    assert dispatch(pre_next) == 0
    assert load_state(pre_inv)["stop_block_count"] == 0


def test_load_command_outcome_reads_steps_output_when_transcript_unflushed(
    tmp_path: Path,
) -> None:
    """Fall back to .system_generated/steps/<idx>/output.txt before flush."""
    from engineering_principles.payload import load_command_execution_outcome

    sys_gen = tmp_path / ".system_generated"
    logs_dir = sys_gen / "logs"
    step_dir = sys_gen / "steps" / "101"
    logs_dir.mkdir(parents=True)
    step_dir.mkdir(parents=True)
    transcript = logs_dir / "transcript.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "step_index": 100,
                "type": "PLANNER_RESPONSE",
                "tool_calls": [
                    {
                        "name": "run_command",
                        "arguments": {"CommandLine": "uv run pytest"},
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (step_dir / "output.txt").write_text(
        "Command exited with code 1.\n1 failed\n", encoding="utf-8"
    )
    payload = {
        **_agy_payload(
            "run_command",
            {"CommandLine": "uv run pytest"},
            transcript_path=str(transcript),
        ),
        "stepIdx": 100,
    }
    has_error, output_text = load_command_execution_outcome(payload)
    assert has_error is True
    assert "Command exited with code 1." in output_text


def test_stop_reconciles_late_flushed_transcript_command_failure(
    agy_workspace: Path, tmp_path: Path
) -> None:
    """Reconcile pending command failure once transcript flushes before Stop."""
    from engineering_principles.dispatch import dispatch

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True)
    transcript = logs_dir / "transcript.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "step_index": 200,
                "type": "PLANNER_RESPONSE",
                "tool_calls": [
                    {
                        "name": "run_command",
                        "arguments": {
                            "CommandLine": "uv run pytest tests/a.py"
                        },
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    test_file = agy_workspace / "tests" / "test_a.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_a():\n    assert False\n", encoding="utf-8")

    post_tool = {
        **_agy_payload(
            "run_command",
            {"CommandLine": "uv run pytest tests/a.py"},
            workspace_paths=[str(agy_workspace)],
            transcript_path=str(transcript),
        ),
        "hookEventName": "PostToolUse",
        "stepIdx": 200,
    }
    state = load_state(post_tool)
    state["tdd_stage"] = "red_pending_verification"
    state["tdd_modified_tests"] = [str(test_file)]
    state["tdd_lint_verified"] = True
    persist_state(post_tool, state)

    # Step 201 not flushed yet during PostToolUse.
    assert dispatch(post_tool) == 0

    # Transcript receives step 201 before Stop runs.
    transcript.write_text(
        transcript.read_text(encoding="utf-8")
        + json.dumps(
            {
                "step_index": 201,
                "type": "GENERIC",
                "status": "DONE",
                "content": "Command exited with code 1.\n1 failed",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    stop_payload = {
        **_agy_payload(
            "",
            {},
            workspace_paths=[str(agy_workspace)],
            transcript_path=str(transcript),
        ),
        "hookEventName": "Stop",
        "terminationReason": "NO_TOOL_CALL",
    }
    assert find_tdd_stop_block_reason(stop_payload) is None
    assert load_state(stop_payload)["tdd_stage"] == "red_verified"


def test_record_tdd_command_ruff_format_failure_keeps_red_pending() -> None:
    """Format-check failure alone in chained cmd must not verify red tests."""
    from engineering_principles.tdd_gate import record_tdd_command

    state = {"tdd_stage": "red_pending_verification", "tdd_lint_verified": True}
    changed = record_tdd_command(
        state,
        "uv run ruff format --check . && uv run pytest",
        True,
        "red_pending_verification",
        output_text="1 file would be reformatted\n",
    )
    assert changed is True
    assert state["tdd_lint_verified"] is False
    assert state["tdd_stage"] == "red_pending_verification"
