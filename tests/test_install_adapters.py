"""Tests for harness adapter materialization."""

from __future__ import annotations

from pathlib import Path

import pytest
from adapter_install.install import SPECS
from adapter_install.install import _remove_replaceable_tree
from adapter_install.install import check_spec
from adapter_install.install import infer_grok_root
from adapter_install.install import main
from adapter_install.install import resolve_dest
from adapter_install.install import resolve_source
from adapter_install.install import run_apply
from adapter_install.install import run_check
from adapter_install.install import validate_dest_rel


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_infer_grok_root_is_repo() -> None:
    """Package layout places grok root two parents above install.py."""
    assert infer_grok_root() == _repo_root()


def test_validate_dest_rejects_escape() -> None:
    """Dest paths must stay under the three harness homes."""
    with pytest.raises(ValueError, match="dest escapes"):
        validate_dest_rel(".agents/../.ssh/id")
    with pytest.raises(ValueError, match="protected dest"):
        validate_dest_rel(".claude")
    with pytest.raises(ValueError, match="dest not in allow-list"):
        validate_dest_rel(".claude/settings.json")
    with pytest.raises(ValueError, match="dest not in allow-list"):
        validate_dest_rel(".claude/credentials.json")
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
    code = run_check(_repo_root(), tmp_path)
    assert code == 1
    for spec in SPECS:
        assert check_spec(_repo_root(), tmp_path, spec) == "missing"


def test_apply_then_check_clean(tmp_path: Path) -> None:
    """Apply writes allow-listed dests. A second check is clean."""
    home = tmp_path / "home"
    home.mkdir()
    assert run_apply(_repo_root(), home) == 0
    assert run_check(_repo_root(), home) == 0
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
    assert (criteria / "00-routing.md").is_file()
    principles = home / ".agents" / "ENGINEERING_PRINCIPLES.md"
    assert principles.is_symlink()
    assert not (home / ".claude" / "settings.json").exists()


def test_identical_regular_file_becomes_symlink(tmp_path: Path) -> None:
    """A same-bytes regular dest is replaced by a symlink."""
    home = tmp_path / "home"
    dest = home / ".agents" / "AGENTS.md"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(
        (_repo_root() / "rules" / "AGENT_CRITERIA.md").read_bytes()
    )
    spec = SPECS[0]
    assert check_spec(_repo_root(), home, spec) == "regular-same"
    assert run_apply(_repo_root(), home) == 0
    assert dest.is_symlink()


def test_divergent_regular_file_aborts(tmp_path: Path) -> None:
    """Apply must not overwrite a dest whose bytes differ."""
    home = tmp_path / "home"
    dest = home / ".agents" / "AGENTS.md"
    dest.parent.mkdir(parents=True)
    dest.write_text("owner edit\n", encoding="utf-8")
    assert run_apply(_repo_root(), home) == 1
    assert dest.read_text(encoding="utf-8") == "owner edit\n"
    assert not dest.is_symlink()


def test_default_command_is_check(tmp_path: Path) -> None:
    """No verb runs check and does not write."""
    code = main(["--home", str(tmp_path), "--grok-root", str(_repo_root())])
    assert code == 1
    assert not (tmp_path / ".agents" / "AGENTS.md").exists()


def test_module_has_no_subprocess() -> None:
    """The installer must not spawn a shell."""
    source = Path(__file__).resolve().parents[1] / "hooks" / "adapter_install"
    text = (source / "install.py").read_text(encoding="utf-8")
    assert "subprocess" not in text
    assert "os.system" not in text
    assert "os.popen" not in text


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
    _remove_replaceable_tree(dest)
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
    assert run_apply(_repo_root(), home) == 1
    assert not (outside / "CLAUDE.md").exists()
    assert not (home / ".agents" / "AGENTS.md").exists()
