"""Tests for Cursor `.mdc` shells derived from scenario adapters."""

from __future__ import annotations

from pathlib import Path

import pytest
from adapter_install.cursor_mdc import parse_cursor_scenario
from adapter_install.cursor_mdc import render_cursor_mdc
from adapter_install.install import MODE_CURSOR_MDC
from adapter_install.install import SPECS
from adapter_install.install import apply_spec
from adapter_install.install import check_spec
from adapter_install.install import resolve_dest
from adapter_install.install import run_apply
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


def _criteria_file(scenario_id: str) -> Path:
    return _repo_root() / "hooks" / "criteria" / f"{scenario_id}.md"


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
    """Section 1 language scenarios MUST declare adapters.cursor."""
    for scenario_id in _LANGUAGE_IDS:
        parsed = parse_cursor_scenario(
            _criteria_file(scenario_id).read_text(encoding="utf-8")
        )
        assert parsed is not None, scenario_id
        assert parsed.scenario_id == scenario_id
        assert parsed.globs
        assert parsed.load
        for item in parsed.load:
            assert item.startswith("references/")
            assert (_repo_root() / "hooks" / "criteria" / item).is_file()


def test_prompt_scenarios_do_not_declare_cursor() -> None:
    """Prompt-semantic scenarios stay off the Cursor glob surface."""
    for name in (
        "reply.md",
        "commit.md",
        "mr.md",
        "translate.md",
        "citation.md",
        "local-mutate.md",
        "external-write.md",
        "assistant-output.md",
        "00-routing.md",
    ):
        text = (_repo_root() / "hooks" / "criteria" / name).read_text(
            encoding="utf-8"
        )
        assert parse_cursor_scenario(text) is None, name


def test_cursor_specs_are_one_to_one_with_scenarios() -> None:
    """Each adapters.cursor row becomes one allow-listed `.mdc` dest."""
    cursor_specs = [s for s in SPECS if s.mode == MODE_CURSOR_MDC]
    assert {s.dest for s in cursor_specs} == {
        f".cursor/rules/lang-{scenario_id}.mdc" for scenario_id in _LANGUAGE_IDS
    }
    for spec in cursor_specs:
        parsed = parse_cursor_scenario(
            (_repo_root() / spec.source).read_text(encoding="utf-8")
        )
        assert parsed is not None
        assert spec.source == f"hooks/criteria/{parsed.scenario_id}.md"
        assert spec.dest == f".cursor/rules/lang-{parsed.scenario_id}.mdc"


def test_rendered_mdc_cites_load_paths_and_omits_l2() -> None:
    """The `.mdc` body cites `load:` files and MUST NOT copy L2 prose."""
    scenario = _criteria_file("typescript")
    parsed = parse_cursor_scenario(scenario.read_text(encoding="utf-8"))
    assert parsed is not None
    body = render_cursor_mdc(scenario).decode("utf-8")
    assert "alwaysApply: false" in body
    assert f'globs: "{parsed.globs}"' in body
    assert "**/*.ts,**/*.tsx" in body
    for item in parsed.load:
        assert f"@~/.agents/criteria/{item}" in body
    lang_ts = (
        _repo_root() / "hooks" / "criteria" / "references" / "lang-ts.md"
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
    assert run_apply(_repo_root(), home) == 0
    dest = home / ".cursor" / "rules" / "lang-typescript.mdc"
    assert dest.is_file()
    assert not dest.is_symlink()
    assert dest.read_bytes() == render_cursor_mdc(_criteria_file("typescript"))
    scenario_bytes = _criteria_file("typescript").read_bytes()
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
    assert check_spec(_repo_root(), home, spec) == "copy-differs"
    assert apply_spec(_repo_root(), home, spec) == "applied"
    assert dest.read_bytes() == render_cursor_mdc(_criteria_file("go"))


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
