"""Tests for resolving a context docs_root from contexts.toml."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from context_docs.resolve import main
from context_docs.resolve import resolve_catalog_path
from context_docs.resolve import resolve_catalog_skill_sources
from context_docs.resolve import resolve_catalog_socket
from context_docs.resolve import resolve_context_docs_root


def _write_files(root: Path, names: tuple[str, ...]) -> None:
    """Create names as files directly under root."""
    root.mkdir(parents=True)
    for name in names:
        (root / name).write_text(name + "\n", encoding="utf-8")


def _write_section(
    path: Path, context_id: str, docs_root: str, required: tuple[str, ...]
) -> None:
    """Append one context table to path."""
    listed = ", ".join(f'"{name}"' for name in required)
    block = (
        f"[context.{context_id}]\n"
        f'docs_root = "{docs_root}"\n'
        f"required = [{listed}]\n"
    )
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    path.write_text(existing + block, encoding="utf-8")


def test_resolve_context_docs_root_with_required_files_returns_absolute_path(
    tmp_path: Path,
) -> None:
    """Listed required files yield ok and the absolute docs_root."""
    docs = tmp_path / "contract"
    names = ("alpha.md", "beta.md")
    _write_files(docs, names)
    config = tmp_path / "contexts.toml"
    _write_section(config, "sample", str(docs), names)
    result = resolve_context_docs_root(config, "sample")
    assert result["ok"] is True
    assert result["context_id"] == "sample"
    assert result["error"] is None
    assert result["docs_root"] == str(docs.resolve())


def test_resolve_context_docs_root_reads_only_the_named_section(
    tmp_path: Path,
) -> None:
    """Each context id returns the docs_root of that table alone."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_files(first, ("alpha.md",))
    _write_files(second, ("beta.md",))
    config = tmp_path / "contexts.toml"
    _write_section(config, "one", str(first), ("alpha.md",))
    _write_section(config, "two", str(second), ("beta.md",))
    one = resolve_context_docs_root(config, "one")
    two = resolve_context_docs_root(config, "two")
    assert one["docs_root"] == str(first.resolve())
    assert two["docs_root"] == str(second.resolve())


def test_resolve_context_docs_root_with_missing_config_returns_ok_false(
    tmp_path: Path,
) -> None:
    """An absent contexts.toml yields ok false."""
    result = resolve_context_docs_root(tmp_path / "missing.toml", "sample")
    assert result["ok"] is False
    assert result["context_id"] == "sample"
    assert result["docs_root"] is None
    assert result["error"] == "config file is absent"


def test_resolve_context_docs_root_with_missing_directory_returns_ok_false(
    tmp_path: Path,
) -> None:
    """A docs_root path that is not a directory yields ok false."""
    config = tmp_path / "contexts.toml"
    _write_section(config, "sample", str(tmp_path / "absent"), ("alpha.md",))
    result = resolve_context_docs_root(config, "sample")
    assert result["ok"] is False
    assert result["docs_root"] is None
    assert result["error"] == "docs_root directory is absent"


def test_resolve_context_docs_root_when_one_file_absent_returns_ok_false(
    tmp_path: Path,
) -> None:
    """A docs_root missing one listed file yields ok false."""
    docs = tmp_path / "contract"
    _write_files(docs, ("alpha.md", "beta.md"))
    (docs / "beta.md").unlink()
    config = tmp_path / "contexts.toml"
    _write_section(config, "sample", str(docs), ("alpha.md", "beta.md"))
    result = resolve_context_docs_root(config, "sample")
    assert result["ok"] is False
    assert result["docs_root"] is None
    assert result["error"] == "required file is absent: beta.md"


def test_resolve_context_docs_root_with_empty_required_returns_ok_true(
    tmp_path: Path,
) -> None:
    """An empty required list resolves successfully without anchor files."""
    docs = tmp_path / "contract"
    docs.mkdir()
    config = tmp_path / "contexts.toml"
    _write_section(config, "sample", str(docs), ())
    result = resolve_context_docs_root(config, "sample")
    assert result["ok"] is True
    assert result["context_id"] == "sample"
    assert result["error"] is None
    assert result["docs_root"] == str(docs.resolve())


def test_main_with_missing_config_exits_1_and_prints_ok_false(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI prints one JSON object and returns 1 when config is absent."""
    code = main(
        ["--context", "sample", "--config", str(tmp_path / "missing.toml")]
    )
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["context_id"] == "sample"
    assert payload["docs_root"] is None
    assert payload["error"] == "config file is absent"


def test_resolve_catalog_socket_with_listed_skill_returns_skills_path(
    tmp_path: Path,
) -> None:
    """A socket whose skill is listed on the pack returns that skill."""
    skills = tmp_path / "skills"
    skills.mkdir()
    config = tmp_path / "contexts.toml"
    config.write_text(
        "[socket.media-sequence]\n"
        'pack = "sample"\n'
        'skill = "skill-sample"\n'
        "\n"
        "[context.sample]\n"
        f'skills_path = "{skills}"\n'
        'skills = ["skill-sample"]\n',
        encoding="utf-8",
    )
    result = resolve_catalog_socket(config, "media-sequence")
    assert result["ok"] is True
    assert result["socket_id"] == "media-sequence"
    assert result["pack"] == "sample"
    assert result["skill"] == "skill-sample"
    assert result["skills_path"] == str(skills.resolve())
    assert result["error"] is None


def test_resolve_catalog_socket_when_skill_unlisted_returns_ok_false(
    tmp_path: Path,
) -> None:
    """A socket skill absent from the pack list yields ok false."""
    skills = tmp_path / "skills"
    skills.mkdir()
    config = tmp_path / "contexts.toml"
    config.write_text(
        "[socket.task-fill]\n"
        'pack = "sample"\n'
        'skill = "skill-other"\n'
        "\n"
        "[context.sample]\n"
        f'skills_path = "{skills}"\n'
        'skills = ["skill-sample"]\n',
        encoding="utf-8",
    )
    result = resolve_catalog_socket(config, "task-fill")
    assert result["ok"] is False
    assert result["skill"] is None
    assert result["error"] == "socket.task-fill.skill is absent from the pack"


def test_resolve_context_docs_root_relative_path_resolves_against_workspace(
    tmp_path: Path,
) -> None:
    """Relative docs_root in .agents/contexts.toml resolves correctly."""
    workspace = tmp_path / "my-workspace"
    agents_dir = workspace / ".agents"
    agents_dir.mkdir(parents=True)
    contract_dir = workspace / "docs" / "contract"
    _write_files(contract_dir, ("alpha.md",))
    config = agents_dir / "contexts.toml"
    config.write_text(
        "[context.sample]\n"
        'docs_root = "docs/contract"\n'
        'required = ["alpha.md"]\n',
        encoding="utf-8",
    )
    result = resolve_context_docs_root(config, "sample")
    assert result["ok"] is True
    assert result["docs_root"] == str(contract_dir.resolve())


def test_resolve_context_docs_root_escaping_workspace_returns_ok_false(
    tmp_path: Path,
) -> None:
    """A relative docs_root escaping workspace root is rejected."""
    workspace = tmp_path / "my-workspace"
    agents_dir = workspace / ".agents"
    agents_dir.mkdir(parents=True)
    outside_dir = tmp_path / "outside_contract"
    _write_files(outside_dir, ("alpha.md",))
    config = agents_dir / "contexts.toml"
    config.write_text(
        "[context.sample]\n"
        'docs_root = "../../outside_contract"\n'
        'required = ["alpha.md"]\n',
        encoding="utf-8",
    )
    result = resolve_context_docs_root(config, "sample")
    assert result["ok"] is False
    assert result["docs_root"] is None
    assert result["error"] == "docs_root directory is absent"


def test_resolve_catalog_path_with_workspace_opt_in(tmp_path: Path) -> None:
    """Explicit workspace_root with .agents/contexts.toml returns that file."""
    criteria_root = tmp_path / "criteria"
    (criteria_root / "config").mkdir(parents=True)
    (criteria_root / "config" / "contexts.toml").write_text(
        "", encoding="utf-8"
    )
    workspace = tmp_path / "workspace"
    agents_dir = workspace / ".agents"
    agents_dir.mkdir(parents=True)
    ws_catalog = agents_dir / "contexts.toml"
    ws_catalog.write_text("[context.ws]\n", encoding="utf-8")

    found = resolve_catalog_path(criteria_root, workspace_root=workspace)
    assert found == ws_catalog


def test_resolve_catalog_path_with_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AGENT_WORKSPACE_ROOT env var opts in to workspace catalog discovery."""
    criteria_root = tmp_path / "criteria"
    (criteria_root / "config").mkdir(parents=True)
    (criteria_root / "config" / "contexts.toml").write_text(
        "", encoding="utf-8"
    )
    workspace = tmp_path / "workspace"
    agents_dir = workspace / ".agents"
    agents_dir.mkdir(parents=True)
    ws_catalog = agents_dir / "contexts.toml"
    ws_catalog.write_text("[context.ws]\n", encoding="utf-8")

    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    found = resolve_catalog_path(criteria_root)
    assert found == ws_catalog


def test_resolve_catalog_path_fallback_to_user_home_agents(
    tmp_path: Path,
) -> None:
    """When workspace has no catalog, falls back to ~/.agents/contexts.toml."""
    criteria_root = tmp_path / "criteria"
    (criteria_root / "config").mkdir(parents=True)
    (criteria_root / "config" / "contexts.toml").write_text(
        "", encoding="utf-8"
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home_dir = tmp_path / "home"
    agents_dir = home_dir / ".agents"
    agents_dir.mkdir(parents=True)
    home_catalog = agents_dir / "contexts.toml"
    home_catalog.write_text("[context.home]\n", encoding="utf-8")

    found = resolve_catalog_path(
        criteria_root, workspace_root=workspace, home_root=home_dir
    )
    assert found == home_catalog


def test_resolve_catalog_path_fallback_to_user_home_adapter_configs(
    tmp_path: Path,
) -> None:
    """When ~/.agents has no catalog, checks adapter fallbacks in order."""
    criteria_root = tmp_path / "criteria"
    (criteria_root / "config").mkdir(parents=True)
    (criteria_root / "config" / "contexts.toml").write_text(
        "", encoding="utf-8"
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home_dir = tmp_path / "home"
    gemini_dir = home_dir / ".gemini"
    gemini_dir.mkdir(parents=True)
    gemini_catalog = gemini_dir / "contexts.toml"
    gemini_catalog.write_text("[context.gemini]\n", encoding="utf-8")

    found = resolve_catalog_path(
        criteria_root, workspace_root=workspace, home_root=home_dir
    )
    assert found == gemini_catalog


def test_resolve_catalog_path_fallback_to_criteria_root_when_all_absent(
    tmp_path: Path,
) -> None:
    """When all catalogs are absent, falls back to criteria repository."""
    criteria_root = tmp_path / "criteria"
    repo_catalog = criteria_root / "config" / "contexts.toml"
    repo_catalog.parent.mkdir(parents=True)
    repo_catalog.write_text("", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    found = resolve_catalog_path(
        criteria_root, workspace_root=workspace, home_root=home_dir
    )
    assert found == repo_catalog


def test_main_with_workspace_root_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI accepts --workspace-root and resolves against the workspace."""
    workspace = tmp_path / "workspace"
    agents_dir = workspace / ".agents"
    agents_dir.mkdir(parents=True)
    contract_dir = workspace / "contract"
    _write_files(contract_dir, ("alpha.md",))
    ws_catalog = agents_dir / "contexts.toml"
    ws_catalog.write_text(
        '[context.ws]\ndocs_root = "contract"\nrequired = ["alpha.md"]\n',
        encoding="utf-8",
    )
    code = main(["--context", "ws", "--workspace-root", str(workspace)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["context_id"] == "ws"
    assert payload["docs_root"] == str(contract_dir.resolve())


@pytest.mark.parametrize("scenario", ["valid", "traversal"])
@pytest.mark.parametrize("target", ["socket", "skill_sources"])
def test_resolve_catalog_skills_path_matrix(
    tmp_path: Path, scenario: str, target: str
) -> None:
    """Skills path resolves against workspace and rejects traversal escapes."""
    workspace = tmp_path / "workspace"
    agents_dir = workspace / ".agents"
    agents_dir.mkdir(parents=True)
    outside_dir = tmp_path / "outside_skills"
    outside_dir.mkdir(parents=True)
    (outside_dir / "skill-sample").mkdir(parents=True)

    skills_dir = workspace / "custom-skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "skill-sample").mkdir(parents=True)

    is_valid = scenario == "valid"
    raw_path = "custom-skills" if is_valid else "../../outside_skills"

    config = agents_dir / "contexts.toml"
    config.write_text(
        "[socket.media-sequence]\n"
        'pack = "ws-pack"\n'
        'skill = "skill-sample"\n'
        "\n"
        "[context.ws-pack]\n"
        f'skills_path = "{raw_path}"\n'
        'skills = ["skill-sample"]\n',
        encoding="utf-8",
    )

    if target == "socket":
        result = resolve_catalog_socket(config, "media-sequence")
        if is_valid:
            assert result["ok"] is True
            assert result["skills_path"] == str(skills_dir.resolve())
        else:
            assert result["ok"] is False
            assert result["skills_path"] is None
            assert result["error"] == "skills_path directory is absent"
    else:
        sources = resolve_catalog_skill_sources(config)
        if is_valid:
            assert isinstance(sources, dict)
            assert (
                sources.get("skill-sample")
                == (skills_dir / "skill-sample").resolve()
            )
        else:
            assert sources == "skills_path directory is absent"
