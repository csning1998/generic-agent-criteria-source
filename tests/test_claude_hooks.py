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


def test_bare_it_pattern_matches_line_start_comment() -> None:
    """Post owns register: a comment beginning the line still matches."""
    bare = "it"
    sample = "# " + bare + " does something"
    assert post_write_review.BARE_IT_PATTERN.search(sample)


def test_bare_it_pattern_matches_inline_trailing_comment() -> None:
    """Regression for !16.

    A comment trailing code on the same line was previously invisible
    since the pattern anchored to the line start.
    """
    bare = "it"
    sample = "x = 1  # " + bare + " does something"
    assert post_write_review.BARE_IT_PATTERN.search(sample)


def test_bare_it_pattern_ignores_code_without_a_comment() -> None:
    """A bare pronoun token with no preceding comment marker is not flagged."""
    sample = "it = compute_it_value()"
    assert not post_write_review.BARE_IT_PATTERN.search(sample)


def test_gate_check_does_not_export_register_helpers() -> None:
    """Register checks live on PostToolUse only, not PreToolUse gate-check."""
    assert not hasattr(gate_check, "BARE_IT_PATTERN")
    assert not hasattr(gate_check, "find_bare_it_violation")
    assert not hasattr(gate_check, "resulting_text")
    assert not hasattr(gate_check, "COMMENT_CHECK_SKIP_GLOBS")


# handle_edit_write end-to-end (gate-check.py)


def _run_handle_edit_write(payload, capsys):
    with pytest.raises(SystemExit):
        gate_check.handle_edit_write(payload, scenarios=[])
    return json.loads(capsys.readouterr().out)


def test_handle_edit_write_allows_inline_trailing_it(tmp_path, capsys) -> None:
    """Pre allows a bare-pronoun comment; Post register reviews after write."""
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
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_handle_edit_write_allows_clean_edit(tmp_path, capsys) -> None:
    """No scenario match allows an Edit through PreToolUse."""
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


# post_write_review.main: malformed stdin and state hardening


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


# find_register_violations: 401(f)/(g)/(d) mechanical checks


@pytest.mark.parametrize(
    "text",
    [
        "# The pointer resolves to a value which the caller must free.",
        "# This test MUST pass on every platform.",
        "# execution runs in which the lock is held.",
        "# The retry budget is non-obvious here.",
        "# leaving no dangling separator behind the join.",
        "# The known_hosts path resolves the same way across every caller.",
    ],
)
def test_find_register_violations_allows_clean_comments(text: str) -> None:
    """A comment that already complies with the 401 register raises nothing."""
    assert post_write_review.find_register_violations(text) == []


def test_find_register_violations_flags_bare_it() -> None:
    """401(f): Post flags a bare pronoun in a comment."""
    bare = "it"
    text = "# " + bare + " does something"
    violations = post_write_review.find_register_violations(text)
    assert any("bare pronoun 'it'" in v for v in violations)


def test_find_register_violations_flags_comma_so() -> None:
    """401(f): a comma-'so' causal connector is a hard violation."""
    text = "# The cache warms, so lookups stay fast."
    violations = post_write_review.find_register_violations(text)
    assert any("comma-'so'" in v for v in violations)


def test_find_register_violations_flags_bare_so_modal() -> None:
    """401(f): a bare 'so' escape-hatch before a modal is a hard violation."""
    text = "# The retry keeps state so it can resume."
    violations = post_write_review.find_register_violations(text)
    assert any("bare escape-hatch 'so'" in v for v in violations)


def test_find_register_violations_flags_bare_so_without_modal() -> None:
    """401(d)/(f): spaced 'so' is banned even when no modal follows."""
    text = "# The hyphenated form is restored so path segments stay covered."
    violations = post_write_review.find_register_violations(text)
    assert any("bare escape-hatch 'so'" in v for v in violations)


def test_find_register_violations_flags_md_bare_so_no_modal() -> None:
    """Markdown prose gets the same spaced-'so' ban via the virtual prefix."""
    text = "The hyphenated form is restored so path segments stay covered."
    violations = post_write_review.find_register_violations(
        text, is_markdown=True
    )
    assert any("bare escape-hatch 'so'" in v for v in violations)


def test_find_register_violations_flags_both_so_shapes_on_one_line() -> None:
    """A comma-'so' clause and a separate bare-'so' modal clause both flag.

    Before the fix, comma-so and bare-so lived in an if/elif pair. A
    line carrying a comma-so clause silently swallowed a second,
    independent bare-so-modal clause elsewhere on the same line.
    """
    text = (
        "# The cache warms, so lookups stay fast, and the worker "
        "retries so it can resume."
    )
    violations = post_write_review.find_register_violations(text)
    assert any("comma-'so'" in v for v in violations)
    assert any("bare escape-hatch 'so'" in v for v in violations)


def test_find_register_violations_flags_inline_trailing_it() -> None:
    """Regression for !16: trailing comment still flags bare pronoun."""
    bare = "it"
    text = "x = 1  # " + bare + " does something"
    violations = post_write_review.find_register_violations(text)
    assert any("bare pronoun 'it'" in v for v in violations)


def test_main_flags_bare_it_from_on_disk_file(
    tmp_path, monkeypatch, capsys
) -> None:
    """Post reads the file on disk after Edit, not the new_string snippet alone.

    Regression for !16: a replacement of only the pronoun is invisible in the
    snippet, but the on-disk comment line already carries the marker.
    """
    import io

    bare = "it"
    target = tmp_path / "sample.py"
    target.write_text("result = calc()  # explains " + bare + "\n")
    payload = {
        "tool_name": "Edit",
        "session_id": "s1",
        "tool_input": {
            "file_path": str(target),
            "old_string": "behavior",
            "new_string": bare,
        },
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    post_write_review.main()
    out = capsys.readouterr().out
    assert "bare pronoun 'it'" in out
    assert "VIOLATION" in out


def test_find_register_violations_flags_that_relative_clause() -> None:
    """401(f) Relative Clause Formation: 'that' MUST NOT introduce a clause."""
    text = "# The retry loop resumes that carries the last cursor forward."
    violations = post_write_review.find_register_violations(text)
    assert any("relative clause" in v for v in violations)


def test_find_register_violations_flags_demonstrative_subject() -> None:
    """401(f) Impersonal Tone: a bare demonstrative MUST NOT be the subject."""
    text = "# This MUST NOT occur under any condition."
    violations = post_write_review.find_register_violations(text)
    assert any("subject position" in v for v in violations)


def test_find_register_violations_flags_demonstrative_object() -> None:
    """401(f) Impersonal Tone: a bare demonstrative MUST NOT be the object."""
    text = "# The caller MUST validate this."
    violations = post_write_review.find_register_violations(text)
    assert any("object position" in v for v in violations)


def test_find_register_violations_flags_stranded_preposition() -> None:
    """401(f) Prohibition of Preposition Stranding."""
    text = "# The lock acquisition happens in."
    violations = post_write_review.find_register_violations(text)
    assert any("stranded preposition" in v for v in violations)


def test_find_register_violations_flags_dash_and_arrow_glyphs() -> None:
    """401(g) Prohibited Symbols: em-dash, en-dash, and arrow glyphs."""
    text = "# The two states diverge — a rare case worth noting."
    violations = post_write_review.find_register_violations(text)
    assert any("dash" in v for v in violations)


def test_find_register_violations_flags_semicolon() -> None:
    """401(f) Prohibition of Punctuation-Forced Clauses."""
    text = "# The mutex guards the counter; the reader never blocks."
    violations = post_write_review.find_register_violations(text)
    assert any("semicolon" in v for v in violations)


def test_find_register_violations_flags_first_person_we() -> None:
    """401(f) Impersonal Tone: first-person pronouns MUST NOT be used."""
    text = "# We handle this differently from the standard case."
    violations = post_write_review.find_register_violations(text)
    assert any("first-person" in v for v in violations)


def test_find_register_violations_flags_bare_negation() -> None:
    """401(f) Prohibition of Bare Negation on a finite main clause."""
    text = "# The function declares no default value for the argument."
    violations = post_write_review.find_register_violations(text)
    assert any("bare 'no'" in v for v in violations)


def test_find_register_violations_flags_defensive_analogy() -> None:
    """401(d) Prohibition of the Defensive Analogy."""
    text = "# The retry loop behaves exactly like the poll loop above."
    violations = post_write_review.find_register_violations(text)
    assert any("analogy" in v for v in violations)


def test_find_register_violations_flags_sentence_initial_which() -> None:
    """401(f): a sentence-initial 'Which' has no antecedent to bind to."""
    text = "# Which means the cache entry is now stale."
    violations = post_write_review.find_register_violations(text)
    assert any("sentence-initial" in v for v in violations)


def test_find_register_violations_flags_possessive_apostrophe() -> None:
    """401(f) Prohibition of Colloquialisms: a genitive 's is colloquial."""
    text = "# The variable's type carries the attributes the module consumes."
    violations = post_write_review.find_register_violations(text)
    assert any("genitive" in v for v in violations)


def test_find_register_violations_flags_which_and_that_in_one_block() -> None:
    """A comment block MUST NOT mix 'which' and 'that', even across lines."""
    text = (
        "# declares a hosts variable which\n"
        "  # carries only the attributes that particular module consumes."
    )
    violations = post_write_review.find_register_violations(text)
    assert any("'which' and 'that'" in v for v in violations)


def test_find_register_violations_allows_which_alone_across_lines() -> None:
    """A 'which' clause spanning two lines, with no 'that', stays clean."""
    text = (
        "# A block which the operator wrote by hand MUST survive every "
        "concurrent mutation byte for\n"
        "# byte."
    )
    violations = post_write_review.find_register_violations(text)
    assert not any("'which' and 'that'" in v for v in violations)


# parse_frontmatter / load_scenarios: criteria file ingestion (gate-check.py)


def test_parse_frontmatter_reads_external_write_scenario() -> None:
    """A real multi-line-array criteria file parses id, globs, and load list."""
    root = Path(__file__).resolve().parent.parent
    meta = gate_check.parse_frontmatter(
        root / "hooks" / "criteria" / "external-write.md"
    )
    assert meta["id"] == "external-write"
    assert "git " in meta["command_prefix"]
    assert "git push" in meta["command_glob"]
    assert "git status" in meta["readonly_command_glob"]
    assert (
        "references/301_Default_State_and_Authorization_Boundaries.md"
        in meta["load"]
    )


def test_load_scenarios_skips_files_without_id() -> None:
    """A criteria file lacking an `id:` key is excluded from the roster."""
    criteria_dir = gate_check.CRITERIA_DIR
    (criteria_dir / "a.md").write_text(
        '---\nid: a\npath_glob: ["*.a"]\n---\nbody\n'
    )
    (criteria_dir / "no-id.md").write_text("---\nfacets: [x]\n---\nbody\n")
    scenarios = gate_check.load_scenarios()
    assert [s["id"] for s in scenarios] == ["a"]


# match_path / match_command: scenario routing (gate-check.py)


def test_match_path_returns_first_matching_scenario() -> None:
    """The first scenario whose path_glob matches the file name wins."""
    scenarios = [
        {"id": "markdown", "path_glob": ["*.md", "*.mdx"]},
        {"id": "typescript", "path_glob": ["*.ts", "*.tsx"]},
    ]
    assert (
        gate_check.match_path(scenarios, "/repo/README.md")["id"] == "markdown"
    )
    assert (
        gate_check.match_path(scenarios, "/repo/app.tsx")["id"] == "typescript"
    )
    assert gate_check.match_path(scenarios, "/repo/app.py") is None


NARROW_PATH_GLOB = (
    '    path_glob: ["exact-target.md", "alt-target.md", "*NESTED*"]\n'
)


@pytest.fixture
def specificity_gate_criteria(tmp_path: Path) -> Path:
    """Isolated criteria: one narrow path_glob and one broad *.md glob."""
    criteria = gate_check.CRITERIA_DIR
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
    (references / "broad-load.md").write_text("BROAD_LOAD_MARKER\n")
    (references / "narrow-load-a.md").write_text("NARROW_LOAD_A_MARKER\n")
    (references / "narrow-load-b.md").write_text("NARROW_LOAD_B_MARKER\n")
    return tmp_path


@pytest.mark.parametrize(
    "filename",
    [
        "exact-target.md",
        "alt-target.md",
        "prefix_NESTED_suffix.md",
    ],
)
def test_gate_once_surfaces_narrow_scenario_load(
    specificity_gate_criteria: Path, filename: str, capsys
) -> None:
    """Narrow path_glob match denies with the narrow scenario load."""
    target = specificity_gate_criteria / filename
    payload = {
        "session_id": "s1",
        "tool_input": {"file_path": str(target), "content": "# title\n"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_edit_write(payload, gate_check.load_scenarios())
    out = json.loads(capsys.readouterr().out)
    context = out["hookSpecificOutput"]["additionalContext"]
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "NARROW_LOAD_A_MARKER" in context
    assert "NARROW_LOAD_B_MARKER" in context


def test_gate_once_broad_md_gets_broad_load_only(
    specificity_gate_criteria: Path, capsys
) -> None:
    """A path matched only by *.md gets the broad scenario load."""
    scenarios = gate_check.load_scenarios()
    meta = gate_check.match_path(scenarios, "/repo/other.md")
    assert meta["id"] == "broad-md"
    target = specificity_gate_criteria / "other.md"
    payload = {
        "session_id": "s1",
        "tool_input": {"file_path": str(target), "content": "# title\n"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_edit_write(payload, scenarios)
    out = json.loads(capsys.readouterr().out)
    context = out["hookSpecificOutput"]["additionalContext"]
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "BROAD_LOAD_MARKER" in context
    assert "NARROW_LOAD_A_MARKER" not in context


def test_match_command_returns_first_matching_scenario() -> None:
    """The first scenario whose command_glob substring matches wins."""
    scenarios = [
        {"id": "external-write", "command_glob": ["git push", "git commit"]}
    ]
    assert (
        gate_check.match_command(scenarios, "git push origin main")["id"]
        == "external-write"
    )
    assert gate_check.match_command(scenarios, "ls -la") is None


# gate_once: once-per-session deny-then-allow semantics (gate-check.py)


def _run_gate_once(session_id, meta, capsys):
    with pytest.raises(SystemExit):
        gate_check.gate_once(session_id, meta)
    return json.loads(capsys.readouterr().out)


def test_gate_once_denies_first_call_then_allows_retry(capsys) -> None:
    """Section 2: the 1st call denies and surfaces load text; the 2nd allows."""
    meta = {"id": "local-mutate", "load": []}
    first = _run_gate_once("session-1", meta, capsys)
    assert first["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert (
        "local-mutate"
        in first["hookSpecificOutput"]["permissionDecisionReason"]
    )
    second = _run_gate_once("session-1", meta, capsys)
    assert second["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_gate_once_isolates_by_scenario_within_the_same_session(capsys) -> None:
    """Surfacing one scenario does not pre-clear a different scenario id."""
    meta_a = {"id": "scenario-a", "load": []}
    meta_b = {"id": "scenario-b", "load": []}
    _run_gate_once("session-1", meta_a, capsys)
    second = _run_gate_once("session-1", meta_b, capsys)
    assert second["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_gate_once_isolates_by_session_for_the_same_scenario(capsys) -> None:
    """A scenario surfaced under one session_id still denies under another."""
    meta = {"id": "local-mutate", "load": []}
    _run_gate_once("session-1", meta, capsys)
    other_session = _run_gate_once("session-2", meta, capsys)
    assert other_session["hookSpecificOutput"]["permissionDecision"] == "deny"


# require_exec_phrase: EXEC_PHRASES detection in the current user turn


def _write_transcript(tmp_path, content: str) -> str:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {"content": content}}) + "\n"
    )
    return str(transcript)


def test_require_exec_phrase_returns_silently_when_phrase_present(
    tmp_path,
) -> None:
    """A transcript line carrying an EXEC_PHRASES token needs no denial."""
    payload = {
        "transcript_path": _write_transcript(tmp_path, "去執行 git push")
    }
    gate_check.require_exec_phrase(payload, "'git push'")


def test_require_exec_phrase_denies_when_phrase_absent(capsys) -> None:
    """Claude: absent phrase denies with an AskUserQuestion instruction."""
    payload = {"transcript_path": ""}
    with pytest.raises(SystemExit):
        gate_check.require_exec_phrase(payload, "'git push'")
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert (
        "AskUserQuestion"
        in out["hookSpecificOutput"]["permissionDecisionReason"]
    )


def test_require_exec_phrase_asks_under_cursor_protocol(
    monkeypatch, capsys
) -> None:
    """Cursor: absent phrase asks via the native permission card."""
    monkeypatch.setattr(
        gate_check, "__file__", "/tmp/home/.cursor/hooks/gate-check.py"
    )
    payload = {"transcript_path": ""}
    with pytest.raises(SystemExit):
        gate_check.require_exec_phrase(payload, "'git push'")
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "ask"


# handle_bash: hard-deny list, external-write allowlist, gate_once integration


def _run_handle_bash(payload, scenarios, capsys):
    with pytest.raises(SystemExit):
        gate_check.handle_bash(payload, scenarios=scenarios)
    return json.loads(capsys.readouterr().out)


EXTERNAL_WRITE_META = {
    "id": "external-write",
    "command_prefix": ["git "],
    "command_glob": ["git push", "git commit"],
    "readonly_command_glob": ["git status", "git log"],
}


def test_handle_bash_hard_denies_force_push(capsys) -> None:
    """Git push --force is denied regardless of scenario or exec phrase."""
    payload = {
        "session_id": "s1",
        "tool_input": {"command": "git push --force origin main"},
    }
    out = _run_handle_bash(payload, [], capsys)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert (
        "must never run"
        in out["hookSpecificOutput"]["permissionDecisionReason"]
    )


def test_handle_bash_hard_denies_rm_rf(capsys) -> None:
    """Rm -rf is denied regardless of scenario or exec phrase."""
    payload = {"session_id": "s1", "tool_input": {"command": "rm -rf /tmp/x"}}
    out = _run_handle_bash(payload, [], capsys)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_handle_bash_allows_readonly_git_without_exec_phrase(capsys) -> None:
    """A readonly_command_glob entry needs no exec phrase."""
    payload = {"session_id": "s1", "tool_input": {"command": "git status"}}
    out = _run_handle_bash(payload, [EXTERNAL_WRITE_META], capsys)
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_handle_bash_denies_git_push_without_exec_phrase(capsys) -> None:
    """Allowlisted write with no exec phrase denies via require_exec_phrase."""
    payload = {
        "session_id": "s1",
        "transcript_path": "",
        "tool_input": {"command": "git push origin main"},
    }
    out = _run_handle_bash(payload, [EXTERNAL_WRITE_META], capsys)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "git push" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_handle_bash_allows_git_push_after_exec_phrase_and_retry(
    tmp_path, capsys
) -> None:
    """With the phrase present, gate_once denies once then allows retry."""
    payload = {
        "session_id": "s1",
        "transcript_path": _write_transcript(
            tmp_path, "Approve running git push now"
        ),
        "tool_input": {"command": "git push origin main"},
    }
    first = _run_handle_bash(payload, [EXTERNAL_WRITE_META], capsys)
    assert first["hookSpecificOutput"]["permissionDecision"] == "deny"
    second = _run_handle_bash(payload, [EXTERNAL_WRITE_META], capsys)
    assert second["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_handle_bash_allows_when_no_scenario_matches(capsys) -> None:
    """An unrelated command with no matching scenario passes through."""
    payload = {"session_id": "s1", "tool_input": {"command": "ls -la"}}
    out = _run_handle_bash(payload, [EXTERNAL_WRITE_META], capsys)
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"


# normalize_payload / is_cursor_mcp_external_write: Claude/Cursor field mapping


def test_normalize_payload_maps_cursor_field_aliases() -> None:
    """Cursor camelCase arguments normalize onto Claude field names."""
    raw = {
        "toolName": "shell_execute",
        "conversationId": "conv-1",
        "arguments": {"path": "/tmp/x.py", "contents": "print(1)"},
        "command": "ls",
    }
    normalized = gate_check.normalize_payload(raw)
    assert normalized["tool_name"] == "shell_execute"
    assert normalized["session_id"] == "conv-1"
    assert normalized["tool_input"]["file_path"] == "/tmp/x.py"
    assert normalized["tool_input"]["content"] == "print(1)"
    assert normalized["tool_input"]["command"] == "ls"


def test_normalize_payload_prefers_claude_native_fields() -> None:
    """Claude's native field names pass through unchanged."""
    raw = {
        "tool_name": "Edit",
        "session_id": "s1",
        "tool_input": {"file_path": "/tmp/y.py"},
    }
    normalized = gate_check.normalize_payload(raw)
    assert normalized["tool_name"] == "Edit"
    assert normalized["session_id"] == "s1"
    assert normalized["tool_input"]["file_path"] == "/tmp/y.py"


def test_is_cursor_mcp_external_write_requires_cursor_protocol(
    monkeypatch,
) -> None:
    """The MCP-write marker match only applies under the Cursor adapter."""
    assert not gate_check.is_cursor_mcp_external_write(
        "mcp__github__create_pull_request"
    )
    monkeypatch.setattr(
        gate_check, "__file__", "/tmp/home/.cursor/hooks/gate-check.py"
    )
    assert gate_check.is_cursor_mcp_external_write(
        "mcp__github__create_pull_request"
    )
    assert not gate_check.is_cursor_mcp_external_write(
        "mcp__github__get_pull_request"
    )


# NOTEBOOK_GLOBS: .ipynb denial must land before any disk write is attempted


def test_handle_edit_write_denies_ipynb_and_leaves_no_file_on_disk(
    tmp_path, capsys
) -> None:
    """notebook.md is a hard policy: deny fires before the target ever exists.

    A PreToolUse deny means the harness never invokes the underlying
    Edit/Write call. The target path therefore stays absent. Moving the
    notebook check to PostToolUse would leave a dirty file on disk before
    any content review could run.
    """
    target = tmp_path / "analysis.ipynb"
    payload = {
        "session_id": "s1",
        "tool_input": {"file_path": str(target), "content": "{}"},
    }
    with pytest.raises(SystemExit):
        gate_check.handle_edit_write(payload, scenarios=[])
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "notebook" in out["hookSpecificOutput"]["permissionDecisionReason"]
    assert not target.exists()


# PreToolUse vs PostToolUse labeling: gate_once denies once and allows a
# retry only while gate-check.py stays a PreToolUse hook. A relabel to
# PostToolUse would let the write land before the deny fires.


def test_gate_check_deny_and_allow_stay_pretooluse(capsys) -> None:
    """gate-check.py decisions must never carry a PostToolUse event name."""
    with pytest.raises(SystemExit):
        gate_check.deny("reason")
    deny_out = json.loads(capsys.readouterr().out)
    assert deny_out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    with pytest.raises(SystemExit):
        gate_check.allow()
    allow_out = json.loads(capsys.readouterr().out)
    assert allow_out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"


def test_post_write_review_emit_stays_posttooluse(capsys) -> None:
    """The counterpart reviewer must stay labeled PostToolUse, never Pre."""
    post_write_review.emit("finding")
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"


def test_emit_deduplicates_identical_content_within_a_session(capsys) -> None:
    """A repeat additionalContext string in one session prints only once."""
    post_write_review.emit("same finding", session_id="s1")
    first = capsys.readouterr().out
    post_write_review.emit("same finding", session_id="s1")
    second = capsys.readouterr().out
    assert first != ""
    assert second == ""


def test_emit_does_not_dedupe_across_sessions(capsys) -> None:
    """The fingerprint is scoped per session_id, not shared globally."""
    post_write_review.emit("same finding", session_id="s1")
    capsys.readouterr()
    post_write_review.emit("same finding", session_id="s2")
    assert capsys.readouterr().out != ""


# MARKDOWN_GLOBS (post-write-review.py): markdown prose runs through the
# same mechanical 401 register scan as source comments, via a virtual
# marker prefix, outside frontmatter and fenced code.


def _run_main_and_capture(payload, monkeypatch) -> str:
    import contextlib
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        post_write_review.main()
    return buf.getvalue()


def _edit_payload(target, new_string: str) -> dict:
    return {
        "tool_name": "Edit",
        "session_id": "s1",
        "tool_input": {
            "file_path": str(target),
            "old_string": "x",
            "new_string": new_string,
        },
    }


def test_main_flags_bare_pronoun_in_markdown_prose(
    tmp_path, monkeypatch
) -> None:
    """A bare-pronoun violation in ordinary .md prose is now caught."""
    bare = "it"
    target = tmp_path / "notes.md"
    target.write_text("Retrying " + bare + " fixes the flaky case.\n")
    out = _run_main_and_capture(_edit_payload(target, bare), monkeypatch)
    assert "bare pronoun 'it'" in out


def test_main_flags_bare_pronoun_in_markdown_heading(
    tmp_path, monkeypatch
) -> None:
    """A markdown heading is prose too, and is scanned like any other line."""
    bare = "it"
    target = tmp_path / "notes.md"
    target.write_text("# Retrying " + bare + " fixes the flaky case\n")
    out = _run_main_and_capture(_edit_payload(target, bare), monkeypatch)
    assert "bare pronoun 'it'" in out


def test_main_skips_markdown_frontmatter(tmp_path, monkeypatch) -> None:
    """YAML frontmatter is not prose and stays outside the register scan."""
    bare = "it"
    target = tmp_path / "notes.md"
    target.write_text(
        "---\n" + "id: " + bare + "\n" + "---\n" + "Body text is clean here.\n"
    )
    out = _run_main_and_capture(_edit_payload(target, bare), monkeypatch)
    assert "bare pronoun 'it'" not in out


def test_main_skips_markdown_fenced_code(tmp_path, monkeypatch) -> None:
    """A fenced code sample is not prose and stays outside the register scan."""
    bare = "it"
    target = tmp_path / "notes.md"
    target.write_text(
        "Body text is clean here.\n\n"
        "```python\n"
        "x = " + bare + "  # " + bare + " does something\n"
        "```\n"
    )
    out = _run_main_and_capture(_edit_payload(target, bare), monkeypatch)
    assert "bare pronoun 'it'" not in out


# Conversational output never reaches PostToolUse: a plain reply carries
# no Edit/Write tool call for this hook to scan.


def test_main_ignores_non_write_tool_calls(monkeypatch, capsys) -> None:
    """A non-Edit/Write tool_name, such as a dialogue-only tool, is a no-op."""
    import io

    payload = {
        "tool_name": "AskUserQuestion",
        "session_id": "s1",
        "tool_input": {"file_path": "/tmp/should-not-matter.md"},
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    post_write_review.main()
    assert capsys.readouterr().out == ""
