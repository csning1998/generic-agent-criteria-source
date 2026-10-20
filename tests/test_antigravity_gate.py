"""Tests for the Antigravity gate-check hook adapter."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Callable

import pytest


def _load(name: str, rel_path: str):
    root = Path(__file__).resolve().parent.parent
    path = root / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate_check = _load(
    "antigravity_gate_check",
    "hooks/adapters/antigravity/gate-check.py",
)


def test_normalize_payload_maps_antigravity_tool_call() -> None:
    """Antigravity protojson fields must map onto unified envelope."""
    raw = {
        "toolCall": {
            "name": "run_command",
            "args": {"CommandLine": "git status"},
        },
        "conversationId": "session-123",
        "transcriptPath": "/tmp/transcript.jsonl",
    }
    normalized = gate_check.normalize_payload(raw)
    assert normalized["tool_name"] == "run_command"
    assert normalized["tool_input"]["command"] == "git status"
    assert normalized["session_id"] == "session-123"
    assert normalized["transcript_path"] == "/tmp/transcript.jsonl"


def test_load_transcript_events_and_extract_latest_prompt(
    tmp_path: Path,
) -> None:
    """Antigravity transcript.jsonl USER_INPUT events must be extracted."""
    transcript_file = tmp_path / "transcript.jsonl"
    lines = [
        {"type": "USER_INPUT", "source": "USER_EXPLICIT", "content": "舊指令"},
        {"type": "PLANNER_RESPONSE", "source": "MODEL", "content": "好的"},
        {
            "type": "USER_INPUT",
            "source": "USER_EXPLICIT",
            "content": "請執行 git status",
        },
    ]
    transcript_file.write_text(
        "\n".join(json.dumps(line) for line in lines),
        encoding="utf-8",
    )
    events = gate_check.load_transcript_events(str(transcript_file))
    assert len(events) == 3
    prompt = gate_check.extract_latest_user_prompt(events)
    assert prompt == "請執行 git status"


@pytest.mark.parametrize(
    ("func", "args", "expected_decision", "expected_reason_substrs"),
    [
        (
            gate_check.deny,
            ("Dangerous operation", "rule context"),
            "deny",
            ["Dangerous operation", "rule context"],
        ),
        (
            gate_check.allow,
            (),
            "allow",
            [],
        ),
        (
            gate_check.force_ask,
            ("Approval required",),
            "force_ask",
            ["Approval required"],
        ),
    ],
)
def test_decision_emitters_matrix(
    capsys: pytest.CaptureFixture[str],
    func: Callable,
    args: tuple,
    expected_decision: str,
    expected_reason_substrs: list[str],
) -> None:
    """Decision helpers must emit standardized Antigravity JSON decisions."""
    with pytest.raises(SystemExit) as exc:
        func(*args)
    assert exc.value.code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["decision"] == expected_decision
    for substr in expected_reason_substrs:
        assert substr in payload.get("reason", "")


@pytest.mark.parametrize(
    ("command", "expected_decision"),
    [
        ("sudo rm -rf /tmp/data", "deny"),
        ("rm -rf /", "deny"),
        ("git push --force origin main", "deny"),
        ("git push -f", "deny"),
    ],
)
def test_intercept_run_command_hard_deny_matrix(
    capsys: pytest.CaptureFixture[str],
    command: str,
    expected_decision: str,
) -> None:
    """Destructive commands must be hard denied immediately."""
    payload = {
        "tool_name": "run_command",
        "tool_input": {"command": command},
        "session_id": "test-session",
    }
    with pytest.raises(SystemExit) as exc:
        gate_check.intercept_run_command(payload, [])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["decision"] == expected_decision
