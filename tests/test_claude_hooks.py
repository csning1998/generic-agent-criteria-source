"""Tests for the Claude Code gate-check and post-write-review hooks.

Loaded from their hyphenated filenames via importlib, since neither is a
valid Python module identifier for a plain `import` statement.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

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


gate_check = _load("gate_check", "hooks/adapters/claude/gate-check.py")
post_write_review = _load(
    "post_write_review", "hooks/adapters/claude/post-write-review.py"
)


@pytest.fixture(autouse=True)
def _isolated_state_dirs(tmp_path, monkeypatch):
    """Redirect both hooks' state and criteria dirs under tmp_path.

    Both modules default STATE_DIR to a fixed, uid-namespaced /tmp path
    shared with this developer's live Claude Code session; running the
    hooks unmodified here would pollute or read that real session state.
    """
    criteria_dir = tmp_path / "criteria"
    criteria_dir.mkdir()
    monkeypatch.setattr(gate_check, "STATE_DIR", tmp_path / "gate-state")
    monkeypatch.setattr(gate_check, "CRITERIA_DIR", criteria_dir)
    monkeypatch.setattr(post_write_review, "STATE_DIR", tmp_path / "post-state")
    monkeypatch.setattr(post_write_review, "CRITERIA_DIR", criteria_dir)


@pytest.mark.parametrize("module", [gate_check, post_write_review])
def test_bare_it_pattern_matches_line_start_comment(module) -> None:
    """No regression: a comment beginning the line still matches."""
    assert module.BARE_IT_PATTERN.search("# it does something")


@pytest.mark.parametrize("module", [gate_check, post_write_review])
def test_bare_it_pattern_matches_inline_trailing_comment(module) -> None:
    """Regression for !16.

    A comment trailing code on the same line was previously invisible
    since the pattern anchored to the line start.
    """
    assert module.BARE_IT_PATTERN.search("x = 1  # it does something")


@pytest.mark.parametrize("module", [gate_check, post_write_review])
def test_bare_it_pattern_ignores_code_without_a_comment(module) -> None:
    """A bare 'it' token with no preceding comment marker is not flagged."""
    assert not module.BARE_IT_PATTERN.search("it = compute_it_value()")


def test_resulting_text_write_uses_content_directly() -> None:
    """A Write call's `content` passes through unchanged."""
    tool_input = {"content": "# it happened\n"}
    text = gate_check.resulting_text(tool_input, "/nonexistent/path.py")
    assert text == "# it happened\n"


def test_resulting_text_falls_back_when_file_unreadable(tmp_path) -> None:
    """An unreadable target falls back to the raw new_string."""
    missing = tmp_path / "missing.py"
    tool_input = {"old_string": "a", "new_string": "b"}
    assert gate_check.resulting_text(tool_input, str(missing)) == "b"


def test_resulting_text_merges_edit_against_full_file(tmp_path) -> None:
    """An Edit call's replacement is merged into the on-disk file."""
    target = tmp_path / "sample.py"
    target.write_text("result = calc()  # explains behavior\n")
    tool_input = {"old_string": "behavior", "new_string": "it"}
    merged = gate_check.resulting_text(tool_input, str(target))
    assert merged == "result = calc()  # explains it\n"


def test_resulting_text_replace_all(tmp_path) -> None:
    """`replace_all` replaces every occurrence, matching the Edit tool."""
    target = tmp_path / "sample.py"
    target.write_text("a a a\n")
    tool_input = {
        "old_string": "a",
        "new_string": "b",
        "replace_all": True,
    }
    assert gate_check.resulting_text(tool_input, str(target)) == "b b b\n"


def test_boundary_spanning_violation_missed_by_snippet_alone(
    tmp_path,
) -> None:
    """Regression for !16.

    The raw new_string snippet alone hid a violation only visible once
    merged against the file's unchanged surrounding comment marker.
    """
    target = tmp_path / "sample.py"
    target.write_text("result = calc()  # explains behavior\n")
    tool_input = {"old_string": "behavior", "new_string": "it"}
    assert gate_check.find_bare_it_violation(tool_input["new_string"]) is None
    merged = gate_check.resulting_text(tool_input, str(target))
    assert gate_check.find_bare_it_violation(merged) is not None


# ---- handle_edit_write end-to-end (gate-check.py) ----


def _run_handle_edit_write(payload, capsys):
    with pytest.raises(SystemExit):
        gate_check.handle_edit_write(payload, scenarios=[])
    return json.loads(capsys.readouterr().out)


def test_handle_edit_write_denies_inline_trailing_it_violation(
    tmp_path, capsys
) -> None:
    """The 401-f register check denies before scenario routing runs."""
    target = tmp_path / "sample.py"
    target.write_text("result = calc()  # explains behavior\n")
    payload = {
        "session_id": "s1",
        "tool_input": {
            "file_path": str(target),
            "old_string": "behavior",
            "new_string": "it",
        },
    }
    out = _run_handle_edit_write(payload, capsys)
    decision = out["hookSpecificOutput"]["permissionDecision"]
    assert decision == "deny"
    assert "401-f" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_handle_edit_write_allows_clean_edit(tmp_path, capsys) -> None:
    """No 401-f register violation and no scenario match allows through."""
    target = tmp_path / "sample.py"
    target.write_text("result = calc()  # explains behavior\n")
    payload = {
        "session_id": "s1",
        "tool_input": {
            "file_path": str(target),
            "old_string": "behavior",
            "new_string": "the outcome",
        },
    }
    out = _run_handle_edit_write(payload, capsys)
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"


# ---- post_write_review.main: malformed stdin and state hardening ----


def test_main_returns_silently_on_malformed_json(monkeypatch, capsys) -> None:
    """Regression for !16: malformed stdin must not crash the hook."""
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    post_write_review.main()
    assert capsys.readouterr().out == ""


def test_main_returns_silently_on_empty_stdin(monkeypatch, capsys) -> None:
    """Regression for !16: empty stdin must not crash the hook."""
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    post_write_review.main()
    assert capsys.readouterr().out == ""


def test_ensure_private_dir_replaces_preexisting_symlink(tmp_path) -> None:
    """Regression for !16.

    A pre-planted symlink at the state path must not be written
    through; it is discarded and replaced by a real directory.
    """
    victim = tmp_path / "victim"
    victim.mkdir()
    target = tmp_path / "state"
    target.symlink_to(victim)
    post_write_review._ensure_private_dir(target)
    assert target.is_dir()
    assert not target.is_symlink()
    assert oct(target.stat().st_mode & 0o777) == "0o700"
    assert list(victim.iterdir()) == []


def test_mark_surfaced_creates_private_marker(tmp_path, monkeypatch) -> None:
    """mark_surfaced leaves a 0o600 marker under a 0o700 state dir."""
    state_dir = tmp_path / "post-state"
    monkeypatch.setattr(post_write_review, "STATE_DIR", state_dir)
    post_write_review.mark_surfaced("session-1", "local-mutate")
    assert post_write_review.already_surfaced("session-1", "local-mutate")
    marker_path = post_write_review.marker("session-1", "local-mutate")
    assert oct(marker_path.stat().st_mode & 0o777) == "0o600"
    assert oct(state_dir.stat().st_mode & 0o777) == "0o700"
