"""Tests for resolving a context docs_root from contexts.toml."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from context_docs.resolve import main
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
