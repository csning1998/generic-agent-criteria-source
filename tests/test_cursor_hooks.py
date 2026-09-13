"""Tests for the Cursor copy of Claude gate-check and post-write-review."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
from pathlib import Path

import pytest
from adapter_install.install import SPECS
from adapter_install.install import run_apply
from adapter_install.install import validate_dest_rel


def _load(name: str, rel_path: str):
    root = Path(__file__).resolve().parent.parent
    path = root / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate_check = _load("cursor_gate_check", "hooks/adapters/claude/gate-check.py")
post_write_review = _load(
    "cursor_post_write_review",
    "hooks/adapters/claude/post-write-review.py",
)


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


def test_match_path_prefers_specific_glob_over_broad_markdown() -> None:
    """A literal path_glob wins over a broader *.md glob."""
    scenarios = [
        {"id": "broad-md", "path_glob": ["*.md", "*.mdx"]},
        {
            "id": "narrow",
            "path_glob": ["exact-target.md", "alt-target.md", "*NESTED*"],
        },
    ]
    assert (
        gate_check.match_path(scenarios, "/repo/exact-target.md")["id"]
        == "narrow"
    )
    alt = gate_check.match_path(scenarios, "/repo/alt-target.md")
    assert alt["id"] == "narrow"
    nested = gate_check.match_path(scenarios, "/repo/prefix_NESTED_suffix.md")
    assert nested["id"] == "narrow"
    other = gate_check.match_path(scenarios, "/repo/other.md")
    assert other["id"] == "broad-md"


def test_match_path_prefers_tdd_glob_over_broad_python() -> None:
    """A TDD-style path_glob wins over a broader *.py glob."""
    scenarios = [
        {"id": "broad-py", "path_glob": ["*.py"]},
        {
            "id": "tdd",
            "path_glob": [
                "**/tests/**",
                "*_test.py",
                "*_test.go",
                "*.test.ts",
                "*.test.tsx",
                "*.spec.ts",
                "*.spec.tsx",
            ],
        },
    ]
    assert (
        gate_check.match_path(scenarios, "/repo/module_test.py")["id"] == "tdd"
    )
    assert (
        gate_check.match_path(scenarios, "/repo/module.py")["id"] == "broad-py"
    )
    assert (
        gate_check.match_path(scenarios, "/repo/widget.test.ts")["id"] == "tdd"
    )


NARROW_PATH_GLOB = (
    '    path_glob: ["exact-target.md", "alt-target.md", "*NESTED*"]\n'
)


@pytest.fixture
def specificity_gate_criteria(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Isolated criteria: one narrow path_glob and one broad *.md glob."""
    criteria = tmp_path / "criteria"
    references = criteria / "references"
    references.mkdir(parents=True)
    (criteria / "broad-md.md").write_text(
        (
            "---\n"
            "id: broad-md\n"
            "observables:\n"
            '    path_glob: ["*.md", "*.mdx"]\n'
            "load:\n"
            "    - references/broad-load.md\n"
            "---\n"
        ),
        encoding="utf-8",
    )
    (criteria / "narrow.md").write_text(
        (
            "---\n"
            "id: narrow\n"
            "observables:\n"
            f"{NARROW_PATH_GLOB}"
            "load:\n"
            "    - references/narrow-load-a.md\n"
            "    - references/narrow-load-b.md\n"
            "---\n"
        ),
        encoding="utf-8",
    )
    (references / "broad-load.md").write_text(
        "BROAD_LOAD_MARKER\n",
        encoding="utf-8",
    )
    (references / "narrow-load-a.md").write_text(
        "NARROW_LOAD_A_MARKER\n",
        encoding="utf-8",
    )
    (references / "narrow-load-b.md").write_text(
        "NARROW_LOAD_B_MARKER\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gate_check, "CRITERIA_DIR", criteria)
    monkeypatch.setattr(gate_check, "STATE_DIR", tmp_path / "gate-state")
    return tmp_path


@pytest.mark.parametrize(
    "filename",
    [
        "exact-target.md",
        "alt-target.md",
        "prefix_NESTED_suffix.md",
    ],
)
def test_cursor_gate_once_surfaces_narrow_scenario_load(
    cursor_argv,
    specificity_gate_criteria: Path,
    filename: str,
    capsys,
) -> None:
    """Narrow path_glob match denies with scenario load on first write."""
    target = specificity_gate_criteria / filename
    payload = gate_check.normalize_payload(
        {
            "conversation_id": f"conv-narrow-{filename}",
            "toolName": "Write",
            "arguments": {
                "path": str(target),
                "contents": "# title\n",
            },
        }
    )
    with pytest.raises(SystemExit):
        gate_check.handle_edit_write(payload, gate_check.load_scenarios())
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "deny"
    assert "NARROW_LOAD_A_MARKER" in out["agent_message"]
    assert "NARROW_LOAD_B_MARKER" in out["agent_message"]


def test_cursor_gate_once_broad_md_gets_broad_load_only(
    cursor_argv, specificity_gate_criteria: Path, capsys
) -> None:
    """A path matched only by *.md gets the broad scenario load."""
    scenarios = gate_check.load_scenarios()
    meta = gate_check.match_path(scenarios, "/repo/other.md")
    assert meta["id"] == "broad-md"
    target = specificity_gate_criteria / "other.md"
    payload = gate_check.normalize_payload(
        {
            "conversation_id": "conv-broad",
            "toolName": "Write",
            "arguments": {
                "path": str(target),
                "contents": "# title\n",
            },
        }
    )
    with pytest.raises(SystemExit):
        gate_check.handle_edit_write(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "deny"
    assert "BROAD_LOAD_MARKER" in out["agent_message"]
    assert "NARROW_LOAD_A_MARKER" not in out["agent_message"]


def test_apply_materializes_cursor_gate_files(tmp_path: Path) -> None:
    """Apply copies Cursor hook scripts and hooks.json under home."""
    home = tmp_path / "home"
    home.mkdir()
    root = Path(__file__).resolve().parent.parent
    assert run_apply(root, home) == 0
    hooks = home / ".cursor" / "hooks"
    gate = hooks / "gate-check.py"
    post = hooks / "post-write-review.py"
    stop = hooks / "stop-output-scan.py"
    skill = hooks / "skill-module-gate.py"
    config = home / ".cursor" / "hooks.json"
    assert (
        gate.read_bytes()
        == (
            root / "hooks" / "adapters" / "claude" / "gate-check.py"
        ).read_bytes()
    )
    assert (
        post.read_bytes()
        == (
            root / "hooks" / "adapters" / "claude" / "post-write-review.py"
        ).read_bytes()
    )
    assert (
        stop.read_bytes()
        == (
            root / "hooks" / "adapters" / "cursor" / "stop-output-scan.py"
        ).read_bytes()
    )
    assert (
        skill.read_bytes()
        == (
            root / "hooks" / "adapters" / "cursor" / "skill-module-gate.py"
        ).read_bytes()
    )
    config_text = config.read_text(encoding="utf-8")
    assert '"failClosed": true' in config_text
    assert '"postToolUse"' in config_text
    assert '"stop"' in config_text
    assert "post-write-review.py" in config_text
    assert "stop-output-scan.py" in config_text
    assert "skill-module-gate.py" in config_text
    assert not (home / ".cursor" / "settings.json").exists()


def test_cursor_hooks_json_is_allow_listed() -> None:
    """hooks.json is an installer dest. settings.json stays rejected."""
    validate_dest_rel(".cursor/hooks.json")
    validate_dest_rel(".cursor/hooks/gate-check.py")
    validate_dest_rel(".cursor/hooks/post-write-review.py")
    validate_dest_rel(".cursor/hooks/stop-output-scan.py")
    validate_dest_rel(".cursor/hooks/skill-module-gate.py")
    with pytest.raises(ValueError, match="dest not in allow-list"):
        validate_dest_rel(".cursor/settings.json")
    dests = {spec.dest for spec in SPECS}
    assert ".cursor/hooks.json" in dests
    assert ".cursor/hooks/gate-check.py" in dests
    assert ".cursor/hooks/post-write-review.py" in dests
    assert ".cursor/hooks/stop-output-scan.py" in dests
    assert ".cursor/hooks/skill-module-gate.py" in dests


def test_cursor_hooks_json_source_wires_pre_post_stop() -> None:
    """Repo hooks.json registers Pre, Post, Stop, and skill-module gate."""
    root = Path(__file__).resolve().parent.parent
    config = json.loads(
        (root / "hooks" / "adapters" / "cursor" / "hooks.json").read_text(
            encoding="utf-8"
        )
    )
    hooks = config["hooks"]
    assert hooks["preToolUse"][0]["failClosed"] is True
    assert "gate-check.py" in hooks["preToolUse"][0]["command"]
    assert any(
        "skill-module-gate.py" in entry["command"]
        for entry in hooks["preToolUse"]
    )
    assert hooks["postToolUse"][0]["failClosed"] is True
    assert "post-write-review.py" in hooks["postToolUse"][0]["command"]
    assert "stop-output-scan.py" in hooks["stop"][0]["command"]


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


@pytest.fixture
def cursor_post_write(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Materialized Cursor post-write-review path and isolated state dirs."""
    monkeypatch.setattr(
        post_write_review,
        "__file__",
        "/tmp/home/.cursor/hooks/post-write-review.py",
    )
    monkeypatch.setattr(post_write_review, "STATE_DIR", tmp_path / "post-state")
    criteria = tmp_path / "criteria"
    criteria.mkdir()
    monkeypatch.setattr(post_write_review, "CRITERIA_DIR", criteria)
    return post_write_review


def _cursor_context(stdout: str) -> str:
    """Cursor postToolUse must emit flat additional_context only."""
    body = json.loads(stdout)
    assert "hookSpecificOutput" not in body
    assert "additional_context" in body
    return body["additional_context"]


def test_emit_cursor_uses_additional_context(cursor_post_write, capsys) -> None:
    """Cursor postToolUse returns flat additional_context only."""
    cursor_post_write.emit("register finding")
    assert _cursor_context(capsys.readouterr().out) == "register finding"


def test_post_write_normalize_maps_cursor_write_fields(
    cursor_post_write,
) -> None:
    """Post-write accepts the same Cursor Write aliases as gate-check."""
    mapped = cursor_post_write.normalize_payload(
        {
            "conversation_id": "conv-1",
            "toolName": "Write",
            "arguments": {
                "path": "/tmp/sample.py",
                "contents": "x = 1\n",
            },
        }
    )
    assert mapped["tool_name"] == "Write"
    assert mapped["session_id"] == "conv-1"
    assert mapped["tool_input"]["file_path"] == "/tmp/sample.py"
    assert mapped["tool_input"]["content"] == "x = 1\n"


def test_post_write_flags_register_on_cursor_write_envelope(
    cursor_post_write, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Cursor Write maps onto the same register pass Claude Post uses."""
    bare = "it"
    target = tmp_path / "sample.py"
    contents = "# " + bare + " does something\nx = 1\n"
    target.write_text(contents)
    payload = cursor_post_write.normalize_payload(
        {
            "conversation_id": "conv-1",
            "toolName": "Write",
            "arguments": {
                "path": str(target),
                "contents": contents,
            },
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    cursor_post_write.main()
    context = _cursor_context(capsys.readouterr().out)
    assert "bare pronoun" in context
    assert "VIOLATION" in context


def test_post_write_flags_register_from_on_disk_after_str_replace(
    cursor_post_write, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """After StrReplace, register reads on-disk text, not new_string alone."""
    bare = "it"
    target = tmp_path / "sample.py"
    target.write_text("x = 1  # explains " + bare + "\n")
    payload = cursor_post_write.normalize_payload(
        {
            "conversation_id": "conv-1",
            "toolName": "StrReplace",
            "arguments": {
                "path": str(target),
                "old_string": "behavior",
                "new_string": bare,
            },
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    cursor_post_write.main()
    context = _cursor_context(capsys.readouterr().out)
    assert "bare pronoun" in context


@pytest.mark.parametrize("tool_name", ["Write", "StrReplace", "TabWrite"])
def test_post_write_accepts_cursor_write_tool_names(
    cursor_post_write,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
    tool_name: str,
) -> None:
    """Every Cursor write tool name runs the post-write register pass."""
    bare = "it"
    target = tmp_path / "sample.py"
    contents = "# " + bare + " does something\n"
    target.write_text(contents)
    payload = cursor_post_write.normalize_payload(
        {
            "conversation_id": "conv-1",
            "toolName": tool_name,
            "arguments": {
                "path": str(target),
                "contents": contents,
            },
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    cursor_post_write.main()
    assert "bare pronoun" in _cursor_context(capsys.readouterr().out)


def test_post_write_surfaces_scenario_load_on_clean_cursor_write(
    cursor_post_write, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Clean Cursor Write still gets scenario self-review context."""
    criteria = tmp_path / "criteria"
    references = criteria / "references"
    references.mkdir(parents=True, exist_ok=True)
    (criteria / "local-mutate.md").write_text(
        (
            "---\n"
            "id: local-mutate\n"
            "observables:\n"
            '    path_glob: ["*.py"]\n'
            "load:\n"
            "    - references/401-e-g_Style_and_Markings.md\n"
            "---\n"
        ),
        encoding="utf-8",
    )
    (references / "401-e-g_Style_and_Markings.md").write_text(
        "style L2 body\n", encoding="utf-8"
    )
    monkeypatch.setattr(cursor_post_write, "CRITERIA_DIR", criteria)
    target = tmp_path / "clean.py"
    contents = "# The pointer resolves to a value which the caller must free.\n"
    target.write_text(contents)
    payload = cursor_post_write.normalize_payload(
        {
            "conversation_id": "conv-1",
            "toolName": "Write",
            "arguments": {"path": str(target), "contents": contents},
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    cursor_post_write.main()
    context = _cursor_context(capsys.readouterr().out)
    assert "Post-write self-review" in context
    assert "style L2 body" in context


def test_post_write_state_dir_follows_cursor_hooks_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unset post-write STATE_DIR follows the Cursor materialized path."""
    monkeypatch.setattr(post_write_review, "STATE_DIR", None)
    monkeypatch.setattr(
        post_write_review,
        "__file__",
        "/tmp/home/.cursor/hooks/post-write-review.py",
    )
    uid = os.getuid()
    assert post_write_review.state_dir() == Path(
        f"/tmp/cursor-gate-state-{uid}"
    )


def test_cursor_pre_allows_bare_pronoun_comment(
    cursor_argv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Pre allows a bare-pronoun comment; Post register catches it after."""
    monkeypatch.setattr(gate_check, "STATE_DIR", tmp_path / "gate-state")
    monkeypatch.setattr(gate_check, "CRITERIA_DIR", tmp_path / "criteria")
    (tmp_path / "criteria").mkdir()
    target = tmp_path / "sample.py"
    target.write_text("result = calc()  # explains behavior\n")
    payload = gate_check.normalize_payload(
        {
            "conversation_id": "conv-1",
            "toolName": "StrReplace",
            "arguments": {
                "path": str(target),
                "old_string": "behavior",
                "new_string": "it",
            },
        }
    )
    with pytest.raises(SystemExit):
        gate_check.handle_edit_write(payload, scenarios=[])
    out = json.loads(capsys.readouterr().out)
    assert out == {"permission": "allow"}


def test_cursor_hard_denies_force_push(
    cursor_argv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Cursor Pre still hard-denies force push with no ask card."""
    monkeypatch.setattr(gate_check, "STATE_DIR", tmp_path / "gate-state")
    payload = {
        "session_id": "conv-1",
        "tool_input": {"command": "git push --force origin HEAD"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios=[])
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "deny"
    assert (
        "force" in out["user_message"].lower()
        or "force" in out["agent_message"].lower()
    )


def test_cursor_hard_denies_rm_rf(
    cursor_argv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Cursor Pre hard-denies rm -rf."""
    monkeypatch.setattr(gate_check, "STATE_DIR", tmp_path / "gate-state")
    payload = {
        "session_id": "conv-1",
        "tool_input": {"command": "rm -rf /tmp/demo"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios=[])
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "deny"


def test_cursor_denies_notebook_write(
    cursor_argv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Cursor Pre denies disk mutation of .ipynb."""
    monkeypatch.setattr(gate_check, "STATE_DIR", tmp_path / "gate-state")
    monkeypatch.setattr(gate_check, "CRITERIA_DIR", tmp_path / "criteria")
    (tmp_path / "criteria").mkdir()
    payload = gate_check.normalize_payload(
        {
            "conversation_id": "conv-1",
            "toolName": "Write",
            "arguments": {
                "path": str(tmp_path / "note.ipynb"),
                "contents": "{}",
            },
        }
    )
    with pytest.raises(SystemExit):
        gate_check.handle_edit_write(payload, scenarios=[])
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "deny"
    assert "notebook" in out["user_message"].lower()


@pytest.mark.parametrize(
    "tool_name",
    [
        "MCP: plugin-gitlab-GitLab-save_note",
        "MCP: plugin-gitlab-GitLab-create_issue",
        "MCP: plugin-gitlab-GitLab-accept_merge_request",
        "MCP: plugin-github-github-create_pull_request",
        "MCP: plugin-github-github-merge_pull_request",
        "MCP: plugin-github-github-add_issue_comment",
    ],
)
def test_cursor_mcp_write_markers_ask(
    cursor_argv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
    tool_name: str,
) -> None:
    """Named GitLab/GitHub MCP writes ask under Cursor when unauthorized."""
    monkeypatch.setattr(gate_check, "STATE_DIR", tmp_path / "gate-state")
    assert gate_check.is_cursor_mcp_external_write(tool_name) is True
    payload = {
        "session_id": "conv-1",
        "transcript_path": str(tmp_path / "missing-transcript.jsonl"),
    }
    with pytest.raises(SystemExit):
        gate_check.require_exec_phrase(payload, f"MCP tool '{tool_name}'")
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "ask"


def test_cursor_git_push_asks_without_phrase(
    cursor_argv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Git push (non-force) asks on Cursor without an execution phrase."""
    scenarios = _external_write_scenarios(tmp_path, monkeypatch)
    payload = {
        "session_id": "conv-1",
        "transcript_path": "",
        "tool_input": {"command": "git push origin HEAD"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "ask"


def _external_write_scenarios(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Install a minimal external-write scenario under CRITERIA_DIR."""
    criteria = tmp_path / "criteria"
    criteria.mkdir(parents=True, exist_ok=True)
    (criteria / "external-write.md").write_text(
        (
            "---\n"
            "id: external-write\n"
            "observables:\n"
            '    command_prefix: ["git ", "glab ", "gh "]\n'
            '    command_glob: ["glab api --method"]\n'
            '    readonly_command_glob: ["git status", "glab api projects"]\n'
            "load:\n"
            "    - references/"
            "301_Default_State_and_Authorization_Boundaries.md\n"
            "---\n"
        ),
        encoding="utf-8",
    )
    references = criteria / "references"
    references.mkdir(parents=True, exist_ok=True)
    (
        references / "301_Default_State_and_Authorization_Boundaries.md"
    ).write_text("external write L2\n", encoding="utf-8")
    monkeypatch.setattr(gate_check, "CRITERIA_DIR", criteria)
    monkeypatch.setattr(gate_check, "STATE_DIR", tmp_path / "gate-state")
    return gate_check.load_scenarios()


def _phrase_transcript(tmp_path: Path, phrase: str) -> Path:
    """Claude JSONL turn whose tool_result content is phrase."""
    path = tmp_path / f"transcript-{phrase}.jsonl"
    event = {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "content": phrase,
                }
            ]
        },
    }
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    return path


def _approve_transcript(tmp_path: Path) -> Path:
    """Claude JSONL turn whose tool_result label is Approve."""
    return _phrase_transcript(tmp_path, "Approve")


def test_cursor_glab_write_asks_without_transcript(
    cursor_argv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Cursor with no transcript asks via the native permission card."""
    scenarios = _external_write_scenarios(tmp_path, monkeypatch)
    payload = {
        "session_id": "conv-1",
        "transcript_path": str(tmp_path / "missing-transcript.jsonl"),
        "tool_input": {"command": "glab api --method POST projects/x/notes"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "ask"
    assert "external-write.md" in out["user_message"]
    assert "AskUserQuestion" not in out["user_message"]
    assert "AskUserQuestion" not in out.get("agent_message", "")


def test_cursor_glab_write_asks_on_empty_transcript_path(
    cursor_argv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """An empty transcript_path string must not read Path('.') as a file."""
    scenarios = _external_write_scenarios(tmp_path, monkeypatch)
    assert gate_check.last_user_message("") == ""
    payload = {
        "session_id": "conv-1",
        "transcript_path": "",
        "tool_input": {"command": "glab api --method POST projects/x/notes"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "ask"


def test_claude_glab_write_denies_without_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Claude without a phrase still denies and names AskUserQuestion."""
    monkeypatch.setattr(
        gate_check, "__file__", "/tmp/home/.claude/hooks/gate-check.py"
    )
    scenarios = _external_write_scenarios(tmp_path, monkeypatch)
    payload = {
        "session_id": "s1",
        "transcript_path": str(tmp_path / "missing-transcript.jsonl"),
        "tool_input": {"command": "glab api --method POST projects/x/notes"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    decision = out["hookSpecificOutput"]["permissionDecision"]
    assert decision == "deny"
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "AskUserQuestion" in reason
    assert out.get("permission") != "ask"


def test_cursor_deny_transcript_still_asks(
    cursor_argv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """A Deny tool_result label does not authorize an external write."""
    scenarios = _external_write_scenarios(tmp_path, monkeypatch)
    transcript = _phrase_transcript(tmp_path, "Deny")
    payload = {
        "session_id": "conv-1",
        "transcript_path": str(transcript),
        "tool_input": {"command": "glab api --method POST projects/x/notes"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "ask"


def test_claude_deny_transcript_still_denies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Claude Deny in the questionnaire still requires AskUserQuestion."""
    monkeypatch.setattr(
        gate_check, "__file__", "/tmp/home/.claude/hooks/gate-check.py"
    )
    scenarios = _external_write_scenarios(tmp_path, monkeypatch)
    transcript = _phrase_transcript(tmp_path, "Deny")
    payload = {
        "session_id": "s1",
        "transcript_path": str(transcript),
        "tool_input": {"command": "glab api --method POST projects/x/notes"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "AskUserQuestion" in reason


def test_cursor_glab_with_approve_transcript_reaches_gate_once(
    cursor_argv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """A Cursor transcript with Approve skips ask and hits gate_once."""
    scenarios = _external_write_scenarios(tmp_path, monkeypatch)
    transcript = _approve_transcript(tmp_path)
    payload = {
        "session_id": "conv-1",
        "transcript_path": str(transcript),
        "tool_input": {"command": "glab api --method POST projects/x/notes"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "deny"
    assert "external write L2" in out["agent_message"]
    assert out["permission"] != "ask"


def test_cursor_approve_second_call_allows(
    cursor_argv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """After Approve and the first gate_once deny, a retry is allowed."""
    scenarios = _external_write_scenarios(tmp_path, monkeypatch)
    transcript = _approve_transcript(tmp_path)
    payload = {
        "session_id": "conv-1",
        "transcript_path": str(transcript),
        "tool_input": {"command": "glab api --method POST projects/x/notes"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios)
    capsys.readouterr()
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    assert out == {"permission": "allow"}


def test_claude_approve_second_call_allows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Claude Approve plus gate_once retry allows on the second call."""
    monkeypatch.setattr(
        gate_check, "__file__", "/tmp/home/.claude/hooks/gate-check.py"
    )
    scenarios = _external_write_scenarios(tmp_path, monkeypatch)
    transcript = _approve_transcript(tmp_path)
    payload = {
        "session_id": "s1",
        "transcript_path": str(transcript),
        "tool_input": {"command": "glab api --method POST projects/x/notes"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios)
    capsys.readouterr()
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"


@pytest.mark.parametrize(
    "phrase",
    ["去執行", "跑這個", "請執行", "執行吧"],
)
def test_chinese_exec_phrase_authorizes_gate_once(
    cursor_argv,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
    phrase: str,
) -> None:
    """Chinese backup phrases authorize the same path as Approve."""
    scenarios = _external_write_scenarios(tmp_path, monkeypatch)
    transcript = _phrase_transcript(tmp_path, phrase)
    payload = {
        "session_id": "conv-1",
        "transcript_path": str(transcript),
        "tool_input": {"command": "glab api --method POST projects/x/notes"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "deny"
    assert "external write L2" in out["agent_message"]


def test_cursor_readonly_glab_allows_without_ask(
    cursor_argv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Readonly glab queries stay allow-listed under Cursor."""
    scenarios = _external_write_scenarios(tmp_path, monkeypatch)
    payload = {
        "session_id": "conv-1",
        "transcript_path": str(tmp_path / "missing-transcript.jsonl"),
        "tool_input": {"command": "glab api projects/x"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    assert out == {"permission": "allow"}


def test_cursor_mcp_save_note_asks(
    cursor_argv, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Cursor MCP GitLab note writes ask when no execution phrase is present."""
    monkeypatch.setattr(gate_check, "STATE_DIR", tmp_path / "gate-state")
    tool_name = "MCP: plugin-gitlab-GitLab-save_note"
    assert gate_check.is_cursor_mcp_external_write(tool_name) is True
    payload = {
        "session_id": "conv-1",
        "transcript_path": str(tmp_path / "missing-transcript.jsonl"),
    }
    with pytest.raises(SystemExit):
        gate_check.require_exec_phrase(payload, f"MCP tool '{tool_name}'")
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "ask"
    assert "AskUserQuestion" not in out["user_message"]


def test_claude_mcp_save_note_is_not_gated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claude leaves non-shell MCP tools outside the Cursor MCP gate."""
    monkeypatch.setattr(
        gate_check, "__file__", "/tmp/home/.claude/hooks/gate-check.py"
    )
    assert (
        gate_check.is_cursor_mcp_external_write(
            "MCP: plugin-gitlab-GitLab-save_note"
        )
        is False
    )


def test_cursor_mcp_marker_rejects_longer_token_prefix(
    cursor_argv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A longer tool id containing a marker as a prefix is not a write gate."""
    monkeypatch.setattr(
        gate_check, "__file__", "/tmp/home/.cursor/hooks/gate-check.py"
    )
    assert (
        gate_check.is_cursor_mcp_external_write("mcp__x__issue_write_lock")
        is False
    )
    assert (
        gate_check.is_cursor_mcp_external_write("mcp__github__issue_write")
        is True
    )


def test_cursor_register_flags_bare_so_without_modal() -> None:
    """401(d)/(f): spaced 'so' is banned even when no modal follows."""
    text = "# The hyphenated form is restored so path segments stay covered."
    violations = post_write_review.find_register_violations(text)
    assert any("bare escape-hatch 'so'" in v for v in violations)


def test_cursor_register_flags_md_bare_so_no_modal() -> None:
    """Markdown prose gets the same spaced-'so' ban via the virtual prefix."""
    text = "The hyphenated form is restored so path segments stay covered."
    violations = post_write_review.find_register_violations(
        text, is_markdown=True
    )
    assert any("bare escape-hatch 'so'" in v for v in violations)


def test_post_write_flags_register_on_markdown_prose(
    cursor_post_write, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Cursor Post scans markdown prose with the same register as Claude."""
    bare = "it"
    target = tmp_path / "note.md"
    contents = "Retrying " + bare + " fixes the flaky case.\n"
    target.write_text(contents, encoding="utf-8")
    payload = cursor_post_write.normalize_payload(
        {
            "conversation_id": "conv-md-prose",
            "toolName": "Write",
            "arguments": {"path": str(target), "contents": contents},
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    cursor_post_write.main()
    context = _cursor_context(capsys.readouterr().out)
    assert "bare pronoun 'it'" in context


def test_post_write_flags_register_on_markdown_heading(
    cursor_post_write, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """A markdown heading is prose and is scanned like any other line."""
    bare = "it"
    target = tmp_path / "note.md"
    contents = "# Retrying " + bare + " fixes the flaky case\n"
    target.write_text(contents, encoding="utf-8")
    payload = cursor_post_write.normalize_payload(
        {
            "conversation_id": "conv-md-heading",
            "toolName": "Write",
            "arguments": {"path": str(target), "contents": contents},
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    cursor_post_write.main()
    context = _cursor_context(capsys.readouterr().out)
    assert "bare pronoun 'it'" in context


def test_post_write_skips_markdown_frontmatter_register(
    cursor_post_write, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """YAML frontmatter stays outside the markdown register scan."""
    criteria = tmp_path / "criteria"
    references = criteria / "references"
    references.mkdir(parents=True, exist_ok=True)
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
    (references / "lang-md.md").write_text("md L2\n", encoding="utf-8")
    monkeypatch.setattr(cursor_post_write, "CRITERIA_DIR", criteria)
    bare = "it"
    target = tmp_path / "note.md"
    contents = "---\nid: " + bare + "\n---\nBody text is clean here.\n"
    target.write_text(contents, encoding="utf-8")
    payload = cursor_post_write.normalize_payload(
        {
            "conversation_id": "conv-md-fm",
            "toolName": "Write",
            "arguments": {"path": str(target), "contents": contents},
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    cursor_post_write.main()
    context = _cursor_context(capsys.readouterr().out)
    assert "bare pronoun 'it'" not in context
    assert "Post-write self-review" in context


def test_post_write_skips_markdown_fenced_code_register(
    cursor_post_write, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """A fenced code sample stays outside the markdown register scan."""
    criteria = tmp_path / "criteria"
    references = criteria / "references"
    references.mkdir(parents=True, exist_ok=True)
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
    (references / "lang-md.md").write_text("md L2\n", encoding="utf-8")
    monkeypatch.setattr(cursor_post_write, "CRITERIA_DIR", criteria)
    bare = "it"
    target = tmp_path / "note.md"
    contents = (
        "Body text is clean here.\n\n"
        "```python\n"
        "x = " + bare + "  # " + bare + " does something\n"
        "```\n"
    )
    target.write_text(contents, encoding="utf-8")
    payload = cursor_post_write.normalize_payload(
        {
            "conversation_id": "conv-md-fence",
            "toolName": "Write",
            "arguments": {"path": str(target), "contents": contents},
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    cursor_post_write.main()
    context = _cursor_context(capsys.readouterr().out)
    assert "bare pronoun 'it'" not in context
    assert "Post-write self-review" in context


def test_post_write_flags_escape_hatch_so_in_markdown(
    cursor_post_write, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Escape-hatch 'so' in markdown prose is a mechanical VIOLATION."""
    target = tmp_path / "merge-request.md"
    contents = "Register moves to PostToolUse so a write can land.\n"
    target.write_text(contents, encoding="utf-8")
    payload = cursor_post_write.normalize_payload(
        {
            "conversation_id": "conv-md-so",
            "toolName": "Write",
            "arguments": {"path": str(target), "contents": contents},
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    cursor_post_write.main()
    context = _cursor_context(capsys.readouterr().out)
    assert "VIOLATION" in context
    assert "so" in context.lower()


def test_emit_dedupes_identical_context(cursor_post_write, capsys) -> None:
    """A second identical Post emit in the same session prints nothing."""
    cursor_post_write.emit("same finding", session_id="conv-1")
    first = capsys.readouterr().out
    assert _cursor_context(first) == "same finding"
    cursor_post_write.emit("same finding", session_id="conv-1")
    assert capsys.readouterr().out == ""


def test_claim_emit_slot_is_exclusive(
    cursor_post_write, tmp_path: Path
) -> None:
    """Only the first O_EXCL claim wins when two Post fires race."""
    slot = tmp_path / "emit__race"
    assert cursor_post_write.claim_emit_slot(slot) is True
    assert cursor_post_write.claim_emit_slot(slot) is False


def test_stop_output_followup_on_em_dash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Cursor stop follow-up fires when last assistant text has an em dash."""
    stop = _load(
        "cursor_stop_output_scan",
        "hooks/adapters/cursor/stop-output-scan.py",
    )
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "role": "assistant",
                "message": {"content": "Done — shipped."},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "status": "completed",
                    "loop_count": 0,
                    "transcript_path": str(transcript),
                }
            )
        ),
    )
    stop.main()
    out = json.loads(capsys.readouterr().out)
    assert "followup_message" in out
    assert (
        "em dash" in out["followup_message"].lower()
        or "—" in out["followup_message"]
    )


def test_stop_output_silent_when_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Cursor stop stays quiet when the last assistant text is clean."""
    stop = _load(
        "cursor_stop_output_scan_clean",
        "hooks/adapters/cursor/stop-output-scan.py",
    )
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "role": "assistant",
                "message": {"content": "Done. Shipped the change."},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "status": "completed",
                    "loop_count": 0,
                    "transcript_path": str(transcript),
                }
            )
        ),
    )
    stop.main()
    assert capsys.readouterr().out.strip() in ("", "{}")


def test_stop_output_ignores_non_assistant_transcript_lines(
    tmp_path: Path,
) -> None:
    """User and tool lines do not become the scanned assistant span."""
    stop = _load(
        "cursor_stop_output_scan_roles",
        "hooks/adapters/cursor/stop-output-scan.py",
    )
    transcript = tmp_path / "t.jsonl"
    lines = [
        json.dumps(
            {"role": "user", "message": {"content": "Ban — in user text."}}
        ),
        json.dumps(
            {
                "type": "tool",
                "message": {"role": "tool", "content": "tool — output"},
            }
        ),
        json.dumps(
            {
                "type": "user",
                "message": {
                    "role": "assistant",
                    "content": "Nested assistant role still counts.",
                },
            }
        ),
    ]
    transcript.write_text("\n".join(lines) + "\n", encoding="utf-8")
    text = stop.last_assistant_text(str(transcript))
    assert "Nested assistant role still counts." in text
    assert "Ban" not in text
    assert stop.finding(text) is None


def test_skill_module_gate_denies_baked_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Cursor Pre denies a skill-module write that bakes an owner home path."""
    skill = _load(
        "cursor_skill_module_gate",
        "hooks/adapters/cursor/skill-module-gate.py",
    )
    target = tmp_path / "skill-module-demo" / "run.py"
    target.parent.mkdir()
    payload = {
        "hook_event_name": "preToolUse",
        "conversation_id": "conv-1",
        "toolName": "Write",
        "arguments": {
            "path": str(target),
            "contents": 'HOME = "/home/csning1998/data"\n',
        },
        "workspace_roots": [str(tmp_path)],
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    skill.main()
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "deny"
    assert (
        "skill-module" in out["agent_message"].lower()
        or "stateless" in out["agent_message"].lower()
    )


def test_skill_module_gate_allows_unrelated_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Cursor skill-module gate allows a write outside skill-module paths."""
    skill = _load(
        "cursor_skill_module_gate_allow",
        "hooks/adapters/cursor/skill-module-gate.py",
    )
    target = tmp_path / "src" / "main.py"
    target.parent.mkdir()
    payload = {
        "hook_event_name": "preToolUse",
        "conversation_id": "conv-1",
        "toolName": "Write",
        "arguments": {
            "path": str(target),
            "contents": "x = 1\n",
        },
        "workspace_roots": [str(tmp_path)],
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    skill.main()
    out = json.loads(capsys.readouterr().out)
    assert out == {"permission": "allow"}
