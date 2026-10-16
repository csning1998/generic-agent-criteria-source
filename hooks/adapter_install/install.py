"""Materialize distill, skills, and thin shells without a shell copy."""

from __future__ import annotations

import argparse
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from context_docs.resolve import resolve_catalog_path
from context_docs.resolve import resolve_catalog_skill_sources

from adapter_install.cursor_mdc import load_cursor_scenarios
from adapter_install.cursor_mdc import render_cursor_mdc


MODE_SYMLINK = "symlink"
MODE_COPY = "copy"
MODE_CURSOR_MDC = "cursor-mdc"
_ALLOWED_PREFIXES = (
    ".agents/",
    ".claude/",
    ".gemini/",
    ".grok/",
    ".cursor/",
)
_PROTECTED_REL = (".claude", ".agents", ".gemini", ".grok", ".cursor")


@dataclass(frozen=True)
class AdapterSpec:
    """One allow-listed adapter mapping."""

    source: str
    dest: str
    mode: str
    scenario_id: str | None = None


_STATIC_SPECS: tuple[AdapterSpec, ...] = (
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
        source="hooks/adapters/claude/scenario_parser.py",
        dest=".claude/hooks/scenario_parser.py",
        mode=MODE_COPY,
    ),
    AdapterSpec(
        source="hooks/adapters/claude/gate-check.py",
        dest=".cursor/hooks/gate-check.py",
        mode=MODE_COPY,
    ),
    AdapterSpec(
        source="hooks/adapters/claude/post-write-review.py",
        dest=".cursor/hooks/post-write-review.py",
        mode=MODE_COPY,
    ),
    AdapterSpec(
        source="hooks/adapters/claude/scenario_parser.py",
        dest=".cursor/hooks/scenario_parser.py",
        mode=MODE_COPY,
    ),
    AdapterSpec(
        source="hooks/adapters/cursor/stop-output-scan.py",
        dest=".cursor/hooks/stop-output-scan.py",
        mode=MODE_COPY,
    ),
    AdapterSpec(
        source="hooks/adapters/cursor/skill-module-gate.py",
        dest=".cursor/hooks/skill-module-gate.py",
        mode=MODE_COPY,
    ),
    AdapterSpec(
        source="hooks/adapters/cursor/hooks.json",
        dest=".cursor/hooks.json",
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
        source="hooks/criteria/4_L2-trigger/markdown.md",
        dest=".claude/lang_md.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/4_L2-trigger/hcl.md",
        dest=".claude/lang_hcl.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/4_L2-trigger/typescript.md",
        dest=".claude/lang_ts.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/4_L2-trigger/ipynb.md",
        dest=".claude/lang_ipynb.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/4_L2-trigger/yaml.md",
        dest=".claude/lang_yaml.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/4_L2-trigger/golang.md",
        dest=".claude/lang_go.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/4_L2-trigger/markdown.md",
        dest=".gemini/lang_md.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/4_L2-trigger/hcl.md",
        dest=".gemini/lang_hcl.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/4_L2-trigger/typescript.md",
        dest=".gemini/lang_ts.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/4_L2-trigger/ipynb.md",
        dest=".gemini/lang_ipynb.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/4_L2-trigger/yaml.md",
        dest=".gemini/lang_yaml.md",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="hooks/criteria/4_L2-trigger/golang.md",
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
    AdapterSpec(
        source="config/contexts.toml",
        dest=".grok/contexts.toml",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="config/contexts.toml",
        dest=".claude/contexts.toml",
        mode=MODE_SYMLINK,
    ),
    AdapterSpec(
        source="config/contexts.toml",
        dest=".gemini/contexts.toml",
        mode=MODE_SYMLINK,
    ),
)


def resolve_grok_root() -> Path:
    """Return the repository root that contains this package."""
    return Path(__file__).resolve().parents[2]


def _derive_cursor_specs(grok_root: Path) -> tuple[AdapterSpec, ...]:
    """Load Cursor `.mdc` specs from the language dispatch table."""
    specs: list[AdapterSpec] = []
    for rel, parsed in load_cursor_scenarios(grok_root):
        specs.append(
            AdapterSpec(
                source=rel,
                dest=f".cursor/rules/lang-{parsed.scenario_id}.mdc",
                mode=MODE_CURSOR_MDC,
                scenario_id=parsed.scenario_id,
            )
        )
    return tuple(specs)


SPECS: tuple[AdapterSpec, ...] = _STATIC_SPECS + _derive_cursor_specs(
    resolve_grok_root()
)


def _extract_spec_dests() -> frozenset[str]:
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
    if dest_rel not in _extract_spec_dests():
        raise ValueError(f"dest not in allow-list {dest_rel}")


def _validate_specs() -> None:
    for spec in SPECS:
        if spec.mode not in (MODE_SYMLINK, MODE_COPY, MODE_CURSOR_MDC):
            raise ValueError(f"unknown mode {spec.mode}")
        validate_dest_rel(spec.dest)
        if spec.mode in (MODE_COPY, MODE_CURSOR_MDC) and spec.dest.endswith(
            "/"
        ):
            raise ValueError(f"copy dest is a directory {spec.dest}")
        if spec.mode == MODE_CURSOR_MDC:
            if not spec.scenario_id:
                raise ValueError("cursor spec is missing scenario_id")
            expected_dest = f".cursor/rules/lang-{spec.scenario_id}.mdc"
            if spec.dest != expected_dest:
                raise ValueError(f"cursor dest mismatch {spec.dest}")


_validate_specs()


def resolve_source(grok_root: Path, spec: AdapterSpec) -> Path:
    """Return the source path under grok_root."""
    source = grok_root.joinpath(*Path(spec.source).parts)
    return source


def resolve_dest(home: Path, spec: AdapterSpec) -> Path:
    """Return the dest path under home."""
    return home.joinpath(*Path(spec.dest).parts)


def _is_lexically_under_home(home: Path, dest: Path) -> bool:
    try:
        dest.relative_to(home)
    except ValueError:
        return False
    return True


def _has_symlink_in_ancestors(home: Path, dest: Path) -> bool:
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


def _is_dest_parent_under_home(home: Path, dest: Path) -> bool:
    if not _is_lexically_under_home(home, dest):
        return False
    if _has_symlink_in_ancestors(home, dest):
        return False
    return True


def _provision_dest_parents(home: Path, dest: Path) -> bool:
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


def _load_file_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _find_local_entries(root: Path) -> tuple[Path, ...]:
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


def _find_files(root: Path) -> tuple[Path, ...]:
    if root.is_file() and not root.is_dir():
        return (root,)
    files = [
        item
        for item in _find_local_entries(root)
        if item.is_file() and not item.is_symlink()
    ]
    return tuple(sorted(files))


def render_expected_payload(
    source: Path, mode: str, *, scenario_id: str | None = None
) -> bytes:
    """Return dest bytes for copy-like modes."""
    if mode == MODE_CURSOR_MDC:
        if not scenario_id:
            raise ValueError("cursor render is missing scenario_id")
        return render_cursor_mdc(source, scenario_id=scenario_id)
    return _load_file_bytes(source)


def is_directory_trees_identical(left: Path, right: Path) -> bool:
    """Return True when both paths exist and hold the same file bytes."""
    if left.is_file() and right.is_file():
        return _load_file_bytes(left) == _load_file_bytes(right)
    if not left.is_dir() or not right.is_dir():
        return False
    left_map = {
        item.relative_to(left).as_posix(): _load_file_bytes(item)
        for item in _find_files(left)
    }
    right_map = {
        item.relative_to(right).as_posix(): _load_file_bytes(item)
        for item in _find_files(right)
    }
    return left_map == right_map


def _clear_replaceable_tree(dest: Path) -> None:
    children = _find_local_entries(dest)
    ordered = sorted(children, key=lambda item: len(item.parts), reverse=True)
    for child in ordered:
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    dest.rmdir()


def _inspect_symlink_state(dest: Path, source: Path) -> str:
    """Evaluate drift when spec expects a symlink."""
    if dest.is_symlink():
        try:
            return (
                "ok" if dest.resolve() == source.resolve() else "wrong-symlink"
            )
        except OSError:
            return "broken-symlink"
    if dest.is_file() or dest.is_dir():
        return (
            "regular-same"
            if is_directory_trees_identical(dest, source)
            else "regular-differs"
        )
    return "unexpected-type"


def _inspect_copy_state(
    dest: Path, source: Path, mode: str, scenario_id: str | None
) -> str:
    """Evaluate drift when spec expects a copy or rendered mdc."""
    if dest.is_symlink():
        return "symlink-for-copy"
    if dest.is_file() and source.is_file():
        expected = render_expected_payload(
            source, mode, scenario_id=scenario_id
        )
        return "ok" if _load_file_bytes(dest) == expected else "copy-differs"
    return "unexpected-type"


def inspect_dest_drift(
    dest: Path, source: Path, mode: str, *, scenario_id: str | None = None
) -> str:
    """Return ok, missing, or a drift token for one dest."""
    if not dest.exists() and not dest.is_symlink():
        return "missing"
    if mode == MODE_SYMLINK:
        return _inspect_symlink_state(dest, source)
    if mode in (MODE_COPY, MODE_CURSOR_MDC):
        return _inspect_copy_state(dest, source, mode, scenario_id)
    return "unexpected-type"


def inspect_spec_drift(grok_root: Path, home: Path, spec: AdapterSpec) -> str:
    """Return ok or a drift token. missing source is source-missing."""
    source = resolve_source(grok_root, spec)
    dest = resolve_dest(home, spec)
    if not source.exists():
        return "source-missing"
    if not _is_dest_parent_under_home(home, dest):
        return "dest-escapes"
    if _is_skills_directory_spec(spec):
        return _inspect_skills_directory(grok_root, home)
    state = inspect_dest_drift(
        dest, source, spec.mode, scenario_id=spec.scenario_id
    )
    if state == "ok":
        return "ok"
    return state


def _is_applyable(state: str) -> bool:
    return state in (
        "ok",
        "missing",
        "incomplete",
        "collapsed-symlink",
        "wrong-symlink",
        "broken-symlink",
        "symlink-for-copy",
        "regular-same",
        "copy-differs",
    )


def _is_skills_directory_spec(spec: AdapterSpec) -> bool:
    """Return True for the per-skill link directory."""
    return spec.source == "skills" and spec.dest == ".grok/skills"


def _resolve_skill_links(grok_root: Path, home: Path) -> dict[str, Path] | str:
    """Return link name to source path, or an error string."""
    skills = grok_root / "skills"
    links = {child.name: child.resolve() for child in skills.iterdir()}
    catalog = resolve_catalog_path(grok_root)
    extra = resolve_catalog_skill_sources(catalog)
    if isinstance(extra, str):
        return extra
    for name, source in extra.items():
        previous = links.get(name)
        if previous is not None and previous != source:
            return f"skill name collision: {name}"
        links[name] = source
    return links


def _is_symlink_target(child: Path, source: Path) -> bool:
    """Return True when child is a symlink to source."""
    if not child.is_symlink():
        return False
    try:
        return child.resolve() == source.resolve()
    except OSError:
        return False


def _is_identical_entry(child: Path, source: Path) -> bool:
    """Return True when a regular child has the same bytes as source."""
    if child.is_symlink():
        return False
    if child.is_file() and source.is_file():
        return _load_file_bytes(child) == _load_file_bytes(source)
    if child.is_dir() and source.is_dir():
        return is_directory_trees_identical(child, source)
    return False


def _inspect_skills_directory(grok_root: Path, home: Path) -> str:
    """Return drift for .grok/skills as one symlink per skill."""
    expected = _resolve_skill_links(grok_root, home)
    if isinstance(expected, str):
        if expected.startswith("skill name collision:"):
            return "skill-name-conflict"
        if expected == "source-missing":
            return "source-missing"
        return "unexpected-type"
    dest = home / ".grok" / "skills"
    if dest.is_symlink():
        return "collapsed-symlink"
    if not dest.exists():
        return "missing"
    if not dest.is_dir():
        return "unexpected-type"
    present = {child.name for child in dest.iterdir()}
    if present - expected.keys():
        return "regular-differs"
    needs_link = False
    for name, source in expected.items():
        child = dest / name
        if name not in present:
            needs_link = True
            continue
        if _is_symlink_target(child, source):
            continue
        if child.is_symlink():
            return "regular-differs"
        if _is_identical_entry(child, source):
            needs_link = True
            continue
        return "regular-differs"
    if needs_link:
        return "incomplete"
    return "ok"


def _reconcile_skills_directory(grok_root: Path, home: Path) -> str:
    """Create one symlink per skill. Leave unexpected names in place."""
    state = _inspect_skills_directory(grok_root, home)
    if state == "ok":
        return "skipped"
    applyable = {
        "missing",
        "incomplete",
        "collapsed-symlink",
        "regular-same",
    }
    if state not in applyable:
        return state
    expected = _resolve_skill_links(grok_root, home)
    if isinstance(expected, str):
        return state
    dest = home / ".grok" / "skills"
    if dest.is_symlink():
        dest.unlink()
    if not dest.exists():
        dest.mkdir(parents=True)
    if not dest.is_dir():
        return "unexpected-type"
    for name, source in expected.items():
        child = dest / name
        if _is_symlink_target(child, source):
            continue
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            _clear_replaceable_tree(child)
        child.symlink_to(source, target_is_directory=source.is_dir())
    return "applied"


def reconcile_spec(grok_root: Path, home: Path, spec: AdapterSpec) -> str:
    """Materializes a single specification destination.

    Returns the execution status token.
    """
    source = resolve_source(grok_root, spec)
    dest = resolve_dest(home, spec)
    if not source.exists():
        return "source-missing"
    if not _is_dest_parent_under_home(home, dest):
        return "dest-escapes"
    if _is_skills_directory_spec(spec):
        return _reconcile_skills_directory(grok_root, home)
    state = inspect_dest_drift(
        dest, source, spec.mode, scenario_id=spec.scenario_id
    )
    if state == "ok":
        return "skipped"
    if state == "regular-differs":
        return "regular-differs"
    if not _is_applyable(state):
        return state
    if not _provision_dest_parents(home, dest):
        return "dest-escapes"
    if not _is_dest_parent_under_home(home, dest):
        return "dest-escapes"
    state = inspect_dest_drift(
        dest, source, spec.mode, scenario_id=spec.scenario_id
    )
    if state == "ok":
        return "skipped"
    if state == "regular-differs":
        return "regular-differs"
    if not _is_applyable(state):
        return state
    if spec.mode == MODE_SYMLINK:
        if dest.is_dir() and not dest.is_symlink():
            _clear_replaceable_tree(dest)
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
        _clear_replaceable_tree(dest)
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(
                render_expected_payload(
                    source, spec.mode, scenario_id=spec.scenario_id
                )
            )
        if spec.mode == MODE_COPY and source.stat().st_mode & 0o111:
            tmp.chmod(tmp.stat().st_mode | 0o111)
        os.replace(tmp, dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return "applied"


def inspect_all_specs(grok_root: Path, home: Path) -> int:
    """Print dest status. Return 1 when any dest is not ok."""
    failed = False
    for spec in SPECS:
        status = inspect_spec_drift(grok_root, home, spec)
        if status == "ok":
            print(f"OK    {spec.dest}")
            continue
        failed = True
        print(f"DRIFT {spec.dest}: {status}")
    return 1 if failed else 0


def reconcile_all_specs(grok_root: Path, home: Path) -> int:
    """Refuse mismatched dests, then materialize. Return 1 on abort."""
    blocked: list[tuple[str, str]] = []
    for spec in SPECS:
        status = inspect_spec_drift(grok_root, home, spec)
        if status == "ok":
            continue
        if status == "regular-differs":
            blocked.append((spec.dest, status))
            continue
        if status == "source-missing" or status == "dest-escapes":
            blocked.append((spec.dest, status))
            continue
        if status == "unexpected-type" or status == "skill-name-conflict":
            blocked.append((spec.dest, status))
    if blocked:
        for dest, status in blocked:
            print(f"ABORT {dest}: {status}")
        return 1
    failed = False
    for spec in SPECS:
        result = reconcile_spec(grok_root, home, spec)
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
        args.grok_root.resolve() if args.grok_root else resolve_grok_root()
    )
    home = args.home.resolve() if args.home else Path.home()
    if args.command == "apply":
        return reconcile_all_specs(grok_root, home)
    return inspect_all_specs(grok_root, home)


if __name__ == "__main__":
    raise SystemExit(main())
