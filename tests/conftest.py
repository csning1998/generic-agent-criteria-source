"""Pytest path setup for hook and skill scripts."""

import sys
from pathlib import Path

import pytest


_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "hooks"))
sys.path.insert(0, str(_ROOT / "hooks/adapters/claude"))
sys.path.insert(0, str(_ROOT / "skills/skill-module-gitlab-mr-labels/scripts"))
sys.path.insert(0, str(_ROOT / "skills/skill-layer-update-antigravity/scripts"))
sys.path.insert(
    0, str(_ROOT / "skills/skill-module-update-antigravity/scripts")
)


@pytest.fixture(autouse=True)
def isolate_catalog_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Isolate catalog path to an empty file preventing host dependencies."""
    empty_catalog = tmp_path_factory.mktemp("catalog") / "contexts.toml"
    empty_catalog.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "adapter_install.install.resolve_catalog_path",
        lambda grok_root: empty_catalog,
    )
