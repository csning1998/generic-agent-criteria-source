"""Regression tests for skill-module statelessness."""

from __future__ import annotations

from contextlib import redirect_stderr
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest
from engineering_principles.dispatch import intercept_post_tool_use
from engineering_principles.dispatch import intercept_pre_tool_use
from engineering_principles.dispatch import intercept_stop
from engineering_principles.module_stateless import derive_composed_module_text
from engineering_principles.module_stateless import find_first_stateful_hit
from engineering_principles.module_stateless import find_module_stateless_reason
from engineering_principles.module_stateless import resolve_skill_module_paths
from engineering_principles.state import load_state


_UUID = "collection://aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_SKILLS_ROOT = Path(__file__).resolve().parent.parent / "skills"


def _write_payload(
    tmp_path: Path,
    rel: str,
    content: str,
    tool: str = "write",
) -> dict:
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    return {
        "hookEventName": "PreToolUse",
        "sessionId": "stateless-session",
        "workspaceRoot": str(tmp_path),
        "cwd": str(tmp_path),
        "toolName": tool,
        "toolInput": {
            "file_path": str(target),
            "content": content,
        },
    }


def _bash_payload(tmp_path: Path, command: str) -> dict:
    return {
        "hookEventName": "PreToolUse",
        "sessionId": "stateless-session",
        "workspaceRoot": str(tmp_path),
        "cwd": str(tmp_path),
        "toolName": "run_terminal_command",
        "toolInput": {"command": command},
    }


def _session_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "ENGINEERING_PRINCIPLES_STATE_DIR", str(tmp_path / "state")
    )
    monkeypatch.setenv("GROK_SESSION_ID", "stateless-session")
    monkeypatch.setenv("GROK_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("ENGINEERING_PRINCIPLES_HOOK", raising=False)


def _resolved_module(tmp_path: Path) -> str:
    return str((tmp_path / "skills/skill-module-demo/SKILL.md").resolve())


def test_find_first_stateful_hit_placeholder_collection() -> None:
    """Angle-bracket tokens are stripped before the collection scan."""
    text = '{"collection": "collection://<from 03-identifiers.md>"}'
    assert find_first_stateful_hit(text) is None


def test_find_first_stateful_hit_baked_identifiers() -> None:
    """UUID, home path, login, prefix, and filled tables are denied."""
    assert find_first_stateful_hit(_UUID) is not None
    assert find_first_stateful_hit("/home/csning1998/.grok/docs") is not None
    assert find_first_stateful_hit("$HOME/csning1998/docs") is not None
    assert find_first_stateful_hit('group: "csning1998-lab"') is not None
    assert find_first_stateful_hit("data_source 316919d4-aaaa") is not None
    assert (
        find_first_stateful_hit('{"type_from_conv": {"feat": "type::feature"}}')
        is not None
    )


def test_find_first_stateful_hit_empty_tables() -> None:
    """Empty mapping objects and placeholder groups stay in a module."""
    text = (
        '{"group": "group/path", "tables": {}, '
        '"type_from_conv": {"<key>": "<label>"}, '
        '"allowlist": ["<label>"]}'
    )
    assert find_first_stateful_hit(text) is None


def test_find_first_stateful_hit_placeholder_tables() -> None:
    """Placeholder mapping keys stay clean after JSON decode."""
    text = (
        '{"type_from_conv": {"<key>": "<label>"}, '
        '"allowlist": ["<label>"], '
        '"area_patterns": [{"pattern": "<regex>", "label": "<label>"}], '
        '"bang_adds": "<label>", '
        '"keep_prefixes": ["<prefix>"]}'
    )
    assert find_first_stateful_hit(text) is None


def test_find_first_stateful_hit_nested_tables() -> None:
    """Filled tables under a tables object are denied."""
    text = (
        '{"tables": {"type_from_conv": {"feat": "type::feature"}, '
        '"allowlist": ["type::feature"]}}'
    )
    hit = find_first_stateful_hit(text)
    assert hit is not None
    assert "mapping table" in hit


def test_find_first_stateful_hit_pretty_printed_json_fence() -> None:
    """Pretty-printed JSON in a markdown fence is decoded."""
    text = (
        "example\n\n```json\n{\n"
        '    "type_from_conv": {\n'
        '        "feat": "type::feature"\n'
        "    }\n"
        "}\n```\n"
    )
    hit = find_first_stateful_hit(text)
    assert hit is not None
    assert "type_from_conv" in hit


def test_find_first_stateful_hit_empty_string_keys() -> None:
    """Empty strings after a would-be placeholder strip remain filled."""
    assert find_first_stateful_hit('{"": ""}') is None
    assert (
        find_first_stateful_hit('{"type_from_conv": {"": "type::feature"}}')
        is not None
    )


def test_find_first_stateful_hit_dummy_result_json() -> None:
    """GitlabMrLabelResult dummy 0/1 values are not mapping tables."""
    text = (
        '{"ok": true, "error": null, "mode": "dry-run", '
        '"total": 0, "noop": 0, "changed": 0, "applied": 0, '
        '"failed": [], "changes": []}'
    )
    assert find_first_stateful_hit(text) is None


def test_find_first_stateful_hit_trailing_comma() -> None:
    """Invalid JSON is skipped. The decoder does not guess table keys."""
    text = '{"type_from_conv": {"feat": "type::feature",}}'
    assert find_first_stateful_hit(text) is None


def test_find_first_stateful_hit_area_patterns() -> None:
    """area_patterns schema keys are allowed. Concrete values are not."""
    hit = find_first_stateful_hit(
        '{"area_patterns": [{"pattern": "terraform", '
        '"label": "area::infrastructure"}]}'
    )
    assert hit is not None
    assert "area_patterns" in hit


def test_find_first_stateful_hit_null_rename() -> None:
    """A null rename field is unfilled JSON, not a GitLab rename table."""
    text = '{"mkdir_paths": ["~/Documents/[P] x"], "rename": null, "moves": []}'
    assert find_first_stateful_hit(text) is None


def test_find_first_stateful_hit_label_rename() -> None:
    """A string-to-string rename map is a filled mapping table."""
    hit = find_first_stateful_hit(
        '{"tables": {"rename": {"pending": "status::pending"}}}'
    )
    assert hit is not None
    assert "rename" in hit


def test_find_first_stateful_hit_checked_in_modules() -> None:
    """Every file under skills/skill-module-* must pass the scan."""
    assert _SKILLS_ROOT.is_dir()
    dirty: list[str] = []
    for path in _SKILLS_ROOT.glob("skill-module-*/**/*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.suffix not in {".md", ".py"}:
            continue
        hit = find_first_stateful_hit(path.read_text(encoding="utf-8"))
        if hit:
            dirty.append(f"{path}: {hit}")
    assert dirty == []


def test_find_module_stateless_reason_non_module_path() -> None:
    """Layer files may hold workspace identifiers."""
    reason = find_module_stateless_reason(
        "skills/skill-apply-gitlab-mr-labels/SKILL.md",
        _UUID,
    )
    assert reason is None


def test_derive_composed_module_text_omits_command() -> None:
    """A shell command is not treated as prospective file text."""
    assert derive_composed_module_text("", "", "", "") == ""
    assert derive_composed_module_text("body", "", "", "") == "body"


def test_resolve_skill_module_paths_outside_workspace(tmp_path: Path) -> None:
    """Write targets outside workspaceRoot are not returned."""
    outside = "/tmp/skill-module-outside/SKILL.md"
    found = resolve_skill_module_paths(
        outside,
        "",
        cwd=str(tmp_path),
        workspace=str(tmp_path),
    )
    assert found == []


def test_resolve_skill_module_paths_cp_dest(tmp_path: Path) -> None:
    """Cp destination is a write target. The source path is not."""
    found = resolve_skill_module_paths(
        "",
        "cp notes.md skills/skill-module-demo/SKILL.md",
        cwd=str(tmp_path),
        workspace=str(tmp_path),
    )
    assert found == [_resolved_module(tmp_path)]
    assert (
        resolve_skill_module_paths(
            "",
            "cp skills/skill-module-demo/SKILL.md /tmp/out.md",
            cwd=str(tmp_path),
            workspace=str(tmp_path),
        )
        == []
    )


def test_resolve_skill_module_paths_mv_dest(tmp_path: Path) -> None:
    """Mv destination is a write target."""
    found = resolve_skill_module_paths(
        "",
        "mv notes.md 'skills/skill-module-demo/SKILL.md'",
        cwd=str(tmp_path),
        workspace=str(tmp_path),
    )
    assert found == [_resolved_module(tmp_path)]


def test_resolve_skill_module_paths_sed_i(tmp_path: Path) -> None:
    """Sed -i edits a file in place. sed without -i does not."""
    found = resolve_skill_module_paths(
        "",
        "sed -i 's/a/b/' skills/skill-module-demo/SKILL.md",
        cwd=str(tmp_path),
        workspace=str(tmp_path),
    )
    assert found == [_resolved_module(tmp_path)]
    assert (
        resolve_skill_module_paths(
            "",
            "sed 's/a/b/' skills/skill-module-demo/SKILL.md",
            cwd=str(tmp_path),
            workspace=str(tmp_path),
        )
        == []
    )


def test_intercept_pre_tool_use_denies_stateful_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PreToolUse denies a skill-module Write that bakes a UUID."""
    _session_env(tmp_path, monkeypatch)
    payload = _write_payload(
        tmp_path,
        "skills/skill-module-demo/SKILL.md",
        f"url = {_UUID}\n",
    )
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_pre_tool_use(payload)
    assert code == 2
    assert "MUST be stateless" in buf.getvalue()


def test_intercept_pre_tool_use_compose_scans_whole_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A clean patch on a dirty module is still denied."""
    _session_env(tmp_path, monkeypatch)
    target = tmp_path / "skills/skill-module-demo/SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text(f"keep {_UUID}\nedit-me\n", encoding="utf-8")
    payload = {
        "hookEventName": "PreToolUse",
        "sessionId": "stateless-session",
        "workspaceRoot": str(tmp_path),
        "cwd": str(tmp_path),
        "toolName": "search_replace",
        "toolInput": {
            "file_path": str(target),
            "old_string": "edit-me",
            "new_string": "edited",
        },
    }
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_pre_tool_use(payload)
    assert code == 2
    assert "collection UUID" in buf.getvalue()


def test_intercept_pre_tool_use_bash_heredoc_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A shell write that names a skill-module path is scanned."""
    _session_env(tmp_path, monkeypatch)
    payload = _bash_payload(
        tmp_path,
        f"cat > skills/skill-module-demo/SKILL.md <<'EOF'\n{_UUID}\nEOF\n",
    )
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_pre_tool_use(payload)
    assert code == 2
    assert "MUST be stateless" in buf.getvalue()


def test_intercept_pre_tool_use_bash_mention_without_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A command that only names a skill-module path is not a write."""
    _session_env(tmp_path, monkeypatch)
    payload = _bash_payload(
        tmp_path,
        f"rg {_UUID} skills/skill-module-demo/SKILL.md",
    )
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_pre_tool_use(payload)
    assert code == 0
    assert "MUST be stateless" not in buf.getvalue()


def test_intercept_pre_tool_use_bash_test_file_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A test file may mention skill-module paths and UUIDs."""
    _session_env(tmp_path, monkeypatch)
    payload = _bash_payload(
        tmp_path,
        "cat > tests/test_module_stateless.py <<'EOF'\n"
        f"path = 'skills/skill-module-demo/SKILL.md'\n"
        f"uuid = '{_UUID}'\n"
        "EOF\n",
    )
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_pre_tool_use(payload)
    assert code == 0


def test_intercept_pre_tool_use_quoted_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An echo payload redirected into a skill-module file is scanned."""
    _session_env(tmp_path, monkeypatch)
    payload = _bash_payload(
        tmp_path,
        f"echo '{_UUID}' > 'skills/skill-module-demo/SKILL.md'\n",
    )
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_pre_tool_use(payload)
    assert code == 2
    assert "MUST be stateless" in buf.getvalue()


def test_intercept_pre_tool_use_command_comment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A UUID in a shell comment is not prospective file text."""
    _session_env(tmp_path, monkeypatch)
    payload = _bash_payload(
        tmp_path,
        f"echo dirty > 'skills/skill-module-demo/SKILL.md'\n# {_UUID}\n",
    )
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_pre_tool_use(payload)
    assert code == 0
    assert "MUST be stateless" not in buf.getvalue()


def test_intercept_pre_tool_use_tee_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tee target on a skill-module path is a write."""
    _session_env(tmp_path, monkeypatch)
    payload = _bash_payload(
        tmp_path,
        f"printf '%s\\n' '{_UUID}' | "
        "tee skills/skill-module-demo/SKILL.md >/dev/null\n",
    )
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_pre_tool_use(payload)
    assert code == 2
    assert "MUST be stateless" in buf.getvalue()


def test_intercept_pre_tool_use_heredoc_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A heredoc body is a scan blob for the redirect target."""
    _session_env(tmp_path, monkeypatch)
    payload = _bash_payload(
        tmp_path,
        "cat > skills/skill-module-demo/SKILL.md <<'EOF'\n"
        '{"type_from_conv": {"feat": "type::feature"}}\n'
        "EOF\n",
    )
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_pre_tool_use(payload)
    assert code == 2
    assert "mapping table" in buf.getvalue()


def test_intercept_pre_tool_use_sed_i_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sed -i script that inserts a UUID is denied."""
    _session_env(tmp_path, monkeypatch)
    payload = _bash_payload(
        tmp_path,
        f"sed -i 's/foo/{_UUID}/' skills/skill-module-demo/SKILL.md",
    )
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_pre_tool_use(payload)
    assert code == 2
    assert "MUST be stateless" in buf.getvalue()


def test_intercept_pre_tool_use_cp_dest_without_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cp records a dest. A UUID elsewhere in the command is not file text."""
    _session_env(tmp_path, monkeypatch)
    payload = _bash_payload(
        tmp_path,
        f"rg {_UUID} notes.md && cp notes.md skills/skill-module-demo/SKILL.md",
    )
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_pre_tool_use(payload)
    assert code == 0
    assert "MUST be stateless" not in buf.getvalue()


def test_intercept_post_tool_use_outside_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PostToolUse does not record a skill-module path outside workspace."""
    _session_env(tmp_path, monkeypatch)
    payload = {
        "hookEventName": "PostToolUse",
        "sessionId": "stateless-session",
        "workspaceRoot": str(tmp_path),
        "cwd": str(tmp_path),
        "toolName": "write",
        "toolInput": {
            "file_path": "/tmp/skill-module-outside/SKILL.md",
            "content": f"url = {_UUID}\n",
        },
    }
    assert intercept_post_tool_use(payload) == 0
    state = load_state(payload)
    assert state.get("skill_module_writes") == []


def test_intercept_post_tool_use_cp_dest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PostToolUse records a cp destination under a skill-module path."""
    _session_env(tmp_path, monkeypatch)
    dest = tmp_path / "skills/skill-module-demo/SKILL.md"
    dest.parent.mkdir(parents=True)
    dest.write_text("url = collection://<from locate>\n", encoding="utf-8")
    payload = {
        "hookEventName": "PostToolUse",
        "sessionId": "stateless-session",
        "workspaceRoot": str(tmp_path),
        "cwd": str(tmp_path),
        "toolName": "run_terminal_command",
        "toolInput": {
            "command": "cp notes.md skills/skill-module-demo/SKILL.md",
        },
    }
    assert intercept_post_tool_use(payload) == 0
    state = load_state(payload)
    writes = state.get("skill_module_writes") or []
    assert _resolved_module(tmp_path) in writes


def test_intercept_stop_blocks_dirty_recorded_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After a write, Stop blocks until the on-disk module is clean."""
    _session_env(tmp_path, monkeypatch)
    target = tmp_path / "skills/skill-module-demo/SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text(f"url = {_UUID}\n", encoding="utf-8")
    post = {
        "hookEventName": "PostToolUse",
        "sessionId": "stateless-session",
        "workspaceRoot": str(tmp_path),
        "cwd": str(tmp_path),
        "toolName": "write",
        "toolInput": {"file_path": str(target), "content": target.read_text()},
        "reason": "end_turn",
    }
    err = StringIO()
    with redirect_stderr(err):
        assert intercept_post_tool_use(post) == 0
    assert "MUST be stateless" in err.getvalue()

    stop = {
        "hookEventName": "Stop",
        "sessionId": "stateless-session",
        "workspaceRoot": str(tmp_path),
        "cwd": str(tmp_path),
        "reason": "end_turn",
    }
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_stop(stop)
    assert code == 2
    assert "Rewrite" in buf.getvalue()

    target.write_text("url = collection://<from locate>\n", encoding="utf-8")
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_stop(stop)
    assert code == 0
    assert buf.getvalue().strip() == ""


def test_intercept_stop_session_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Session-end Stop fires are observe-only."""
    _session_env(tmp_path, monkeypatch)
    assert (
        intercept_stop(
            {
                "hookEventName": "Stop",
                "sessionId": "stateless-session",
                "workspaceRoot": str(tmp_path),
                "reason": "shutdown",
            }
        )
        == 0
    )
