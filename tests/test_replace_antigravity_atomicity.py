"""Rollback and preflight atomicity tests for the replace module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import replace


def _make_staging(base: Path, name: str, content: bytes) -> Path:
    staging = base / f".{name}.staging"
    (staging / "tree").mkdir(parents=True)
    (staging / "tree" / name).write_bytes(content)
    return staging


def test_commit_product_rolls_back_when_move_fails(tmp_path: Path) -> None:
    """A failed move restores the original live root from the backup."""
    root = tmp_path / "antigravity-ide"
    root.mkdir()
    (root / "antigravity-ide").write_bytes(b"old")
    staging = _make_staging(tmp_path, "antigravity-ide", b"new")

    with (
        patch("replace.stop_main_pid"),
        patch("shutil.move", side_effect=OSError("disk full")),
    ):
        with pytest.raises(OSError, match="disk full"):
            replace.commit_product("ide", staging, root, "1.0.0", False)

    assert (root / "antigravity-ide").read_bytes() == b"old"
    assert not (tmp_path / "antigravity-ide.bak.1.0.0").exists()


def test_commit_product_fresh_install_move_failure(tmp_path: Path) -> None:
    """Without a prior root, a failed move leaves no partial install."""
    root = tmp_path / "antigravity"
    staging = _make_staging(tmp_path, "antigravity", b"new")

    with (
        patch("replace.stop_main_pid"),
        patch("shutil.move", side_effect=OSError("boom")),
    ):
        with pytest.raises(OSError, match="boom"):
            replace.commit_product("hub", staging, root, "0.0.0", False)

    assert not root.exists()


def _payload(**overrides: object) -> dict:
    base: dict = {
        "op": "replace",
        "products": ["ide", "hub"],
        "ide_url": "https://dl.google.com/ide.tar.gz",
        "ide_root": "/opt/antigravity-test/ide",
        "old_ide_version": "1.0.0",
        "hub_url": "https://dl.google.com/hub.tar.gz",
        "hub_root": "/opt/antigravity-test/hub",
        "old_hub_version": "1.0.0",
    }
    base.update(overrides)
    return base


def test_build_jobs_validates_all_products_first() -> None:
    """An invalid second product fails before any job is returned."""
    payload = _payload(hub_url="https://evil.example.com/hub.tar.gz")
    with pytest.raises(ValueError, match="is not in official hosts"):
        replace.build_jobs(payload)


def test_build_jobs_rejects_bad_version_and_root() -> None:
    """Bad version or root in any product aborts job construction."""
    with pytest.raises(ValueError, match="Invalid version string"):
        replace.build_jobs(_payload(old_hub_version="../x"))
    with pytest.raises(ValueError, match="outside allowed"):
        replace.build_jobs(_payload(ide_root="/etc/ide"))
    with pytest.raises(ValueError, match="Invalid ide_sha256"):
        replace.build_jobs(_payload(ide_sha256="zz"))


def test_main_stage_failure_touches_no_live_root(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A failing second download occurs before any commit is attempted."""
    calls: list[str] = []

    def fake_stage(url: str, root: Path, sha256: str | None) -> Path:
        calls.append(url)
        if "hub" in url:
            raise RuntimeError("download failed")
        return Path("/nonexistent-staging")

    with (
        patch("sys.argv", ["replace.py", "--payload", json.dumps(_payload())]),
        patch("replace.stage_product", side_effect=fake_stage),
        patch("replace.commit_product") as mock_commit,
        patch("shutil.rmtree"),
    ):
        exit_code = replace.main()

    assert exit_code == 1
    mock_commit.assert_not_called()
    assert len(calls) == 2
    res = json.loads(capsys.readouterr().out)
    assert res["ok"] is False
    assert res["backups"] == []
