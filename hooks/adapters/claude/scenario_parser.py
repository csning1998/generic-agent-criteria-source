"""Scenario and frontmatter parsing helpers for Claude Code and Cursor hooks."""

from __future__ import annotations

import fnmatch
import re
import sys
from pathlib import Path


ARRAY_KEYS = (
    "path_glob",
    "command_prefix",
    "readonly_command_glob",
    "command_glob",
)


def parse_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter arrays used by criteria scenario files."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    data: dict = {
        "load": [],
        "path_glob": [],
        "command_glob": [],
        "command_prefix": [],
        "readonly_command_glob": [],
    }
    section = None
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("id:"):
            data["id"] = stripped.split(":", 1)[1].strip()
            section = None
            continue
        if stripped == "load:":
            section = "load"
            continue
        matched_key = next(
            (k for k in ARRAY_KEYS if stripped.startswith(k + ":")), None
        )
        if matched_key is not None:
            rest = stripped[len(matched_key) + 1 :].strip()
            data[matched_key] = re.findall(r'"([^"]+)"', rest)
            section = None if rest.endswith("]") else matched_key
            continue
        if stripped.startswith("- ") and section == "load":
            data["load"].append(stripped[2:].strip())
            continue
        if section in ARRAY_KEYS:
            data[section].extend(re.findall(r'"([^"]+)"', stripped))
            if stripped.endswith("]"):
                section = None
            continue
        if re.match(r"^[a-zA-Z_]+:", stripped):
            section = None
    if section in ARRAY_KEYS:
        print(
            f"WARNING: {path} has an unclosed '{section}' array "
            "(no closing ']' found); entries may be missing.",
            file=sys.stderr,
        )
    return data


def parse_languages_entries(path: Path) -> list[dict]:
    """Parse entries from languages.md into scenario dictionaries."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return []
    end = text.find("\n---", 3)
    if end == -1:
        return []
    block = text[3:end]
    entries: list[dict] = []
    current: dict | None = None
    in_load = False

    def _record_current_entry():
        nonlocal current, in_load
        if current and current.get("id"):
            entries.append(current)
        current = None
        in_load = False

    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- id:"):
            _record_current_entry()
            entry_id = stripped.split(":", 1)[1].strip()
            current = {
                "id": entry_id,
                "load": [],
                "path_glob": [],
                "command_glob": [],
                "command_prefix": [],
                "readonly_command_glob": [],
            }
            continue
        if current is None:
            continue
        if stripped.startswith("path_glob:"):
            rest = stripped.split(":", 1)[1].strip()
            current["path_glob"] = re.findall(r'"([^"]+)"', rest)
            in_load = False
            continue
        if stripped == "load:":
            in_load = True
            continue
        if in_load and stripped.startswith("- "):
            current["load"].append(stripped[2:].strip())
            continue
        if not stripped.startswith("- "):
            in_load = False

    _record_current_entry()
    return entries


def load_scenarios_from_dir(criteria_dir: Path) -> list[dict]:
    """Load the frontmatter of every criteria scenario under criteria_dir."""
    if not criteria_dir.is_dir():
        return []
    scenarios = []
    scenarios_dir = criteria_dir / "2_context" / "scenarios"
    paths = (
        sorted(scenarios_dir.glob("*.md"))
        if scenarios_dir.is_dir()
        else sorted(criteria_dir.glob("*.md"))
    )
    for path in paths:
        if path.name == "languages.md":
            scenarios.extend(parse_languages_entries(path))
        else:
            meta = parse_frontmatter(path)
            if meta.get("id"):
                scenarios.append(meta)
    return scenarios


def compute_glob_specificity(pattern: str) -> int:
    """Score a path_glob pattern by its literal character count."""
    return sum(1 for char in pattern if char not in "*?")


def find_most_specific_scenario(
    scenarios: list[dict], file_path: str
) -> dict | None:
    """Return the scenario whose path_glob best matches file_path's name.

    When several scenarios match, the highest specificity score wins.
    A literal `merge-request.md` therefore beats a broad `*.md`.
    """
    name = Path(file_path).name
    best: dict | None = None
    best_score = -10_000
    for meta in scenarios:
        for pattern in meta.get("path_glob", []):
            if not fnmatch.fnmatch(name, pattern):
                continue
            score = compute_glob_specificity(pattern)
            if score > best_score:
                best_score = score
                best = meta
    return best
