"""Materialize distill, skills, and thin shells without a shell copy."""

from __future__ import annotations

import argparse
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


MODE_SYMLINK = "symlink"
MODE_COPY = "copy"
_ALLOWED_PREFIXES = (".agents/", ".claude/", ".gemini/", ".grok/")
_PROTECTED_REL = (".claude", ".agents", ".gemini", ".grok")


@dataclass(frozen=True)
class AdapterSpec:
    """One allow-listed adapter mapping."""

    source: str
    dest: str
    mode: str


SPECS: tuple[AdapterSpec, ...] = (
    AdapterSpec(
        source="rules/AGENT_CRITERIA.md",
        dest=".agents/AGENTS.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="rules/AGENT_CRITERIA.md",
        dest=".gemini/GEMINI.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/adapters/claude/CLAUDE.md",
        dest=".claude/CLAUDE.md",
        mode=MODE_COPY,
    ),
    AdapterSpec(
        source="hooks/adapters/claude/gate-check.py",
        dest=".claude/hooks/gate-check.py",
        mode=MODE_COPY,
    ),
    AdapterSpec(
        source="hooks/adapters/claude/post-write-review.py",
        dest=".claude/hooks/post-write-review.py",
        mode=MODE_COPY,
    ),
    AdapterSpec(
        source="hooks/adapters/skills",
        dest=".agents/skills",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria",
        dest=".agents/criteria",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="rules/ENGINEERING_PRINCIPLES.md",
        dest=".agents/ENGINEERING_PRINCIPLES.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/references/lang-md.md",
        dest=".claude/lang_md.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/references/lang-hcl.md",
        dest=".claude/lang_hcl.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/references/lang-ts.md",
        dest=".claude/lang_ts.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/references/lang-ipynb.md",
        dest=".claude/lang_ipynb.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/references/lang-yaml.md",
        dest=".claude/lang_yaml.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/references/lang-go.md",
        dest=".claude/lang_go.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/references/lang-md.md",
        dest=".gemini/lang_md.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/references/lang-hcl.md",
        dest=".gemini/lang_hcl.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/references/lang-ts.md",
        dest=".gemini/lang_ts.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/references/lang-ipynb.md",
        dest=".gemini/lang_ipynb.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/references/lang-yaml.md",
        dest=".gemini/lang_yaml.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/references/lang-go.md",
        dest=".gemini/lang_go.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="rules",
        dest=".grok/rules",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="skills",
        dest=".grok/skills",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks",
        dest=".grok/hooks",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="roles",
        dest=".grok/roles",
        mode=MODE_SYMLINK,
    ),
)


def infer_grok_root() -> Path:
    """Return the repository root that contains this package."""
    return Path(__file__).resolve().parents[2]


def _spec_dests() -> frozenset[str]:
    return frozenset(spec.dest for spec in SPECS)


def validate_dest_rel(dest_rel: str) -> None:
    """Reject a dest path that is outside the SPECS allow-list."""
    if dest_rel in _PROTECTED_REL:
        raise ValueError(f"protected dest {dest_rel}")
    if dest_rel != Path(dest_rel).as_posix():
        raise ValueError(f"non-posix dest {dest_rel}")
    if dest_rel.startswith("/") or dest_rel.startswith("~"):
        raise ValueError(f"absolute dest {dest_rel}")
    parts = Path(dest_rel).parts
    if ".." in parts or parts[0] == "/":
        raise ValueError(f"dest escapes home {dest_rel}")
    if not dest_rel.startswith(_ALLOWED_PREFIXES):
        raise ValueError(f"dest prefix not allowed {dest_rel}")
    if dest_rel not in _spec_dests():
        raise ValueError(f"dest not in allow-list {dest_rel}")


def _validate_specs() -> None:
    for spec in SPECS:
        if spec.mode not in (MODE_SYMLINK, MODE_COPY):
            raise ValueError(f"unknown mode {spec.mode}")
        validate_dest_rel(spec.dest)
        if spec.mode == MODE_COPY and spec.dest.endswith("/"):
            raise ValueError(f"copy dest is a directory {spec.dest}")


_validate_specs()


def resolve_source(grok_root: Path, spec: AdapterSpec) -> Path:
    """Return the source path under grok_root."""
    source = grok_root.joinpath(*Path(spec.source).parts)
    return source


def resolve_dest(home: Path, spec: AdapterSpec) -> Path:
    """Return the dest path under home."""
    return home.joinpath(*Path(spec.dest).parts)


def _lexically_under_home(home: Path, dest: Path) -> bool:
    try:
        dest.relative_to(home)
    except ValueError:
        return False
    return True


def _symlink_in_ancestors(home: Path, dest: Path) -> bool:
    cursor = dest.parent
    home_r = home.resolve()
    while cursor != home and cursor != home_r:
        if cursor.exists() and cursor.is_symlink():
            return True
        parent = cursor.parent
        if parent == cursor:
            break
        cursor = parent
    return False


def _dest_parent_under_home(home: Path, dest: Path) -> bool:
    if not _lexically_under_home(home, dest):
        return False
    if _symlink_in_ancestors(home, dest):
        return False
    return True


def _mkdir_parents(home: Path, dest: Path) -> bool:
    cursor = home
    try:
        rel_parts = dest.parent.relative_to(home).parts
    except ValueError:
        return False
    for part in rel_parts:
        cursor = cursor / part
        if cursor.exists():
            if cursor.is_symlink() or not cursor.is_dir():
                return False
            continue
        cursor.mkdir(mode=0o755)
        if cursor.is_symlink() or not cursor.is_dir():
            return False
    return True


def _file_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _walk_local(root: Path) -> tuple[Path, ...]:
    """List entries under root. Directory symlinks are not descended."""
    if root.is_symlink() or not root.is_dir():
        return (root,)
    found: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            found.append(child)
            if child.is_dir() and not child.is_symlink():
                stack.append(child)
    return tuple(found)


def _iter_files(root: Path) -> tuple[Path, ...]:
    if root.is_file() and not root.is_dir():
        return (root,)
    files = [
        item
        for item in _walk_local(root)
        if item.is_file() and not item.is_symlink()
    ]
    return tuple(sorted(files))


def trees_match(left: Path, right: Path) -> bool:
    """Return True when both paths exist and hold the same file bytes."""
    if left.is_file() and right.is_file():
        return _file_bytes(left) == _file_bytes(right)
    if not left.is_dir() or not right.is_dir():
        return False
    left_map = {
        item.relative_to(left).as_posix(): _file_bytes(item)
        for item in _iter_files(left)
    }
    right_map = {
        item.relative_to(right).as_posix(): _file_bytes(item)
        for item in _iter_files(right)
    }
    return left_map == right_map


def _remove_replaceable_tree(dest: Path) -> None:
    children = _walk_local(dest)
    ordered = sorted(children, key=lambda item: len(item.parts), reverse=True)
    for child in ordered:
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    dest.rmdir()


def current_state(dest: Path, source: Path, mode: str) -> str:
    """Return ok, missing, or a drift token for one dest."""
    if not dest.exists() and not dest.is_symlink():
        return "missing"
    if dest.is_symlink():
        if mode != MODE_SYMLINK:
            return "symlink-for-copy"
        try:
            if dest.resolve() == source.resolve():
                return "ok"
        except OSError:
            return "broken-symlink"
        return "wrong-symlink"
    if mode == MODE_SYMLINK:
        if dest.is_file() or dest.is_dir():
            if trees_match(dest, source):
                return "regular-same"
            return "regular-differs"
        return "unexpected-type"
    if dest.is_file() and source.is_file():
        if trees_match(dest, source):
            return "ok"
        return "copy-differs"
    return "unexpected-type"


def check_spec(grok_root: Path, home: Path, spec: AdapterSpec) -> str:
    """Return ok or a drift token. missing source is source-missing."""
    source = resolve_source(grok_root, spec)
    dest = resolve_dest(home, spec)
    if not source.exists():
        return "source-missing"
    if not _dest_parent_under_home(home, dest):
        return "dest-escapes"
    state = current_state(dest, source, spec.mode)
    if state == "ok":
        return "ok"
    return state


def _can_apply(state: str) -> bool:
    return state in (
        "ok",
        "missing",
        "wrong-symlink",
        "broken-symlink",
        "symlink-for-copy",
        "regular-same",
        "copy-differs",
    )


def apply_spec(grok_root: Path, home: Path, spec: AdapterSpec) -> str:
    """Materializes a single specification destination.

    Returns the execution status token.
    """
    source = resolve_source(grok_root, spec)
    dest = resolve_dest(home, spec)
    if not source.exists():
        return "source-missing"
    if not _dest_parent_under_home(home, dest):
        return "dest-escapes"
    state = current_state(dest, source, spec.mode)
    if state == "ok":
        return "skipped"
    if state == "regular-differs":
        return "regular-differs"
    if not _can_apply(state):
        return state
    if not _mkdir_parents(home, dest):
        return "dest-escapes"
    if not _dest_parent_under_home(home, dest):
        return "dest-escapes"
    state = current_state(dest, source, spec.mode)
    if state == "ok":
        return "skipped"
    if state == "regular-differs":
        return "regular-differs"
    if not _can_apply(state):
        return state
    if spec.mode == MODE_SYMLINK:
        if dest.is_dir() and not dest.is_symlink():
            _remove_replaceable_tree(dest)
        elif dest.exists() or dest.is_symlink():
            dest.unlink()
        dest.symlink_to(
            source.resolve(),
            target_is_directory=source.is_dir(),
        )
        return "applied"

    # os.replace() swaps a regular file or symlink atomically, avoiding the
    # missing-destination window an unlink-then-write sequence would expose
    # to a concurrent reader or filesystem watcher.
    if dest.is_dir() and not dest.is_symlink():
        _remove_replaceable_tree(dest)
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(source.read_bytes())
        if source.stat().st_mode & 0o111:
            tmp.chmod(tmp.stat().st_mode | 0o111)
        os.replace(tmp, dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return "applied"


def run_check(grok_root: Path, home: Path) -> int:
    """Print dest status. Return 1 when any dest is not ok."""
    failed = False
    for spec in SPECS:
        status = check_spec(grok_root, home, spec)
        if status == "ok":
            print(f"OK    {spec.dest}")
            continue
        failed = True
        print(f"DRIFT {spec.dest}: {status}")
    return 1 if failed else 0


def run_apply(grok_root: Path, home: Path) -> int:
    """Refuse mismatched dests, then materialize. Return 1 on abort."""
    blocked: list[tuple[str, str]] = []
    for spec in SPECS:
        status = check_spec(grok_root, home, spec)
        if status == "ok":
            continue
        if status == "regular-differs":
            blocked.append((spec.dest, status))
            continue
        if status == "source-missing" or status == "dest-escapes":
            blocked.append((spec.dest, status))
            continue
        if status == "unexpected-type":
            blocked.append((spec.dest, status))
    if blocked:
        for dest, status in blocked:
            print(f"ABORT {dest}: {status}")
        return 1
    failed = False
    for spec in SPECS:
        result = apply_spec(grok_root, home, spec)
        if result == "skipped":
            print(f"SKIP  {spec.dest}")
            continue
        if result == "applied":
            print(f"APPLY {spec.dest}")
            continue
        failed = True
        print(f"ABORT {spec.dest}: {result}")
        return 1
    return 1 if failed else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse check or apply. Default command is check."""
    parser = argparse.ArgumentParser(
        description=(
            "Materialize harness adapter files from the Grok SSoT tree."
        )
    )
    parser.add_argument(
        "command",
        choices=("check", "apply"),
        nargs="?",
        default="check",
    )
    parser.add_argument("--home", type=Path, default=None)
    parser.add_argument("--grok-root", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry. check is the default verb."""
    args = parse_args(argv)
    grok_root = (
        args.grok_root.resolve() if args.grok_root else infer_grok_root()
    )
    home = args.home.resolve() if args.home else Path.home()
    if args.command == "apply":
        return run_apply(grok_root, home)
    return run_check(grok_root, home)


if __name__ == "__main__":
    raise SystemExit(main())
