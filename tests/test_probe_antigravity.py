"""Unit tests for the Antigravity probe script."""

from __future__ import annotations

import gzip
import io
import json
import struct
from pathlib import Path
from unittest.mock import patch

import probe
import pytest


HUB_URL = "https://edgedl.me.gvt1.com/antigravity-hub/1.2.3-456/linux-x64/Antigravity.tar.gz"
IDE_URL = (
    "https://edgedl.me.gvt1.com/stable/4.5.6/linux-x64/Antigravity-IDE.tar.gz"
)


def write_asar(path: Path, files: dict[str, bytes]) -> Path:
    """Write a minimal asar archive holding files at the top level."""
    entries, body, offset = {}, b"", 0
    for name, data in files.items():
        entries[name] = {"offset": str(offset), "size": len(data)}
        body += data
        offset += len(data)
    header = json.dumps({"files": entries}).encode()
    header_size = len(header) + 8
    path.write_bytes(
        struct.pack("<I", 4)
        + struct.pack("<I", header_size)
        + struct.pack("<I", len(header) + 4)
        + struct.pack("<I", len(header))
        + header
        + body
    )
    return path


class FakeResponse(io.BytesIO):
    """Response stub carrying a Content-Encoding header."""

    def __init__(self, payload: bytes, encoding: str = "") -> None:
        """Hold payload and the optional Content-Encoding value."""
        super().__init__(payload)
        self.headers = {"Content-Encoding": encoding} if encoding else {}

    def __enter__(self) -> FakeResponse:
        """Return the stub as the context value."""
        return self

    def __exit__(self, *args: object) -> None:
        """Close the stub."""
        self.close()


def test_fetch_decodes_a_gzip_payload() -> None:
    """A gzip response body is decompressed."""
    with patch.object(
        probe.urllib.request,
        "urlopen",
        return_value=FakeResponse(gzip.compress(b"page"), "gzip"),
    ):
        assert probe.fetch("https://antigravity.google/download") == b"page"


def test_fetch_returns_a_plain_payload() -> None:
    """A plain response body is returned unchanged."""
    with patch.object(
        probe.urllib.request, "urlopen", return_value=FakeResponse(b"page")
    ):
        assert probe.fetch("https://antigravity.google/download") == b"page"


@pytest.mark.parametrize(
    ("url", "version"),
    [
        (HUB_URL, "1.2.3"),
        (IDE_URL, "4.5.6"),
        ("https://example.invalid/7.8.9-rc1/x.tar.gz", "7.8.9"),
        ("https://example.invalid/latest/x.tar.gz", "unknown"),
    ],
)
def test_parse_version_from_url(url: str, version: str) -> None:
    """Each known URL layout yields its version, and others yield unknown."""
    assert probe.parse_version_from_url(url) == version


def test_resolve_official_picks_the_linux_tarballs() -> None:
    """The Linux x64 hub and IDE tarballs are picked from the page."""
    page = f'<a href="{HUB_URL}">hub</a> <a href="{IDE_URL}">ide</a> <a href="https://x.invalid/mac/Antigravity.tar.gz">mac</a>'
    with patch.object(probe, "fetch", return_value=page.encode()):
        official = probe.resolve_official()
    assert official == {
        "hub": {"version": "1.2.3", "url": HUB_URL},
        "ide": {"version": "4.5.6", "url": IDE_URL},
    }


def test_resolve_official_stops_without_both_tarballs() -> None:
    """A page without the IDE tarball stops the probe."""
    with patch.object(
        probe, "fetch", return_value=f'<a href="{HUB_URL}">hub</a>'.encode()
    ):
        with pytest.raises(SystemExit):
            probe.resolve_official()


def test_asar_reads_the_package_version_and_the_icon(tmp_path: Path) -> None:
    """The package version and the icon are read from an asar archive."""
    asar = write_asar(
        tmp_path / "app.asar",
        {"package.json": b'{"version": "2.0.1"}', "icon.png": b"PNG"},
    )
    assert probe.read_asar_package_version(asar) == "2.0.1"
    dest = tmp_path / "icon.png"
    assert probe.extract_asar_icon(asar, dest) is True
    assert dest.read_bytes() == b"PNG"


def test_asar_without_the_entries(tmp_path: Path) -> None:
    """An asar archive without the entries yields no version and no icon."""
    asar = write_asar(tmp_path / "app.asar", {"other.txt": b"x"})
    assert probe.read_asar_package_version(asar) is None
    assert probe.extract_asar_icon(asar, tmp_path / "icon.png") is False


def test_read_ide_version(tmp_path: Path) -> None:
    """The IDE version comes from product.json, or None without the file."""
    assert probe.read_ide_version(tmp_path) is None
    product = tmp_path / "resources/app/product.json"
    product.parent.mkdir(parents=True)
    product.write_text('{"ideVersion": "4.5.6"}')
    assert probe.read_ide_version(tmp_path) == "4.5.6"


def test_read_hub_version_prefers_the_asar(tmp_path: Path) -> None:
    """The hub version prefers app.asar over package.json."""
    assert probe.read_hub_version(tmp_path) is None
    pkg = tmp_path / "resources/app/package.json"
    pkg.parent.mkdir(parents=True)
    pkg.write_text('{"version": "1.0.0"}')
    assert probe.read_hub_version(tmp_path) == "1.0.0"
    write_asar(
        tmp_path / "resources/app.asar",
        {"package.json": b'{"version": "1.2.3"}'},
    )
    assert probe.read_hub_version(tmp_path) == "1.2.3"


def test_find_existing_roots_skips_missing_markers_and_duplicates(
    tmp_path: Path,
) -> None:
    """Roots without the marker and symlinked duplicates are skipped."""
    real = tmp_path / "real"
    real.mkdir()
    (real / "antigravity").write_text("")
    link = tmp_path / "link"
    link.symlink_to(real)
    empty = tmp_path / "empty"
    empty.mkdir()
    roots = probe.find_existing_roots(
        [tmp_path / "absent", empty, real, link], "antigravity"
    )
    assert roots == [real]


def test_main_extract_hub_icon(tmp_path: Path) -> None:
    """The extract-hub-icon mode writes the icon and rejects wrong usage."""
    asar = write_asar(tmp_path / "app.asar", {"icon.png": b"PNG"})
    dest = tmp_path / "icon.png"
    with patch.object(
        probe.sys,
        "argv",
        ["probe.py", "extract-hub-icon", str(asar), str(dest)],
    ):
        assert probe.main() == 0
    assert dest.read_bytes() == b"PNG"
    with patch.object(
        probe.sys, "argv", ["probe.py", "extract-hub-icon", str(asar)]
    ):
        assert probe.main() == 2


def test_main_prints_the_probe_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The default mode prints the official URLs and the installs."""
    ide_root = tmp_path / "ide"
    (ide_root / "resources/app").mkdir(parents=True)
    (ide_root / "antigravity-ide").write_text("")
    (ide_root / "resources/app/product.json").write_text(
        '{"ideVersion": "4.5.6"}'
    )
    official = {
        "hub": {"version": "1.2.3", "url": HUB_URL},
        "ide": {"version": "4.5.6", "url": IDE_URL},
    }
    with (
        patch.object(probe.sys, "argv", ["probe.py"]),
        patch.object(probe, "resolve_official", return_value=official),
        patch.object(probe, "IDE_CANDIDATES", [ide_root]),
        patch.object(probe, "HUB_CANDIDATES", []),
    ):
        assert probe.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["official"] == official
    assert payload["installed"] == {
        "ide": [{"path": str(ide_root), "version": "4.5.6"}],
        "hub": [],
    }
