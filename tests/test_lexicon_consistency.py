"""Lexicon invariants for hook identifiers and criteria tokens."""

from __future__ import annotations

import ast
import re
from pathlib import Path


_REPO = Path(__file__).resolve().parent.parent
_LEXICON = _REPO / "docs/coding-standards/lexicon.md"
_HOOKS = _REPO / "hooks"
_SCENARIOS = _HOOKS / "criteria" / "2_context" / "scenarios"
_CRITERIA = _HOOKS / "criteria"

KNOWN_PENDING_RENAME = frozenset(
    {
        "deny",
        "allow",
        "deny_cursor_external_write",
        "block_stop",
    }
)

# Terraform CLI flags, SELinux filenames, and mesh identity issuers.
_ALLOWED_PLATFORM_SUBSTRINGS = (
    "terraform providers lock -platform=",
    "target platform",
    "missing platform hash",
    "61-container-runtime-and-selinux.md",
    "Originates from the Platform",
    "issued by the platform",
    "Platform Engineering",
)


def _permitted_prefixes() -> tuple[str, ...]:
    """Parse Permitted Leading Verbs from lexicon.md Section 1."""
    text = _LEXICON.read_text(encoding="utf-8")
    section = text.split("## Section 2.")[0]
    prefixes: list[str] = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0].startswith("-") or cells[0] == "Verb Category":
            continue
        prefixes.extend(re.findall(r"`([a-z]+_)`", cells[1]))
    return tuple(dict.fromkeys(prefixes))


def _function_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    ]


def _name_matches_lexicon(name: str, prefixes: tuple[str, ...]) -> bool:
    if name == "main":
        return True
    if name.startswith("__") and name.endswith("__"):
        return True
    if name.startswith("test_"):
        return True
    stripped = name.lstrip("_")
    if stripped in KNOWN_PENDING_RENAME:
        return True
    bare = {prefix.rstrip("_") for prefix in prefixes}
    if stripped in bare:
        return True
    return any(stripped.startswith(prefix) for prefix in prefixes)


def test_module_level_function_names_use_approved_prefixes() -> None:
    """Every hooks/ def uses a Section 1 prefix or a named pending rename."""
    prefixes = _permitted_prefixes()
    assert prefixes
    offenders: list[str] = []
    for path in sorted(_HOOKS.rglob("*.py")):
        for name in _function_names(path):
            if _name_matches_lexicon(name, prefixes):
                continue
            offenders.append(f"{path.relative_to(_REPO)}:{name}")
    assert offenders == []


def test_criteria_scenarios_omit_the_retired_surface_key() -> None:
    """Scenario frontmatter uses verdict: rather than surface:."""
    hits = []
    for path in sorted(_SCENARIOS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "surface:" in text:
            hits.append(path.name)
    assert hits == []


def test_criteria_prose_omits_retired_harness_synonyms() -> None:
    """hooks/criteria prose does not use platform as a Harness synonym."""
    hits: list[str] = []
    for path in sorted(_CRITERIA.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "platform" not in text.lower():
            continue
        remainder = text
        for allowed in _ALLOWED_PLATFORM_SUBSTRINGS:
            remainder = remainder.replace(allowed, "")
        if re.search(r"platform", remainder, flags=re.IGNORECASE):
            hits.append(str(path.relative_to(_REPO)))
    assert hits == []


def test_gate_check_and_post_write_review_share_the_same_harness_predicate_name() -> (
    None
):
    """Gate-check and post-write-review share is_cursor_harness."""
    gate_names = set(
        _function_names(_HOOKS / "adapters" / "claude" / "gate-check.py")
    )
    post_names = set(
        _function_names(_HOOKS / "adapters" / "claude" / "post-write-review.py")
    )
    assert "is_cursor_harness" in gate_names
    assert "is_cursor_harness" in post_names
    assert "is_cursor_runtime" not in gate_names
    assert "is_cursor_runtime" not in post_names
