"""Tests for Cursor `.mdc` shells derived from scenario adapters."""

from __future__ import annotations

from pathlib import Path

import pytest
from adapter_install.cursor_mdc import LANGUAGES_REL
from adapter_install.cursor_mdc import iter_cursor_scenarios
from adapter_install.cursor_mdc import parse_cursor_scenario
from adapter_install.cursor_mdc import parse_languages_scenarios
from adapter_install.cursor_mdc import render_cursor_mdc
from adapter_install.install import MODE_CURSOR_MDC
from adapter_install.install import SPECS
from adapter_install.install import execute_apply
from adapter_install.install import inspect_spec_drift
from adapter_install.install import reconcile_spec
from adapter_install.install import render_expected_payload
from adapter_install.install import resolve_dest
from adapter_install.install import resolve_source
from adapter_install.install import validate_dest_rel


_LANGUAGE_IDS = (
    "markdown",
    "typescript",
    "go",
    "hcl",
    "yaml",
    "notebook",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _scenarios_dir() -> Path:
    return _repo_root() / "hooks" / "criteria" / "2_context" / "scenarios"


def test_parse_cursor_accepts_two_space_load_and_nested_globs() -> None:
    """A two-space list and a nested cursor mapping still yield globs."""
    text = (
        "---\n"
        "id: markdown\n"
        "load:\n"
        "  - references/lang-md.md\n"
        "adapters:\n"
        "  cursor:\n"
        "    surface: mdc\n"
        '    globs: "**/*.md,**/*.mdx"\n'
        "---\n"
        "body\n"
    )
    parsed = parse_cursor_scenario(text)
    assert parsed is not None
    assert parsed.globs == "**/*.md,**/*.mdx"
    assert parsed.load == ("references/lang-md.md",)


def test_parse_cursor_missing_globs_raises() -> None:
    """A cursor key without globs MUST fail closed rather than skip."""
    text = (
        "---\n"
        "id: markdown\n"
        "load:\n"
        "    - references/lang-md.md\n"
        "adapters:\n"
        "    cursor: { surface: mdc }\n"
        "---\n"
        "body\n"
    )
    with pytest.raises(ValueError, match="missing globs"):
        parse_cursor_scenario(text)


def test_language_scenarios_declare_cursor_globs() -> None:
    """Language dispatch entries MUST declare globs and load paths."""
    lang_file = _scenarios_dir() / "languages.md"
    parsed_langs = {
        s.scenario_id: s
        for s in parse_languages_scenarios(
            lang_file.read_text(encoding="utf-8")
        )
    }
    assert set(parsed_langs) == set(_LANGUAGE_IDS)
    for scenario_id in _LANGUAGE_IDS:
        parsed = parsed_langs[scenario_id]
        assert parsed.scenario_id == scenario_id
        assert parsed.globs
        assert parsed.load
        for item in parsed.load:
            assert (_repo_root() / "hooks" / "criteria" / item).is_file()


def test_prompt_scenarios_do_not_declare_cursor() -> None:
    """Prompt-semantic scenarios stay off the Cursor glob surface."""
    for name in (
        "reply.md",
        "commit.md",
        "merge-request-compose.md",
        "merge-request-review.md",
        "task-translation.md",
        "citation.md",
        "local-mutate.md",
        "external-write.md",
        "assistant-output.md",
        "notebook.md",
    ):
        text = (_scenarios_dir() / name).read_text(encoding="utf-8")
        assert parse_cursor_scenario(text) is None, name
    routing_text = (
        _repo_root() / "hooks" / "criteria" / "README.md"
    ).read_text(encoding="utf-8")
    assert parse_cursor_scenario(routing_text) is None


def test_iter_cursor_scenarios_scenario_markdown_is_absent_from_rows() -> None:
    """Cursor inbound is the languages table. Scenario markdown is excluded."""
    rows = iter_cursor_scenarios(_repo_root())
    assert {rel for rel, _parsed in rows} == {LANGUAGES_REL}
    assert {parsed.scenario_id for _rel, parsed in rows} == set(_LANGUAGE_IDS)


def test_cursor_specs_are_one_to_one_with_scenarios() -> None:
    """Each languages.md entry becomes one allow-listed lang-{id}.mdc dest."""
    cursor_specs = [s for s in SPECS if s.mode == MODE_CURSOR_MDC]
    assert {s.scenario_id for s in cursor_specs} == set(_LANGUAGE_IDS)
    for spec in cursor_specs:
        assert spec.source == LANGUAGES_REL
        scenario_id = spec.scenario_id
        assert scenario_id is not None
        assert spec.dest == f".cursor/rules/lang-{scenario_id}.mdc"
        source_path = _repo_root() / spec.source
        assert source_path.is_file()
        body = render_cursor_mdc(source_path, scenario_id=scenario_id)
        assert body.startswith(b"---\n")


def test_render_cursor_mdc_unknown_scenario_id_raises_value_error() -> None:
    """An unknown id MUST fail closed instead of selecting the first entry."""
    lang_file = _scenarios_dir() / "languages.md"
    with pytest.raises(ValueError, match="no cursor adapter"):
        render_cursor_mdc(lang_file, scenario_id="not-a-language")


def test_render_cursor_mdc_missing_scenario_id_raises_value_error() -> None:
    """A missing scenario_id MUST fail closed."""
    lang_file = _scenarios_dir() / "languages.md"
    with pytest.raises(ValueError, match="missing scenario_id"):
        render_cursor_mdc(lang_file, scenario_id="")


def test_render_cursor_mdc_non_languages_path_raises_value_error() -> None:
    """Render MUST reject a source which is not the languages table."""
    notebook = _scenarios_dir() / "notebook.md"
    with pytest.raises(ValueError, match="requires languages.md"):
        render_cursor_mdc(notebook, scenario_id="notebook")


def test_render_expected_payload_missing_scenario_id_raises_value_error() -> (
    None
):
    """Cursor mode MUST require scenario_id on the spec rather than dest."""
    source = _repo_root() / LANGUAGES_REL
    with pytest.raises(ValueError, match="missing scenario_id"):
        render_expected_payload(source, MODE_CURSOR_MDC)


def test_render_cursor_mdc_notebook_entry_cites_ipynb_load() -> None:
    """The notebook dispatch row still renders the ipynb glob and load."""
    body = render_cursor_mdc(
        _scenarios_dir() / "languages.md", scenario_id="notebook"
    ).decode("utf-8")
    assert 'globs: "**/*.ipynb"' in body
    assert "@~/.agents/criteria/4_L2-trigger/ipynb.md" in body


def test_rendered_mdc_cites_load_paths_and_omits_l2() -> None:
    """The `.mdc` body cites `load:` files and MUST NOT copy L2 prose."""
    lang_file = _scenarios_dir() / "languages.md"
    body = render_cursor_mdc(lang_file, scenario_id="typescript").decode(
        "utf-8"
    )
    assert "alwaysApply: false" in body
    assert 'globs: "**/*.ts,**/*.tsx"' in body
    assert "@~/.agents/criteria/4_L2-trigger/typescript.md" in body
    lang_ts = (
        _repo_root() / "hooks" / "criteria" / "4_L2-trigger" / "typescript.md"
    ).read_text(encoding="utf-8")
    assert "jQuery" in lang_ts
    assert "jQuery" not in body
    assert "AGENT_CRITERIA" not in body
    assert "The Helpful Assistant" not in body


def test_apply_writes_rendered_mdc_not_scenario_bytes(
    tmp_path: Path,
) -> None:
    """Apply writes rendered bytes. Dest is a regular file, not a symlink."""
    home = tmp_path / "home"
    home.mkdir()
    assert execute_apply(_repo_root(), home) == 0
    dest = home / ".cursor" / "rules" / "lang-typescript.mdc"
    assert dest.is_file()
    assert not dest.is_symlink()
    expected = render_cursor_mdc(
        _scenarios_dir() / "languages.md", scenario_id="typescript"
    )
    assert dest.read_bytes() == expected
    scenario_bytes = (_scenarios_dir() / "languages.md").read_bytes()
    assert dest.read_bytes() != scenario_bytes
    assert not (home / ".cursor" / "settings.json").exists()
    distill = (_repo_root() / "rules" / "AGENT_CRITERIA.md").read_bytes()
    for spec in SPECS:
        if not spec.dest.startswith(".cursor/"):
            continue
        payload = resolve_dest(home, spec).read_bytes()
        assert payload != distill


def test_cursor_mdc_copy_differs_is_overwritten(tmp_path: Path) -> None:
    """A drifted `.mdc` is copy-differs. Apply overwrites from render."""
    home = tmp_path / "home"
    spec = next(s for s in SPECS if s.dest == ".cursor/rules/lang-go.mdc")
    dest = resolve_dest(home, spec)
    dest.parent.mkdir(parents=True)
    dest.write_text("owner edit\n", encoding="utf-8")
    assert inspect_spec_drift(_repo_root(), home, spec) == "copy-differs"
    assert reconcile_spec(_repo_root(), home, spec) == "applied"
    source = resolve_source(_repo_root(), spec)
    assert dest.read_bytes() == render_cursor_mdc(source, scenario_id="go")


def test_cursor_home_is_protected() -> None:
    """The installer MUST NOT replace `~/.cursor` as a whole."""
    with pytest.raises(ValueError, match="protected dest"):
        validate_dest_rel(".cursor")
    with pytest.raises(ValueError, match="dest not in allow-list"):
        validate_dest_rel(".cursor/settings.json")
    with pytest.raises(ValueError, match="dest not in allow-list"):
        validate_dest_rel(".cursor/rules/always-on.mdc")


def test_adapter_install_package_has_no_shell_copy() -> None:
    """Adapter install MUST NOT spawn a shell or call shutil copy helpers."""
    package = _repo_root() / "hooks" / "adapter_install"
    forbidden = (
        "subprocess",
        "os.system",
        "os.popen",
        "shutil.",
        "rsync",
        "Popen",
    )
    for path in package.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} contains {token}"
        assert "cp -" not in text
        assert "ln -" not in text
