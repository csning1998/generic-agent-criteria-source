"""Tests for harness adapter materialization."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from adapter_install.install import MODE_COPY
from adapter_install.install import MODE_SYMLINK
from adapter_install.install import SPECS
from adapter_install.install import AdapterSpec
from adapter_install.install import _clear_replaceable_tree
from adapter_install.install import inspect_all_specs
from adapter_install.install import inspect_spec_drift
from adapter_install.install import main
from adapter_install.install import reconcile_all_specs
from adapter_install.install import reconcile_spec
from adapter_install.install import resolve_dest
from adapter_install.install import resolve_grok_root
from adapter_install.install import resolve_source
from adapter_install.install import validate_dest_rel


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_resolve_grok_root_is_repo() -> None:
    """Package layout places grok root two parents above install.py."""
    assert resolve_grok_root() == _repo_root()


def test_validate_dest_rejects_escape() -> None:
    """Dest paths must stay under the allow-listed harness homes."""
    with pytest.raises(ValueError, match="dest escapes"):
        validate_dest_rel(".agents/../.ssh/id")
    with pytest.raises(ValueError, match="protected dest"):
        validate_dest_rel(".claude")
    with pytest.raises(ValueError, match="protected dest"):
        validate_dest_rel(".cursor")
    with pytest.raises(ValueError, match="dest not in allow-list"):
        validate_dest_rel(".claude/settings.json")
    with pytest.raises(ValueError, match="dest not in allow-list"):
        validate_dest_rel(".claude/credentials.json")
    with pytest.raises(ValueError, match="dest not in allow-list"):
        validate_dest_rel(".cursor/settings.json")
    with pytest.raises(ValueError, match="absolute dest"):
        validate_dest_rel("/tmp/CLAUDE.md")


def test_specs_sources_exist() -> None:
    """Every allow-listed source is present in this tree."""
    grok_root = _repo_root()
    for spec in SPECS:
        source = resolve_source(grok_root, spec)
        assert source.exists(), spec.source


def test_check_empty_home_is_drift(tmp_path: Path) -> None:
    """An empty home reports missing for every dest."""
    code = inspect_all_specs(_repo_root(), tmp_path)
    assert code == 1
    for spec in SPECS:
        assert inspect_spec_drift(_repo_root(), tmp_path, spec) == "missing"


def test_apply_then_check_clean(tmp_path: Path) -> None:
    """Apply writes allow-listed dests. A second check is clean."""
    home = tmp_path / "home"
    home.mkdir()
    assert reconcile_all_specs(_repo_root(), home) == 0
    assert inspect_all_specs(_repo_root(), home) == 0
    agents = home / ".agents" / "AGENTS.md"
    assert agents.is_symlink()
    assert (
        agents.resolve()
        == (_repo_root() / "rules" / "AGENT_CRITERIA.md").resolve()
    )
    claude = home / ".claude" / "CLAUDE.md"
    assert claude.is_file()
    assert not claude.is_symlink()
    source = _repo_root() / "hooks" / "adapters" / "claude" / "CLAUDE.md"
    assert claude.read_bytes() == source.read_bytes()
    skills = home / ".agents" / "skills"
    assert skills.is_symlink()
    assert (skills / "translate" / "SKILL.md").is_file()
    criteria = home / ".agents" / "criteria"
    assert criteria.is_symlink()
    assert (criteria / "README.md").is_file()
    principles = home / ".agents" / "ENGINEERING_PRINCIPLES.md"
    assert principles.is_symlink()
    assert not (home / ".claude" / "settings.json").exists()
    ts_mdc = home / ".cursor" / "rules" / "lang-typescript.mdc"
    assert ts_mdc.is_file()
    assert not ts_mdc.is_symlink()
    assert "alwaysApply: false" in ts_mdc.read_text(encoding="utf-8")
    assert not (home / ".cursor" / "settings.json").exists()


def test_reconcile_spec_with_identical_regular_file_replaces_with_symlink(
    tmp_path: Path,
) -> None:
    """A same-bytes regular dest is replaced by a symlink."""
    home = tmp_path / "home"
    dest = home / ".agents" / "AGENTS.md"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(
        (_repo_root() / "rules" / "AGENT_CRITERIA.md").read_bytes()
    )
    spec = SPECS[0]
    assert inspect_spec_drift(_repo_root(), home, spec) == "regular-same"
    assert reconcile_all_specs(_repo_root(), home) == 0
    assert dest.is_symlink()


def test_reconcile_all_specs_divergent_regular_file_aborts_without_mutation(
    tmp_path: Path,
) -> None:
    """Apply must not overwrite a dest whose bytes differ."""
    home = tmp_path / "home"
    dest = home / ".agents" / "AGENTS.md"
    dest.parent.mkdir(parents=True)
    dest.write_text("owner edit\n", encoding="utf-8")
    assert reconcile_all_specs(_repo_root(), home) == 1
    assert dest.read_text(encoding="utf-8") == "owner edit\n"
    assert not dest.is_symlink()


def test_reconcile_spec_with_divergent_file_aborts_without_overwrite(
    tmp_path: Path,
) -> None:
    """`reconcile_spec` itself must refuse a divergent file dest.

    `reconcile_all_specs` pre-screens every spec with `inspect_spec_drift`
    and aborts the whole run before calling `reconcile_spec` at all.
    `test_reconcile_all_specs_divergent_regular_file_aborts_without_mutation`
    never exercises `reconcile_spec`'s own `regular-differs` handling.
    This test calls `reconcile_spec` directly to close that blind spot
    for the file case, mirroring the directory-dest case.
    """
    home = tmp_path / "home"
    spec = next(s for s in SPECS if s.dest == ".agents/AGENTS.md")
    dest = resolve_dest(home, spec)
    dest.parent.mkdir(parents=True)
    dest.write_text("owner edit\n", encoding="utf-8")
    assert inspect_spec_drift(_repo_root(), home, spec) == "regular-differs"
    assert reconcile_spec(_repo_root(), home, spec) == "regular-differs"
    assert dest.read_text(encoding="utf-8") == "owner edit\n"
    assert not dest.is_symlink()


def test_reconcile_spec_with_divergent_directory_aborts_without_overwrite(
    tmp_path: Path,
) -> None:
    """Apply must not delete a directory dest whose contents differ.

    Regression guard for the `.grok/skills` symlink spec: a stray
    untracked file under a real directory dest (for example a leftover
    `__pycache__`) must abort that spec instead of silently deleting
    the owner's directory.
    """
    home = tmp_path / "home"
    spec = next(s for s in SPECS if s.dest == ".grok/skills")
    dest = resolve_dest(home, spec)
    dest.mkdir(parents=True)
    marker = dest / "owner-file.txt"
    marker.write_text("owner edit\n", encoding="utf-8")
    assert inspect_spec_drift(_repo_root(), home, spec) == "regular-differs"
    assert reconcile_spec(_repo_root(), home, spec) == "regular-differs"
    assert dest.is_dir()
    assert not dest.is_symlink()
    assert marker.read_text(encoding="utf-8") == "owner edit\n"


def test_identical_skills_directory_becomes_per_skill_symlinks(
    tmp_path: Path,
) -> None:
    """A same-bytes skills directory becomes one symlink per child."""
    home = tmp_path / "home"
    spec = next(s for s in SPECS if s.dest == ".grok/skills")
    dest = resolve_dest(home, spec)
    source = resolve_source(_repo_root(), spec)
    dest.parent.mkdir(parents=True)
    shutil.copytree(source, dest)
    assert inspect_spec_drift(_repo_root(), home, spec) == "incomplete"
    assert reconcile_spec(_repo_root(), home, spec) == "applied"
    assert dest.is_dir()
    assert not dest.is_symlink()
    for child in source.iterdir():
        link = dest / child.name
        assert link.is_symlink()
        assert link.resolve() == child.resolve()


def test_catalog_skill_links_beside_repo_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A catalog skills list adds one symlink and keeps repo skill links."""
    home = tmp_path / "home"
    pack_skill = tmp_path / "pack" / "skill-sample"
    pack_skill.mkdir(parents=True)
    (pack_skill / "SKILL.md").write_text("sample\n", encoding="utf-8")
    catalog = tmp_path / "contexts.toml"
    catalog.write_text(
        "[context.sample]\n"
        f'skills_path = "{pack_skill.parent}"\n'
        'skills = ["skill-sample"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "adapter_install.install.resolve_catalog_path",
        lambda grok_root: catalog,
    )
    spec = next(s for s in SPECS if s.dest == ".grok/skills")
    assert reconcile_spec(_repo_root(), home, spec) == "applied"
    external = home / ".grok" / "skills" / "skill-sample"
    repo_skill = home / ".grok" / "skills" / "skill-yt-dlp"
    assert external.is_symlink()
    assert external.resolve() == pack_skill.resolve()
    assert repo_skill.is_symlink()
    assert (
        repo_skill.resolve()
        == (_repo_root() / "skills" / "skill-yt-dlp").resolve()
    )


def test_contexts_toml_symlinks_for_grok_claude_and_agy() -> None:
    """The catalog file is one symlink for Grok, Claude, and Antigravity."""
    specs = [spec for spec in SPECS if spec.source == "config/contexts.toml"]
    dests = {spec.dest for spec in specs}
    assert dests == {
        ".grok/contexts.toml",
        ".claude/contexts.toml",
        ".gemini/contexts.toml",
    }
    assert all(spec.mode == MODE_SYMLINK for spec in specs)


def test_default_command_is_check(tmp_path: Path) -> None:
    """No verb runs check and does not write."""
    code = main(["--home", str(tmp_path), "--grok-root", str(_repo_root())])
    assert code == 1
    assert not (tmp_path / ".agents" / "AGENTS.md").exists()


def test_module_has_no_subprocess() -> None:
    """The installer must not spawn a shell."""
    source = Path(__file__).resolve().parents[1] / "hooks" / "adapter_install"
    for path in source.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "subprocess" not in text
        assert "os.system" not in text
        assert "os.popen" not in text
        assert "shutil." not in text
        assert "cp -" not in text
        assert "ln -" not in text


def test_resolve_dest_stays_under_home(tmp_path: Path) -> None:
    """Each dest resolves under the injected home."""
    for spec in SPECS:
        dest = resolve_dest(tmp_path, spec)
        dest.relative_to(tmp_path)


def test_remove_tree_does_not_follow_dir_symlink(tmp_path: Path) -> None:
    """A nested directory symlink is unlinked. Its target is not deleted."""
    victim = tmp_path / "victim"
    victim.mkdir()
    marker = victim / "keep.txt"
    marker.write_text("keep\n", encoding="utf-8")
    dest = tmp_path / "skills"
    dest.mkdir()
    (dest / "SKILL.md").write_text("x\n", encoding="utf-8")
    (dest / "escape").symlink_to(victim)
    _clear_replaceable_tree(dest)
    assert not dest.exists()
    assert marker.is_file()
    assert marker.read_text(encoding="utf-8") == "keep\n"


def test_symlink_home_component_aborts(tmp_path: Path) -> None:
    """A symlink ancestor of dest is dest-escapes. Apply writes nothing."""
    home = tmp_path / "home"
    home.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (home / ".claude").symlink_to(outside)
    assert reconcile_all_specs(_repo_root(), home) == 1
    assert not (outside / "CLAUDE.md").exists()
    assert not (home / ".agents" / "AGENTS.md").exists()


def test_apply_leaves_no_tmp_file_behind(tmp_path: Path) -> None:
    """A successful copy-mode apply leaves no `.name.tmp*` sibling."""
    home = tmp_path / "home"
    home.mkdir()
    assert reconcile_all_specs(_repo_root(), home) == 0
    hooks_dir = home / ".claude" / "hooks"
    leaked = [p for p in hooks_dir.iterdir() if ".tmp" in p.name]
    assert leaked == []


def test_reconcile_spec_cleans_up_tmp_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression for !16.

    A failure between write and replace must not leak the
    `.name.tmp*` scratch file at the destination.
    """
    grok_root = tmp_path / "grok"
    grok_root.mkdir()
    source = grok_root / "src.txt"
    source.write_text("hello\n")
    home = tmp_path / "home"
    dest_dir = home / ".claude"
    dest_dir.mkdir(parents=True)
    spec = AdapterSpec(source="src.txt", dest=".claude/target", mode=MODE_COPY)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("simulated os.replace failure")

    monkeypatch.setattr("adapter_install.install.os.replace", _boom)
    with pytest.raises(RuntimeError, match="simulated os.replace failure"):
        reconcile_spec(grok_root, home, spec)
    leaked = [p for p in dest_dir.iterdir() if ".tmp" in p.name]
    assert leaked == []
    assert not (dest_dir / "target").exists()


def test_reconcile_spec_dir_dest_under_copy_mode_is_left_untouched(
    tmp_path: Path,
) -> None:
    """A real directory at a copy-mode dest is reported unexpected-type.

    The state machine gates reconcile_spec before its atomic-replace branch,
    leaving no tree-removal path for a non-symlink directory dest.
    """
    grok_root = tmp_path / "grok"
    grok_root.mkdir()
    source = grok_root / "src.txt"
    source.write_text("hello\n")
    home = tmp_path / "home"
    dest = home / ".claude" / "target"
    dest.mkdir(parents=True)
    (dest / "inner.txt").write_text("leftover\n")
    spec = AdapterSpec(source="src.txt", dest=".claude/target", mode=MODE_COPY)

    result = reconcile_spec(grok_root, home, spec)

    assert result == "unexpected-type"
    assert dest.is_dir()
    assert (dest / "inner.txt").read_text() == "leftover\n"
