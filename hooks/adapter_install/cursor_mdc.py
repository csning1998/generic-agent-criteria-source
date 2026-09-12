"""Render Cursor `.mdc` shells from scenario frontmatter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_ID = re.compile(r"(?m)^id:\s*([A-Za-z0-9_-]+)\s*$")
_CURSOR_KEY = re.compile(r"(?m)^(?P<indent>[ \t]+)cursor:\s*(?P<rest>.*)$")
_GLOBS = re.compile(r'\bglobs:\s*"([^"]+)"')
_KEY_LINE = re.compile(r"^[a-zA-Z_]+:")


@dataclass(frozen=True)
class CursorScenario:
    """Parsed Cursor adapter fields from one scenario file."""

    scenario_id: str
    globs: str
    load: tuple[str, ...]


def frontmatter(text: str) -> str | None:
    """Return YAML between the opening fences, or None."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    return text[4:end]


def _load_entries(block: str) -> tuple[str, ...]:
    """Collect dash items under `load:`, ignoring list indent."""
    items: list[str] = []
    in_load = False
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "load:":
            in_load = True
            continue
        if stripped.startswith("- ") and in_load:
            items.append(stripped[2:].strip())
            continue
        if _KEY_LINE.match(stripped):
            in_load = False
    return tuple(items)


def _cursor_globs(block: str) -> str | None:
    """Return globs when a cursor adapter key exists, or None when absent."""
    match = _CURSOR_KEY.search(block)
    if match is None:
        return None
    flow = _GLOBS.search(match.group("rest"))
    if flow is not None:
        return flow.group(1)
    indent = match.group("indent")
    nested: list[str] = []
    for line in block[match.end() :].splitlines():
        if not line.strip():
            continue
        extra = line[len(indent) :] if line.startswith(indent) else ""
        if not extra[:1].isspace():
            break
        nested.append(line)
    nested_match = _GLOBS.search("\n".join(nested))
    if nested_match is None:
        raise ValueError("cursor adapter is missing globs")
    return nested_match.group(1)


def parse_cursor_scenario(text: str) -> CursorScenario | None:
    """Return Cursor fields when adapters.cursor is present."""
    raw = frontmatter(text)
    if raw is None:
        return None
    globs = _cursor_globs(raw)
    if globs is None:
        return None
    ident = _ID.search(raw)
    if ident is None:
        raise ValueError("cursor scenario is missing id")
    load = _load_entries(raw)
    if not load:
        raise ValueError(f"cursor scenario {ident.group(1)} is missing load")
    return CursorScenario(
        scenario_id=ident.group(1),
        globs=globs,
        load=load,
    )


def iter_cursor_scenarios(
    grok_root: Path,
) -> tuple[tuple[str, CursorScenario], ...]:
    """Yield relative source path and parsed fields for each Cursor scenario."""
    criteria = grok_root / "hooks" / "criteria"
    rows: list[tuple[str, CursorScenario]] = []
    for path in sorted(criteria.glob("*.md")):
        parsed = parse_cursor_scenario(path.read_text(encoding="utf-8"))
        if parsed is None:
            continue
        rel = path.relative_to(grok_root).as_posix()
        rows.append((rel, parsed))
    return tuple(rows)


def render_cursor_mdc(scenario_path: Path) -> bytes:
    """Return thin `.mdc` bytes. L2 bodies stay in references/."""
    parsed = parse_cursor_scenario(scenario_path.read_text(encoding="utf-8"))
    if parsed is None:
        raise ValueError(f"no cursor adapter in {scenario_path}")
    lines = [
        "---",
        f"description: {parsed.scenario_id} L2 criteria",
        f'globs: "{parsed.globs}"',
        "alwaysApply: false",
        "---",
        "",
        "The Agent MUST open each `@` path prior to mutating a matching path.",
        "Duplication of the listed files in the `.mdc` body is prohibited.",
        "",
    ]
    for item in parsed.load:
        lines.append(f"@~/.agents/criteria/{item}")
    lines.append("")
    return "\n".join(lines).encode("utf-8")
