#!/usr/bin/env python3
"""Executes post-tool verification for Claude Code based on scenario criteria.

Triggers post-execution evaluation following `Edit` or `Write` tool calls
matching target `path_glob` patterns. Injects scenario context files
defined in `load:` via `additionalContext` once per session per scenario,
instructing immediate file re-check and inline violation remediation.

Uses an isolated state-marker namespace (`STATE_PREFIX`) distinct from
`gate-check.py`'s, keeping the two hooks' state independent.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from pathlib import Path


CRITERIA_DIR = Path.home() / ".agents" / "criteria"
STATE_DIR = Path(f"/tmp/claude-gate-state-{os.getuid()}")
STATE_PREFIX = "post-review"

# Mirrors gate-check.py's 401(f)/(d) static checks. A PreToolUse failure
# which raises no error leaves the write unverified without this second
# pass.
BARE_IT_PATTERN = re.compile(r"(?:#|//).*\bit\b", re.IGNORECASE)
# "them" is always a pronoun, never a determiner, unlike
# "this"/"that"/"these"/"those", which also serve as determiners
# immediately before a noun and MAY legitimately appear that way.
BARE_THEM_PATTERN = re.compile(r"(?:#|//).*\bthem\b", re.IGNORECASE)
# "otherwise" (including "would otherwise") is banned outright by
# 401(f), with no determiner exception to carve out.
OTHERWISE_PATTERN = re.compile(r"(?:#|//).*\botherwise\b", re.IGNORECASE)
COMMA_SO_PATTERN = re.compile(r"^\s*(?:#|//).*,\s*so\b", re.IGNORECASE)
# Catches the escape-hatch "so" even without a preceding comma (e.g.
# "variables so a test can shrink them"), narrowed to a nearby modal
# so idioms like "so-called" or "so far" do not match.
BARE_SO_PATTERN = re.compile(
    r"(?:#|//).*\bso\s+(?:\w+\s+){0,4}"
    r"(?:can|could|will|would|must|may|might|should)\b",
    re.IGNORECASE,
)
# Flags a contrast clause for the 401(d) Defensive Fluff Versus Guardrail
# Test. The test itself needs a judgment call about substitution risk;
# this pattern only surfaces the clause for that classification.
CONTRAST_CLAUSE_PATTERN = re.compile(
    r"(?:#|//).*(?:\brather than\b|,\s*not\b)", re.IGNORECASE
)
TEMPORAL_DEPENDENCY_PATTERN = re.compile(
    r"^\s*(?:#|//).*\b(this session|current session|mid-session|"
    r"has been observed|this task|current task|current fix|this fix|"
    r"currently|for now|as of now|at the moment|for the time being|"
    r"temporarily|recently|right now|nowadays)\b",
    re.IGNORECASE,
)
COMMENT_LINE_PATTERN = re.compile(r"^\s*(?:#|//)")
MAX_COMMENT_BLOCK_LINES = 3
COMMENT_CHECK_SKIP_GLOBS = ("*.md", "*.mdx")

# VIOLATION tags a deterministic, unconditional 401 ban on one word or
# symbol. REMINDER tags a heuristic proxy for a rule 401 itself asks the
# agent to classify, or a proxy which cannot fully rule out a false match.
VIOLATION = "VIOLATION"
REMINDER = "REMINDER"

# A genitive 's reads as colloquial in this register regardless of the
# attached noun, per 401(f) Prohibition of Colloquialisms.
POSSESSIVE_APOSTROPHE_PATTERN = re.compile(r"(?:#|//).*\w+'s\b")
WHICH_WORD_PATTERN = re.compile(r"\bwhich\b", re.IGNORECASE)
THAT_WORD_PATTERN = re.compile(r"\bthat\b", re.IGNORECASE)

# 401(f) Relative Clause Formation: "that" MUST NOT introduce a relative
# clause. This pattern catches only the subject-relative shape. The
# object-relative shape is left to the self-review pass.
THAT_RELATIVE_CLAUSE_PATTERN = re.compile(
    r"\bthat\s+(?:is|are|was|were|has|have|had|carries|consumes|"
    r"holds|reads|resolves|requires|defines|matches|applies|"
    r"governs|must|shall|should|may|can|could|will|would)\b",
    re.IGNORECASE,
)
# 401(f) Impersonal Tone: this/that/these/those MUST NOT occupy the
# subject position. A demonstrative directly before a verb or modal
# triggers this pattern; a determiner use like "this test MUST" does not.
DEMONSTRATIVE_SUBJECT_PATTERN = re.compile(
    r"\b(?:this|that|these|those)\s+(?:is|are|was|were|has|have|had|"
    r"must|shall|should|may|can|could|will|would)\b",
    re.IGNORECASE,
)
# 401(f) Impersonal Tone: this/that/these/those MUST NOT occupy the
# object position. A demonstrative immediately before clause-ending
# punctuation has no following noun and is a bare pronoun instead.
DEMONSTRATIVE_OBJECT_PATTERN = re.compile(
    r"\b(?:this|that|these|those)\s*[.,](?:\s|$)", re.IGNORECASE
)
# 401(f) Relative Clause Formation, non-relative use: a sentence-initial
# "Which" is never introducing a relative clause, because a relative
# clause requires an antecedent earlier in the same sentence.
WHICH_SENTENCE_INITIAL_PATTERN = re.compile(r"(?:^|[.!?]\s+)Which\b")
# 401(f) Prohibition of Preposition Stranding: a preposition MUST NOT
# end a clause.
PREPOSITION_STRANDING_PATTERN = re.compile(
    r"\b(?:in|on|at|to|for|with|from|of|by|about|into|onto|through|"
    r"over|under|between|among|against|across|after|before|during)"
    r"\s*[.,](?:\s|$)",
    re.IGNORECASE,
)
# 401(g) Prohibited Symbols: em-dash, en-dash, and arrow glyphs are
# banned outright. A plain hyphen is excluded, because a hyphen also
# forms ordinary compound words (e.g. "non-obvious").
DASH_ARROW_PATTERN = re.compile(r"[–—→←⇒]")
# 401(f) Prohibition of Punctuation-Forced Clauses: a semicolon
# joining two clauses is banned.
SEMICOLON_PATTERN = re.compile(r"(?:#|//).*;")
# 401(f) Impersonal Tone: first-person pronouns MUST NOT be used. "I"
# stays case-sensitive, because a correctly capitalized pronoun is the
# only spelling that is never a loop variable.
FIRST_PERSON_I_PATTERN = re.compile(r"\bI\b")
FIRST_PERSON_WE_PATTERN = re.compile(r"\b(?:we|us|our|ours)\b", re.IGNORECASE)
# 401(f) Prohibition of Bare Negation: a finite verb MUST NOT negate an
# object with a bare "no". "leaving no X" (a participle) and "with no
# X" (a preposition) are excluded by this finite-verb list.
BARE_NEGATION_PATTERN = re.compile(
    r"\b(?:declares?|holds?|carries?|has|have|had|contains?|"
    r"provides?|returns?|accepts?|requires?|reports?|yields?|"
    r"produces?)\s+no\s+\w+",
    re.IGNORECASE,
)
# 401(d) Prohibition of the Defensive Analogy: justifying the current
# case by comparison to an already-tested case is banned outright.
DEFENSIVE_ANALOGY_PATTERN = re.compile(
    r"\b(?:exactly like|just as with|just like)\b", re.IGNORECASE
)

ARRAY_KEYS = (
    "path_glob",
    "command_prefix",
    "readonly_command_glob",
    "command_glob",
)


def parse_frontmatter(path: Path) -> dict:
    """Parse the YAML-flow-style arrays used by hooks/criteria/*.md."""
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
    return data


def load_scenarios() -> list[dict]:
    """Load every criteria scenario's frontmatter under CRITERIA_DIR."""
    if not CRITERIA_DIR.is_dir():
        return []
    scenarios = []
    for path in sorted(CRITERIA_DIR.glob("*.md")):
        meta = parse_frontmatter(path)
        if meta.get("id"):
            scenarios.append(meta)
    return scenarios


def match_path(scenarios: list[dict], file_path: str) -> dict | None:
    """Return the first scenario whose path_glob matches file_path's name."""
    name = Path(file_path).name
    for meta in scenarios:
        for pattern in meta.get("path_glob", []):
            if fnmatch.fnmatch(name, pattern):
                return meta
    return None


def resolve_load_text(meta: dict) -> str:
    """Concatenate the referenced text of every file in meta's load list."""
    parts = []
    for rel in meta.get("load", []):
        ref_path = CRITERIA_DIR / rel
        if ref_path.exists():
            text = ref_path.read_text(encoding="utf-8")
            parts.append(f"=== {rel} ===\n{text}")
    return "\n\n".join(parts)


def marker(session_id: str, scenario_id: str) -> Path:
    """Return the state-marker path for session_id and scenario_id."""
    return STATE_DIR / session_id / f"{STATE_PREFIX}__{scenario_id}"


def already_surfaced(session_id: str, scenario_id: str) -> bool:
    """Return whether scenario_id was already surfaced this session."""
    return marker(session_id, scenario_id).exists()


def _ensure_private_dir(path: Path) -> None:
    """Make path a real 0o700 directory.

    Discards a pre-existing symlink or non-directory entry a predictable
    /tmp path could have collected.
    """
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        path.unlink()
    path.mkdir(mode=0o700, exist_ok=True)
    os.chmod(path, 0o700)


def mark_surfaced(session_id: str, scenario_id: str) -> None:
    """Record scenario_id as surfaced for session_id."""
    _ensure_private_dir(STATE_DIR)
    _ensure_private_dir(STATE_DIR / session_id)
    marker(session_id, scenario_id).touch(mode=0o600, exist_ok=True)


def emit(additional_context: str) -> None:
    """Print a PostToolUse hookSpecificOutput payload carrying context."""
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": additional_context,
        }
    }
    print(json.dumps(payload))


def _find_line_violations(line: str, stripped: str) -> list[str]:
    """Return every per-line register finding line triggers, each tagged."""
    violations: list[str] = []
    if BARE_IT_PATTERN.search(line):
        violations.append(
            f"[{VIOLATION}] bare pronoun 'it' with no antecedent noun: "
            f"{stripped!r}"
        )
    if BARE_THEM_PATTERN.search(line):
        violations.append(
            f"[{VIOLATION}] bare pronoun 'them' with no antecedent noun: "
            f"{stripped!r}"
        )
    if OTHERWISE_PATTERN.search(line):
        violations.append(
            f"[{VIOLATION}] escape-hatch 'otherwise' implying an "
            f"unstated counterfactual: {stripped!r}"
        )
    if COMMA_SO_PATTERN.search(line):
        violations.append(
            f"[{VIOLATION}] comma-'so' causal connector: {stripped!r}"
        )
    elif BARE_SO_PATTERN.search(line):
        violations.append(
            f"[{VIOLATION}] bare escape-hatch 'so' connector: {stripped!r}"
        )
    if CONTRAST_CLAUSE_PATTERN.search(line):
        violations.append(
            f"[{REMINDER}] contrast clause ('rather than' / ', not ...') "
            "present; classify it against 401(d)'s Defensive Fluff Versus "
            f"Guardrail Test before keeping it: {stripped!r}"
        )
    if TEMPORAL_DEPENDENCY_PATTERN.search(line):
        violations.append(
            f"[{REMINDER}] temporal-dependency language in a comment: "
            f"{stripped!r}"
        )
    if POSSESSIVE_APOSTROPHE_PATTERN.search(line):
        violations.append(
            f"[{VIOLATION}] colloquial genitive 's in a comment: {stripped!r}"
        )
    return violations


def _find_comment_body_violations(
    comment_body: str, stripped: str
) -> list[str]:
    """Return every register finding scoped to one comment line, tagged."""
    violations: list[str] = []
    if THAT_RELATIVE_CLAUSE_PATTERN.search(comment_body):
        violations.append(
            f"[{REMINDER}] 'that' looks like it introduces a relative "
            f"clause; use 'which' if so: {stripped!r}"
        )
    if DEMONSTRATIVE_SUBJECT_PATTERN.search(comment_body):
        violations.append(
            f"[{REMINDER}] possible bare demonstrative in subject "
            f"position: {stripped!r}"
        )
    if DEMONSTRATIVE_OBJECT_PATTERN.search(comment_body):
        violations.append(
            f"[{REMINDER}] possible bare demonstrative in object "
            f"position: {stripped!r}"
        )
    if PREPOSITION_STRANDING_PATTERN.search(comment_body):
        violations.append(
            f"[{REMINDER}] possible stranded preposition at clause end: "
            f"{stripped!r}"
        )
    if DASH_ARROW_PATTERN.search(comment_body):
        violations.append(
            f"[{VIOLATION}] em-dash, en-dash, or arrow glyph: {stripped!r}"
        )
    has_first_person = FIRST_PERSON_I_PATTERN.search(
        comment_body
    ) or FIRST_PERSON_WE_PATTERN.search(comment_body)
    if has_first_person:
        violations.append(f"[{VIOLATION}] first-person pronoun: {stripped!r}")
    if BARE_NEGATION_PATTERN.search(comment_body):
        violations.append(
            f"[{REMINDER}] possible bare 'no' negating a finite clause: "
            f"{stripped!r}"
        )
    if DEFENSIVE_ANALOGY_PATTERN.search(comment_body):
        violations.append(
            f"[{REMINDER}] possible defensive analogy to a separate "
            f"case: {stripped!r}"
        )
    return violations


def find_register_violations(text: str) -> list[str]:
    """Return one tagged finding per mechanical register check in text.

    Each returned string starts with `[VIOLATION]` or `[REMINDER]`; see
    the VIOLATION/REMINDER constants above for the distinction.
    """
    violations: list[str] = []
    lines = text.splitlines()
    block_len = 0
    block_words: list[str] = []
    block_which_that_flagged = False
    for line in lines:
        stripped = line.strip()
        violations.extend(_find_line_violations(line, stripped))
        if SEMICOLON_PATTERN.search(line):
            violations.append(
                f"[{VIOLATION}] semicolon joining two clauses: {stripped!r}"
            )
        if COMMENT_LINE_PATTERN.match(line) and stripped not in ("#", "//"):
            comment_body = COMMENT_LINE_PATTERN.sub("", line, count=1)
            violations.extend(
                _find_comment_body_violations(comment_body, stripped)
            )
            block_len += 1
            block_words.append(comment_body.strip())
            block_text = " ".join(block_words)
            if WHICH_SENTENCE_INITIAL_PATTERN.search(block_text):
                violations.append(
                    f"[{REMINDER}] possible sentence-initial 'Which' "
                    f"with no antecedent: {block_text!r}"
                )
            if (
                not block_which_that_flagged
                and WHICH_WORD_PATTERN.search(block_text)
                and THAT_WORD_PATTERN.search(block_text)
            ):
                violations.append(
                    f"[{REMINDER}] 'which' and 'that' both appear in "
                    "the same comment block; consider using only one: "
                    f"{block_text!r}"
                )
                block_which_that_flagged = True
            if block_len == MAX_COMMENT_BLOCK_LINES + 1:
                violations.append(
                    f"[{VIOLATION}] comment block exceeds "
                    f"{MAX_COMMENT_BLOCK_LINES} lines, starting near: "
                    f"{stripped!r}"
                )
        else:
            block_len = 0
            block_words = []
            block_which_that_flagged = False
    return violations


def _render_register_message(violations: list[str]) -> str:
    """Render tagged findings as one VIOLATION section, one REMINDER section."""
    hard = [v for v in violations if v.startswith(f"[{VIOLATION}]")]
    soft = [v for v in violations if v.startswith(f"[{REMINDER}]")]
    sections = []
    if hard:
        listed = "\n".join(f"- {v}" for v in hard)
        sections.append(
            "Register VIOLATION DETECTED (mechanical check, not "
            "advisory): fix every line below in the file now, before "
            f"any other action.\n{listed}"
        )
    if soft:
        listed = "\n".join(f"- {v}" for v in soft)
        sections.append(
            "Register REMINDER (heuristic, needs a judgment call): "
            f"review every line below against 401(d)/(f) before the "
            f"next action.\n{listed}"
        )
    return "\n\n".join(sections)


def main() -> None:
    """Run the PostToolUse register and scenario-load checks on stdin."""
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    if payload.get("tool_name") not in ("Edit", "Write"):
        return
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return

    skip = COMMENT_CHECK_SKIP_GLOBS
    if not any(fnmatch.fnmatch(Path(file_path).name, g) for g in skip):
        write_text = (
            tool_input.get("new_string") or tool_input.get("content") or ""
        )
        violations = find_register_violations(write_text)
        if violations:
            emit(_render_register_message(violations))
            return

    scenarios = load_scenarios()
    meta = match_path(scenarios, file_path)
    if meta is None:
        meta = next(
            (m for m in scenarios if m.get("id") == "local-mutate"), None
        )
    if meta is None:
        return

    session_id = payload.get("session_id", "unknown")
    scenario_id = meta["id"]
    file_name = Path(file_path).name

    if not already_surfaced(session_id, scenario_id):
        mark_surfaced(session_id, scenario_id)
        rules = resolve_load_text(meta)
        emit(
            f"Post-write self-review ({scenario_id} scenario) for "
            f"{file_name}. Re-read the rules below against the file you "
            "just wrote. Fix any violation directly in the file now; do "
            "not just acknowledge the violation.\n\n"
            f"{rules}"
        )
    else:
        emit(
            f"Post-write self-review ({scenario_id} scenario) for {file_name}. "
            f"Rules already surfaced this session for '{scenario_id}'. "
            "Re-check this specific write against those rules and fix any "
            "violation directly, without re-reading the full text again."
        )


if __name__ == "__main__":
    main()
