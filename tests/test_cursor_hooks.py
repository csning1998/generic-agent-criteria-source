"""Tests for the Cursor copy of Claude gate-check."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
from adapter_install.install import SPECS
from adapter_install.install import run_apply
from adapter_install.install import validate_dest_rel


def _load():
    root = Path(__file__).resolve().parent.parent
    path = root / "hooks" / "adapters" / "claude" / "gate-check.py"
    spec = importlib.util.spec_from_file_location("cursor_gate_check", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate_check = _load()


@pytest.fixture
def cursor_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cursor protocol is selected from the materialized hooks path."""
    monkeypatch.setattr(
        gate_check, "__file__", "/tmp/home/.cursor/hooks/gate-check.py"
    )


@pytest.fixture
def isolated_criteria(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """CRITERIA_DIR and STATE_DIR default to a live uid path under /tmp."""
    criteria = tmp_path / "criteria"
    references = criteria / "references"
    references.mkdir(parents=True)
    (criteria / "markdown.md").write_text(
        (
            "---\n"
            "id: markdown\n"
            "observables:\n"
            '    path_glob: ["*.md"]\n'
            "load:\n"
            "    - references/lang-md.md\n"
            "---\n"
        ),
        encoding="utf-8",
    )
    (references / "lang-md.md").write_text(
        "markdown L2 body\n", encoding="utf-8"
    )
    monkeypatch.setattr(gate_check, "CRITERIA_DIR", criteria)
    monkeypatch.setattr(gate_check, "STATE_DIR", tmp_path / "gate-state")
    return tmp_path


def test_normalize_maps_cursor_write_fields() -> None:
    """Cursor Write uses toolName, path, and contents."""
    mapped = gate_check.normalize_payload(
        {
            "conversation_id": "conv-1",
            "toolName": "Write",
            "arguments": {
                "path": "/tmp/note.md",
                "contents": "# Title\n",
            },
        }
    )
    assert mapped["tool_name"] == "Write"
    assert mapped["session_id"] == "conv-1"
    assert mapped["tool_input"]["file_path"] == "/tmp/note.md"
    assert mapped["tool_input"]["content"] == "# Title\n"


def test_cursor_protocol_denies_first_markdown_write(
    cursor_argv, isolated_criteria: Path, capsys
) -> None:
    """The first markdown Write is denied and load text is returned."""
    payload = gate_check.normalize_payload(
        {
            "conversation_id": "conv-1",
            "toolName": "Write",
            "arguments": {
                "path": str(isolated_criteria / "note.md"),
                "contents": "# Title\n",
            },
        }
    )
    with pytest.raises(SystemExit):
        gate_check.handle_edit_write(payload, gate_check.load_scenarios())
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "deny"
    assert "markdown L2 body" in out["agent_message"]


def test_cursor_protocol_allows_retry(
    cursor_argv, isolated_criteria: Path, capsys
) -> None:
    """A second markdown Write in the same session is allowed."""
    payload = gate_check.normalize_payload(
        {
            "conversation_id": "conv-1",
            "toolName": "StrReplace",
            "arguments": {
                "path": str(isolated_criteria / "note.md"),
                "old_string": "a",
                "new_string": "b",
            },
        }
    )
    scenarios = gate_check.load_scenarios()
    with pytest.raises(SystemExit):
        gate_check.handle_edit_write(payload, scenarios)
    capsys.readouterr()
    with pytest.raises(SystemExit):
        gate_check.handle_edit_write(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    assert out == {"permission": "allow"}


def test_apply_materializes_cursor_gate_files(tmp_path: Path) -> None:
    """Apply copies gate-check.py and hooks.json under the injected home."""
    home = tmp_path / "home"
    home.mkdir()
    assert run_apply(Path(__file__).resolve().parent.parent, home) == 0
    script = home / ".cursor" / "hooks" / "gate-check.py"
    config = home / ".cursor" / "hooks.json"
    source = (
        Path(__file__).resolve().parent.parent
        / "hooks"
        / "adapters"
        / "claude"
        / "gate-check.py"
    )
    assert script.read_bytes() == source.read_bytes()
    assert '"failClosed": true' in config.read_text(encoding="utf-8")
    assert not (home / ".cursor" / "settings.json").exists()


def test_cursor_protocol_ignores_relative_argv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User-hook argv `hooks/gate-check.py` still selects Cursor JSON."""
    monkeypatch.setattr(sys, "argv", ["hooks/gate-check.py"])
    monkeypatch.setattr(
        gate_check, "__file__", "/tmp/home/.cursor/hooks/gate-check.py"
    )
    assert gate_check.cursor_protocol() is True
    monkeypatch.setattr(
        gate_check, "__file__", "/tmp/home/.claude/hooks/gate-check.py"
    )
    assert gate_check.cursor_protocol() is False


def test_state_dir_uses_cursor_tree_when_unoverridden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unset STATE_DIR follows the materialized adapter, not argv."""
    monkeypatch.setattr(gate_check, "STATE_DIR", None)
    monkeypatch.setattr(sys, "argv", ["hooks/gate-check.py"])
    monkeypatch.setattr(
        gate_check, "__file__", "/tmp/home/.cursor/hooks/gate-check.py"
    )
    uid = os.getuid()
    assert gate_check.state_dir() == Path(f"/tmp/cursor-gate-state-{uid}")
    monkeypatch.setattr(
        gate_check, "__file__", "/tmp/home/.claude/hooks/gate-check.py"
    )
    assert gate_check.state_dir() == Path(f"/tmp/claude-gate-state-{uid}")


def test_cursor_hooks_json_is_allow_listed() -> None:
    """hooks.json is an installer dest. settings.json stays rejected."""
    validate_dest_rel(".cursor/hooks.json")
    validate_dest_rel(".cursor/hooks/gate-check.py")
    with pytest.raises(ValueError, match="dest not in allow-list"):
        validate_dest_rel(".cursor/settings.json")
    dests = {spec.dest for spec in SPECS}
    assert ".cursor/hooks.json" in dests
    assert ".cursor/hooks/gate-check.py" in dests
