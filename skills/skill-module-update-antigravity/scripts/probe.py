#!/usr/bin/env python3
"""Print official Antigravity tarball URLs and local versions as JSON."""

from __future__ import annotations

import gzip
import json
import os
import re
import struct
import sys
import urllib.request
from pathlib import Path


DOWNLOAD_PAGE = "https://antigravity.google/download"
HOME = Path.home()

HUB_CANDIDATES = [
    HOME / ".local/share/antigravity/Antigravity-x64",
    Path("/opt/antigravity/Antigravity-x64"),
    Path("/opt/antigravity"),
]
IDE_CANDIDATES = [
    HOME / ".local/share/antigravity-ide",
    Path("/opt/antigravity-ide/Antigravity-IDE"),
    Path("/usr/share/antigravity-ide"),
]


def fetch(url: str) -> bytes:
    """Download URL bytes, decoding gzip when the server sends it."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "skill-layer-update-antigravity",
            "Accept-Encoding": "gzip, deflate, identity",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = resp.read()
        encoding = (resp.headers.get("Content-Encoding") or "").lower()
    if encoding == "gzip" or payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)
    return payload


def parse_version_from_url(url: str) -> str:
    """Parse a version token from a known official tarball URL."""
    for pattern in (
        r"/antigravity-hub/([^/]+)/",
        r"/stable/([^/]+)/",
        r"/(\d+\.\d+\.\d+(?:-[^/]+)?)/",
    ):
        match = re.search(pattern, url)
        if match:
            return match.group(1).split("-", 1)[0]
    return "unknown"


def resolve_official() -> dict[str, dict[str, str]]:
    """Read official Linux x64 hub and IDE tarball URLs."""
    html = fetch(DOWNLOAD_PAGE).decode("utf-8", errors="replace")
    urls = re.findall(r"https://[^\s\"'<>]+", html)
    hub_url = ""
    ide_url = ""
    for url in urls:
        if "linux-x64" not in url:
            continue
        if url.endswith("Antigravity.tar.gz"):
            hub_url = url
        if "IDE.tar.gz" in url:
            ide_url = url
    if not hub_url or not ide_url:
        raise SystemExit(
            "official Linux x64 tarball URLs were not found on "
            "the download page"
        )
    return {
        "hub": {"version": parse_version_from_url(hub_url), "url": hub_url},
        "ide": {"version": parse_version_from_url(ide_url), "url": ide_url},
    }


def read_asar_package_version(asar_path: Path) -> str | None:
    """Read package.json version from an Electron asar archive."""
    with asar_path.open("rb") as handle:
        handle.read(4)
        header_size = struct.unpack("<I", handle.read(4))[0]
        handle.read(4)
        json_size = struct.unpack("<I", handle.read(4))[0]
        header = json.loads(handle.read(json_size).decode())
        info = header.get("files", {}).get("package.json")
        if not info:
            return None
        handle.seek(8 + header_size + int(info["offset"]))
        pkg = json.loads(handle.read(int(info["size"])).decode())
    return pkg.get("version")


def extract_asar_icon(asar_path: Path, dest: Path) -> bool:
    """Write icon.png from an asar archive to dest. Return False if absent."""
    with asar_path.open("rb") as handle:
        handle.read(4)
        header_size = struct.unpack("<I", handle.read(4))[0]
        handle.read(4)
        json_size = struct.unpack("<I", handle.read(4))[0]
        header = json.loads(handle.read(json_size).decode())
        icon = header.get("files", {}).get("icon.png")
        if not icon:
            return False
        handle.seek(8 + header_size + int(icon["offset"]))
        dest.write_bytes(handle.read(int(icon["size"])))
    return True


def read_ide_version(root: Path) -> str | None:
    """Return ideVersion from a local Antigravity IDE install root."""
    product = root / "resources/app/product.json"
    if not product.is_file():
        return None
    data = json.loads(product.read_text())
    return data.get("ideVersion")


def read_hub_version(root: Path) -> str | None:
    """Return the hub version from asar or package.json."""
    asar = root / "resources/app.asar"
    if asar.is_file():
        return read_asar_package_version(asar)
    pkg = root / "resources/app/package.json"
    if pkg.is_file():
        return json.loads(pkg.read_text()).get("version")
    return None


def find_existing_roots(candidates: list[Path], marker: str) -> list[Path]:
    """Return unique existing install roots that contain marker."""
    found: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        if not (candidate / marker).is_file():
            continue
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        found.append(candidate)
    return found


def main() -> int:
    """Print probe JSON, or extract a hub icon when asked."""
    if len(sys.argv) > 1 and sys.argv[1] == "extract-hub-icon":
        if len(sys.argv) != 4:
            print(
                "usage: probe.py extract-hub-icon <asar> <dest.png>",
                file=sys.stderr,
            )
            return 2
        ok = extract_asar_icon(Path(sys.argv[2]), Path(sys.argv[3]))
        return 0 if ok else 1

    official = resolve_official()
    ide_installs = []
    for root in find_existing_roots(IDE_CANDIDATES, "antigravity-ide"):
        ide_installs.append(
            {"path": str(root), "version": read_ide_version(root)}
        )
    hub_installs = []
    for root in find_existing_roots(HUB_CANDIDATES, "antigravity"):
        hub_installs.append(
            {"path": str(root), "version": read_hub_version(root)}
        )
    payload = {
        "download_page": DOWNLOAD_PAGE,
        "official": official,
        "installed": {"ide": ide_installs, "hub": hub_installs},
        "launchers": {
            "ide": str(Path("/usr/local/bin/antigravity-ide")),
            "hub_user": str(HOME / ".local/bin/antigravity"),
            "hub_system": str(Path("/usr/local/bin/antigravity")),
        },
        "data_dirs_do_not_touch": [
            str(HOME / ".antigravity-ide"),
            str(HOME / ".config/Antigravity IDE"),
            str(HOME / ".config/Antigravity"),
        ],
        "arch": os.uname().machine,
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
