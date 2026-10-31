"""Staging cleanup, scheme, and archive symlink tests for replace."""

from __future__ import annotations

import json
import struct
from pathlib import Path
from unittest.mock import patch

import pytest
import replace


OFFICIAL_URL = "https://dl.google.com/a.tar.gz"


def test_validate_url_host_rejects_plain_http() -> None:
    """An http URL on an official host is rejected at validation time."""
    with pytest.raises(ValueError, match="Scheme must be https"):
        replace.validate_url_host("http://dl.google.com/a.tar.gz")


def _staging_of(root: Path) -> Path:
    return root.parent / f".{root.name}.staging"


def test_stage_product_cleans_up_on_download_failure(tmp_path: Path) -> None:
    """A failed download removes the staging directory."""
    root = tmp_path / "antigravity-ide"
    with patch("replace.download_archive", side_effect=RuntimeError("x")):
        with pytest.raises(RuntimeError):
            replace.stage_product(OFFICIAL_URL, root)
    assert not _staging_of(root).exists()


def test_stage_product_cleans_up_on_sha256_mismatch(tmp_path: Path) -> None:
    """A digest mismatch removes the partial archive and staging directory."""
    root = tmp_path / "antigravity-ide"

    def fake_download(url: str, dest: Path) -> None:
        dest.write_bytes(b"payload")

    with patch("replace.download_archive", side_effect=fake_download):
        with pytest.raises(ValueError, match="sha256 mismatch"):
            replace.stage_product(OFFICIAL_URL, root, "0" * 64)
    assert not _staging_of(root).exists()


def test_stage_product_cleans_up_on_tar_failure(tmp_path: Path) -> None:
    """A failing tar removes the staging directory."""
    root = tmp_path / "antigravity-ide"
    with (
        patch("replace.download_archive"),
        patch("subprocess.check_call", side_effect=OSError("tar")),
    ):
        with pytest.raises(OSError, match="tar"):
            replace.stage_product(OFFICIAL_URL, root)
    assert not _staging_of(root).exists()


def _stage_tree(base: Path) -> Path:
    staging = base / ".staging"
    (staging / "tree").mkdir(parents=True)
    return staging


def test_dangling_antigravity_icon_symlink_is_not_written(
    tmp_path: Path,
) -> None:
    """A dangling antigravity.png symlink never receives the copied icon."""
    root = tmp_path / "antigravity-ide"
    staging = _stage_tree(tmp_path)
    linux = staging / "tree/resources/app/resources/linux"
    linux.mkdir(parents=True)
    (linux / "code.png").write_bytes(b"icon")
    victim = tmp_path / "victim.txt"
    (linux / "antigravity.png").symlink_to(victim)

    with patch("replace.stop_main_pid"):
        replace.commit_product("ide", staging, root, "1.0.0", False)

    assert not victim.exists()


def test_symlinked_resources_dir_blocks_ide_icon_copy(tmp_path: Path) -> None:
    """A symlinked parent directory cannot redirect the icon copy."""
    root = tmp_path / "antigravity-ide"
    staging = _stage_tree(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "code.png").write_bytes(b"icon")
    app = staging / "tree/resources/app"
    app.mkdir(parents=True)
    (app / "resources").symlink_to(outside)

    with patch("replace.stop_main_pid"):
        replace.commit_product("ide", staging, root, "1.0.0", False)

    assert not (outside / "antigravity.png").exists()


def _build_asar(path: Path, icon: bytes) -> None:
    header = json.dumps(
        {"files": {"icon.png": {"offset": "0", "size": len(icon)}}}
    ).encode()
    json_size = len(header)
    pickle_size = json_size + 4
    header_size = pickle_size + 4
    blob = (
        struct.pack("<I", 4)
        + struct.pack("<I", header_size)
        + struct.pack("<I", pickle_size)
        + struct.pack("<I", json_size)
        + header
    )
    path.write_bytes(blob + icon)


def test_hub_icon_symlink_is_not_written(tmp_path: Path) -> None:
    """A resources/icon.png symlink never receives the extracted icon."""
    root = tmp_path / "Antigravity-x64"
    staging = _stage_tree(tmp_path)
    resources = staging / "tree/resources"
    resources.mkdir(parents=True)
    _build_asar(resources / "app.asar", b"PNGDATA")
    victim = tmp_path / "victim.txt"
    victim.write_bytes(b"keep")
    (resources / "icon.png").symlink_to(victim)

    with patch("replace.stop_main_pid"):
        replace.commit_product("hub", staging, root, "1.0.0", True)

    assert victim.read_bytes() == b"keep"


def test_hub_icon_extracted_for_regular_path(tmp_path: Path) -> None:
    """A normal archive still receives the extracted icon."""
    root = tmp_path / "Antigravity-x64"
    staging = _stage_tree(tmp_path)
    resources = staging / "tree/resources"
    resources.mkdir(parents=True)
    _build_asar(resources / "app.asar", b"PNGDATA")

    with patch("replace.stop_main_pid"):
        replace.commit_product("hub", staging, root, "1.0.0", True)

    assert (root / "resources/icon.png").read_bytes() == b"PNGDATA"
