"""Path classification for governed IaC and planning trees."""

from __future__ import annotations

import os
from pathlib import Path

from engineering_principles.config import ARCHITECTURE_STEM_RE
from engineering_principles.config import BOOTSTRAPPER_NAME_RE
from engineering_principles.config import GENERIC_MODULE_RE
from engineering_principles.config import GOVERNED_DIR_PARTS
from engineering_principles.config import SECRET_MINT_LAYER_RE


def normalize_posix(path: str) -> str:
    """Normalize separators to POSIX slashes."""
    return path.replace("\\", "/")


def is_self_path(path: str) -> bool:
    """Return True when the path sits under the owner Grok home."""
    expanded = str(Path(path).expanduser())
    home_grok = str(Path.home() / ".grok")
    return expanded.startswith(home_grok + os.sep) or expanded == home_grok


def is_governed_path(path: str) -> bool:
    """Return True when a path component is a governed tree name."""
    parts = Path(normalize_posix(path)).parts
    return any(part in GOVERNED_DIR_PARTS for part in parts)


def is_iac_path(path: str) -> bool:
    """Return True when a path component is terraform, ansible, or packer."""
    parts = Path(normalize_posix(path)).parts
    return any(part in ("terraform", "ansible", "packer") for part in parts)


def is_ansible_path(path: str) -> bool:
    """Return True when a path component is ansible."""
    return "ansible" in Path(normalize_posix(path)).parts


def is_generic_module(path: str) -> bool:
    """Return True for shared Terraform modules or utils_* roles."""
    return bool(GENERIC_MODULE_RE.search(normalize_posix(path)))


def is_secret_mint_layer(path: str) -> bool:
    """Return True for vault, credential, pki, identity, or approle layers."""
    posix_path = normalize_posix(path)
    if "/terraform/layers/" not in posix_path:
        return False
    return bool(SECRET_MINT_LAYER_RE.search(posix_path))


def is_consumer_layer(path: str) -> bool:
    """Return True for a Terraform layer that must not mint secrets."""
    posix_path = normalize_posix(path)
    if "/terraform/layers/" not in posix_path:
        return False
    return not is_secret_mint_layer(posix_path)


def is_introduced_bootstrapper_name(path: str) -> bool:
    """Return True when a new path still uses the bootstrapper token."""
    candidate = Path(path).expanduser()
    if not BOOTSTRAPPER_NAME_RE.search(normalize_posix(str(candidate))):
        return False
    current = candidate
    while not current.exists() and current != current.parent:
        if BOOTSTRAPPER_NAME_RE.search(current.name):
            parent = current.parent
            for ancestor in [parent, *parent.parents]:
                if ancestor.exists() and BOOTSTRAPPER_NAME_RE.search(
                    ancestor.name
                ):
                    return False
            return True
        current = current.parent
    return False


def find_planning_root(start: Path) -> Path | None:
    """Walk parents until a planning tree with decisions or architecture."""
    cursor = start.resolve() if start.exists() else start
    seen: set[Path] = set()
    while cursor not in seen:
        seen.add(cursor)
        candidate = cursor / "planning"
        if (candidate / "decisions.md").is_file() or (
            candidate / "architecture.md"
        ).is_file():
            return candidate
        if cursor.parent == cursor:
            break
        cursor = cursor.parent
    return None


def load_architecture_repo_tokens(planning: Path) -> list[str]:
    """Return repo tokens encoded in architecture_*.md file names."""
    tokens: list[str] = []
    for item in planning.glob("architecture*.md"):
        match = ARCHITECTURE_STEM_RE.match(item.stem)
        if match is None:
            continue
        repo = match.group(1).split("_", 1)[0].strip()
        if repo and repo not in tokens:
            tokens.append(repo)
    return tokens


def is_planning_gate_required(path: str, planning: Path | None) -> bool:
    """Return True when a mutation needs planning reads first."""
    if planning is None or not path:
        return False
    posix_path = normalize_posix(path)
    try:
        resolved = Path(path).expanduser().resolve()
    except OSError:
        resolved = Path(posix_path)
    try:
        if resolved == planning.resolve() or (
            planning.resolve() in resolved.parents
        ):
            return True
    except OSError:
        if "/planning/" in posix_path:
            return True
    if not is_governed_path(posix_path):
        return False
    tokens = load_architecture_repo_tokens(planning)
    if not tokens:
        return True
    return any(token in posix_path for token in tokens)
