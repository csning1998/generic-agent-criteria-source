#!/usr/bin/env python3
"""Execute Antigravity replacement operations from a JSON payload."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import struct
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path


OFFICIAL_HOSTS = frozenset(
    {"storage.googleapis.com", "dl.google.com", "edgedl.me.gvt1.com"}
)
REDIRECT_CODES = frozenset({"301", "302", "303", "307", "308"})
MAX_REDIRECTS = 5
CURL_TIMEOUT_SECONDS = 900
VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
# Allowed install base directories and the minimum path depth below each.
INSTALL_BASES = {"home": 2, "/opt": 1}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments for the replace module."""
    parser = argparse.ArgumentParser(
        description="Execute Antigravity binary replacement."
    )
    parser.add_argument(
        "--payload",
        help="JSON payload string or path to JSON file.",
        default=None,
    )
    return parser.parse_args()


def load_payload(payload_input: str | None) -> dict:
    """Load JSON payload from argument string, file path, or stdin."""
    if not payload_input:
        return json.load(sys.stdin)
    stripped = payload_input.strip()
    if not stripped.startswith("{"):
        path = Path(payload_input)
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(payload_input)


def validate_url_host(url: str) -> None:
    """Ensure downloaded URL host is within official allowed hosts."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Scheme must be https, got {parsed.scheme}")
    hostname = (parsed.hostname or "").lower()
    if hostname not in OFFICIAL_HOSTS:
        raise ValueError(
            f"Host {parsed.hostname} is not in official hosts: "
            f"{sorted(OFFICIAL_HOSTS)}"
        )


def validate_version(version: str) -> str:
    """Reject version strings that could escape the backup directory."""
    if not isinstance(version, str) or not VERSION_PATTERN.match(version):
        raise ValueError(f"Invalid version string: {version!r}")
    if ".." in version:
        raise ValueError(f"Invalid version string: {version!r}")
    return version


def validate_install_root(raw_root_path: str | None) -> Path:
    """Resolve an install root and require it under an allowed base."""
    if not raw_root_path or not isinstance(raw_root_path, str):
        raise ValueError("Install root is required")
    root = Path(os.path.expanduser(raw_root_path)).resolve()
    bases = {
        Path.home().resolve(): INSTALL_BASES["home"],
        Path("/opt"): INSTALL_BASES["/opt"],
    }
    for base, min_depth in bases.items():
        if root.is_relative_to(base):
            if len(root.relative_to(base).parts) >= min_depth:
                return root
    raise ValueError(f"Install root {root} is outside allowed locations")


def verify_sha256(path: Path, expected: str) -> None:
    """Raise ValueError when the file digest differs from expected."""
    if not SHA256_PATTERN.match(expected):
        raise ValueError("Expected sha256 must be 64 hex characters")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected.lower():
        raise ValueError(f"sha256 mismatch for {path.name}")


def download_archive(url: str, dest: Path) -> None:
    """Download url, validating every redirect hop against the allow-list."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        validate_url_host(current)
        out = subprocess.check_output(
            [
                "curl",
                "-sS",
                "--proto",
                "=https",
                "--max-redirs",
                "0",
                "--max-time",
                str(CURL_TIMEOUT_SECONDS),
                "-o",
                str(dest),
                "-w",
                "%{http_code} %{redirect_url}",
                current,
            ],
            text=True,
        )
        code, _, location = out.strip().partition(" ")
        if code.startswith("2"):
            return
        if code in REDIRECT_CODES and location:
            current = location
            continue
        raise RuntimeError(f"Download failed with HTTP {code}: {current}")
    raise RuntimeError(f"Too many redirects while fetching {url}")


def stop_main_pid(process_pattern: str) -> None:
    """Stop main PID identified from `ps -eo pid,ppid,args`."""
    out = subprocess.check_output(["ps", "-eo", "pid,ppid,args"], text=True)
    candidates = []
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        pid_str, ppid_str, cmd = parts
        if cmd.split(None, 1)[0] == process_pattern:
            try:
                candidates.append((int(pid_str), int(ppid_str), cmd))
            except ValueError:
                continue

    if not candidates:
        return

    candidate_pids = {p[0] for p in candidates}
    roots = [p for p in candidates if p[1] not in candidate_pids]

    for root_pid, _, _ in roots:
        try:
            os.kill(root_pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.time() + 5
    while time.time() < deadline:
        has_running_processes = False
        for root_pid, _, _ in roots:
            try:
                os.kill(root_pid, 0)
                has_running_processes = True
            except ProcessLookupError:
                pass
        if not has_running_processes:
            break
        time.sleep(0.5)

    for root_pid, _, _ in roots:
        try:
            os.kill(root_pid, 0)
        except ProcessLookupError:
            continue
        try:
            os.kill(root_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def extract_asar_icon(asar_path: Path, dest: Path) -> bool:
    """Write icon.png from an asar archive to dest."""
    try:
        with asar_path.open("rb") as handle:
            header_bytes = handle.read(4)
            if len(header_bytes) < 4:
                return False
            raw_size = handle.read(4)
            if len(raw_size) < 4:
                return False
            header_size = struct.unpack("<I", raw_size)[0]
            handle.read(4)
            json_bytes = handle.read(4)
            if len(json_bytes) < 4:
                return False
            json_size = struct.unpack("<I", json_bytes)[0]
            header = json.loads(handle.read(json_size).decode("utf-8"))
            icon = header.get("files", {}).get("icon.png")
            if not icon:
                return False
            handle.seek(8 + header_size + int(icon["offset"]))
            dest.write_bytes(handle.read(int(icon["size"])))
        return True
    except Exception:
        return False


def is_contained_regular(path: Path, root: Path) -> bool:
    """Return True when path is not a symlink and resolves inside root."""
    if path.is_symlink():
        return False
    return path.resolve().is_relative_to(root.resolve())


def stage_product(
    url: str, install_root: Path, sha256: str | None = None
) -> Path:
    """Download and extract one product into a sibling staging directory."""
    validate_url_host(url)
    staging_dir = install_root.parent / f".{install_root.name}.staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    tar_path = staging_dir / "product.tar.gz"
    extract_dir = staging_dir / "tree"
    extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        download_archive(url, tar_path)
        if sha256:
            verify_sha256(tar_path, sha256)
        subprocess.check_call(
            [
                "tar",
                "-xzf",
                str(tar_path),
                "-C",
                str(extract_dir),
                "--strip-components=1",
            ]
        )
    except BaseException:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise
    return staging_dir


def commit_product(
    product: str,
    staging_dir: Path,
    install_root: Path,
    old_version: str,
    extract_hub_icon: bool,
) -> str | None:
    """Stop processes, back up the live root, and deploy the staged tree."""
    validate_version(old_version)
    extract_dir = staging_dir / "tree"

    if product == "ide":
        stop_main_pid(str(install_root / "antigravity-ide"))
    else:
        stop_main_pid(str(install_root / "antigravity"))

    backup_path = None
    backup_dir = None
    if install_root.exists():
        backup_name = f"{install_root.name}.bak.{old_version}"
        backup_dir = install_root.parent / backup_name
        if backup_dir.parent != install_root.parent:
            raise ValueError(f"Backup path escapes parent: {backup_dir}")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        install_root.rename(backup_dir)
        backup_path = str(backup_dir)

    try:
        shutil.move(str(extract_dir), str(install_root))
    except Exception:
        shutil.rmtree(install_root, ignore_errors=True)
        if backup_dir is not None:
            backup_dir.rename(install_root)
        raise
    shutil.rmtree(staging_dir, ignore_errors=True)

    if product == "ide":
        code_icon = install_root / "resources/app/resources/linux/code.png"
        antigravity_icon = (
            install_root / "resources/app/resources/linux/antigravity.png"
        )
        if (
            code_icon.is_file()
            and is_contained_regular(code_icon, install_root)
            and not antigravity_icon.is_symlink()
            and not antigravity_icon.exists()
            and is_contained_regular(antigravity_icon, install_root)
        ):
            shutil.copy2(code_icon, antigravity_icon)

        sandbox = install_root / "chrome-sandbox"
        if sandbox.is_file() and is_contained_regular(sandbox, install_root):
            try:
                os.chmod(sandbox, 0o4755)
            except PermissionError:
                os.chmod(sandbox, 0o755)
    elif product == "hub":
        if extract_hub_icon:
            asar = install_root / "resources/app.asar"
            icon = install_root / "resources/icon.png"
            if asar.is_file() and is_contained_regular(icon, install_root):
                icon.parent.mkdir(parents=True, exist_ok=True)
                extract_asar_icon(asar, icon)

        sandbox = install_root / "chrome-sandbox"
        if sandbox.is_file() and is_contained_regular(sandbox, install_root):
            os.chmod(sandbox, 0o755)

    return backup_path


def replace_product(
    product: str,
    url: str,
    install_root: Path,
    old_version: str,
    extract_hub_icon: bool,
    sha256: str | None = None,
) -> str | None:
    """Stage and commit one product tree."""
    staging_dir = stage_product(url, install_root, sha256)
    return commit_product(
        product, staging_dir, install_root, old_version, extract_hub_icon
    )


def build_jobs(payload: dict) -> list[dict]:
    """Validate every requested product before any filesystem change."""
    products = payload.get("products", [])
    jobs = []
    for product in ("ide", "hub"):
        url = payload.get(f"{product}_url")
        if product not in products or not url:
            continue
        validate_url_host(url)
        sha256 = payload.get(f"{product}_sha256")
        if sha256 and not SHA256_PATTERN.match(sha256):
            raise ValueError(f"Invalid {product}_sha256")
        jobs.append(
            {
                "product": product,
                "url": url,
                "root": validate_install_root(payload.get(f"{product}_root")),
                "old_version": validate_version(
                    payload.get(f"old_{product}_version", "unknown")
                ),
                "sha256": sha256,
                "extract_hub_icon": product == "hub"
                and bool(payload.get("extract_hub_icon")),
            }
        )
    return jobs


def main() -> int:
    """Execute replace operations and print AntigravityResult JSON."""
    args = parse_args()
    try:
        payload = load_payload(args.payload)
    except Exception as err:
        json.dump(
            {
                "ok": False,
                "error": f"Failed to load payload: {err}",
                "op": "replace",
                "probe": {},
                "backups": [],
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return 1

    backups = []
    staged_jobs = []

    try:
        jobs = build_jobs(payload)
        for job in jobs:
            staged_jobs.append(
                (job, stage_product(job["url"], job["root"], job["sha256"]))
            )
        for job, staging_dir in staged_jobs:
            backup_path = commit_product(
                job["product"],
                staging_dir,
                job["root"],
                job["old_version"],
                job["extract_hub_icon"],
            )
            if backup_path:
                backups.append(backup_path)

        result = {
            "ok": True,
            "error": None,
            "op": "replace",
            "probe": payload.get("probe", {}),
            "backups": backups,
        }
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    except Exception as err:
        for _, staging_dir in staged_jobs:
            shutil.rmtree(staging_dir, ignore_errors=True)
        result = {
            "ok": False,
            "error": str(err),
            "op": "replace",
            "probe": payload.get("probe", {}),
            "backups": backups,
        }
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
