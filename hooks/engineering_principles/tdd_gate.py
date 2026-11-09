"""Test-Driven Development (TDD) gate and state machine enforcement (§ 202)."""

from __future__ import annotations

import ast
import fnmatch
import re
import subprocess
from pathlib import Path
from pathlib import PurePath
from typing import Any

from engineering_principles.config import GREEN_AUTH_RE
from engineering_principles.config import LINTER_CMD_RE
from engineering_principles.config import MUTATING_TOOLS
from engineering_principles.config import TDD_TEST_GLOBS
from engineering_principles.config import TEST_RUNNER_CMD_RE
from engineering_principles.payload import extract_latest_user_request
from engineering_principles.state import load_state
from engineering_principles.state import persist_state
from engineering_principles.state import resolve_workspace_root


def is_tdd_test_path(path: str) -> bool:
    """Return True if path matches TDD test patterns."""
    if not path:
        return False
    posix = Path(path).as_posix()
    name = PurePath(posix).name
    parts = PurePath(posix).parts
    if "tests" in parts:
        return True
    for glob in TDD_TEST_GLOBS:
        if fnmatch.fnmatch(name, glob) or fnmatch.fnmatch(posix, glob):
            return True
    return False


def is_tdd_production_path(path: str, workspace_root: Path) -> bool:
    """Return True if path is a governed production file under workspace."""
    if not path or is_tdd_test_path(path):
        return False
    candidate = Path(path).expanduser()
    try:
        resolved = candidate.resolve()
        ws = workspace_root.resolve()
        if not resolved.is_relative_to(ws):
            return False
    except (ValueError, OSError):
        return False
    if ".git" in resolved.parts:
        return False
    if resolved.name.endswith(".d.ts"):
        return False
    return resolved.suffix in {".py", ".ts", ".tsx", ".go"}


def is_scaffolding_only_text(text: str) -> bool:
    """Return True if text only contains stubs or type declarations."""
    clean = text.strip()
    if not clean:
        return True
    if re.search(r"\b(if|elif|while|for|match|case|switch)\b", clean):
        return False
    if re.search(r"\breturn\s+[^\n#]+", clean):
        return False
    try:
        tree = ast.parse(clean)
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Match)):
                return False
            if isinstance(node, ast.Return) and node.value is not None:
                return False
            if isinstance(node, ast.Assign) and isinstance(
                node.value, (ast.BinOp, ast.Call)
            ):
                return False
        return True
    except SyntaxError:
        pass
    return True


def record_tdd_prompt_authorization(
    payload: dict[str, Any], prompt: str
) -> None:
    """Record owner green authorization if prompt matches GREEN_AUTH_RE."""
    if not prompt or not GREEN_AUTH_RE.search(prompt):
        return
    state = load_state(payload)
    stage = state.get("tdd_stage", "idle")
    if stage in {"red_verified", "red_pending_verification"}:
        state["tdd_stage"] = "green_authorized"
        state["tdd_tests_passed_in_green"] = False
        state["tdd_lint_verified"] = False
        state["tdd_prod_mutated_in_green"] = False
        persist_state(payload, state)


def find_tdd_write_deny_reason(
    payload: dict[str, Any], path: str, text: str
) -> str | None:
    """Return deny reason if writing production code violates TDD stages."""
    if not path:
        return None
    workspace_root = resolve_workspace_root(payload)
    if not is_tdd_production_path(path, workspace_root):
        return None

    state = load_state(payload)
    stage = state.get("tdd_stage", "idle")
    if stage == "green_authorized":
        return None

    prompt = extract_latest_user_request(payload)
    if prompt and GREEN_AUTH_RE.search(prompt):
        record_tdd_prompt_authorization(payload, prompt)
        return None

    if stage == "red_pending_verification":
        if not is_scaffolding_only_text(text):
            return (
                "202_Test_Driven_Development.md § 202(a)(1). Red step "
                "scaffolding: writing business logic or control flow before "
                "owner green authorization is prohibited. Only stubs and "
                "type signatures are permitted."
            )
    elif stage == "red_verified":
        return (
            "202_Test_Driven_Development.md § 202(c). Gate transition: owner "
            "authorization is required before advancing into green step and "
            "modifying production code."
        )
    return None


def record_tdd_test_mutation(
    state: dict[str, Any], path: str, stage: str
) -> bool:
    """Record test file mutation and transition state to red_pending."""
    if stage != "green_authorized":
        state["tdd_stage"] = "red_pending_verification"
    mods = state.setdefault("tdd_modified_tests", [])
    if path and path not in mods:
        mods.append(path)
    state["tdd_lint_verified"] = False
    return True


def record_tdd_production_mutation(state: dict[str, Any], stage: str) -> bool:
    """Record production file mutation under green_authorized stage."""
    if stage != "green_authorized":
        return False
    state["tdd_prod_mutated_in_green"] = True
    state["tdd_tests_passed_in_green"] = False
    state["tdd_lint_verified"] = False
    return True


def record_tdd_mutation_tool(
    state: dict[str, Any], path: str, workspace_root: Path, stage: str
) -> bool:
    """Record file mutation from a mutating tool call."""
    if is_tdd_test_path(path):
        return record_tdd_test_mutation(state, path, stage)
    if is_tdd_production_path(path, workspace_root):
        return record_tdd_production_mutation(state, stage)
    return False


def record_tdd_test_runner(
    state: dict[str, Any], stage: str, has_error: bool
) -> bool:
    """Record test runner result and update stage accordingly."""
    if stage in {"red_pending_verification", "red_verified", "premature_green"}:
        state["tdd_stage"] = "red_verified" if has_error else "premature_green"
        return True
    if stage == "green_authorized" and not has_error:
        state["tdd_tests_passed_in_green"] = True
        return True
    return False


def record_tdd_linter(
    state: dict[str, Any], stage: str, has_error: bool
) -> bool:
    """Record linter execution and advance idle stage when complete."""
    if has_error:
        return False
    state["tdd_lint_verified"] = True
    if stage == "green_authorized" and state.get("tdd_tests_passed_in_green"):
        state["tdd_stage"] = "idle"
        state["tdd_modified_tests"] = []
    return True


def record_tdd_command(
    state: dict[str, Any], command: str, has_error: bool, stage: str
) -> bool:
    """Record test runner and linter commands from shell tool executions."""
    changed = False
    if TEST_RUNNER_CMD_RE.search(command):
        changed = record_tdd_test_runner(state, stage, has_error) or changed
    if LINTER_CMD_RE.search(command):
        changed = record_tdd_linter(state, stage, has_error) or changed
    return changed


def record_tdd_post_tool(
    payload: dict[str, Any], tool: str, path: str, command: str
) -> None:
    """Record test modifications, test runner executions, and linter runs."""
    state = load_state(payload)
    stage = state.get("tdd_stage", "idle")
    changed = False

    if tool in MUTATING_TOOLS:
        workspace_root = resolve_workspace_root(payload)
        changed = (
            record_tdd_mutation_tool(state, path, workspace_root, stage)
            or changed
        )

    is_cmd_tool = tool in {"runcommand", "runterminalcommand", "bash"}
    if (is_cmd_tool or command) and command:
        has_error = bool(payload.get("error"))
        changed = (
            record_tdd_command(state, command, has_error, stage) or changed
        )

    if changed:
        persist_state(payload, state)


def is_git_dirty_path(path: str, workspace_root: Path) -> bool:
    """Return True if path holds uncommitted or untracked changes in git."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--", path],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if proc.returncode != 0:
            return True
        return bool(proc.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return True


def find_green_authorized_block_reason(
    state: dict[str, Any],
) -> str | None:
    """Return deny reason if green stage mutations lack test or lint proof."""
    mutated = state.get("tdd_prod_mutated_in_green")
    passed = state.get("tdd_tests_passed_in_green")
    linted = state.get("tdd_lint_verified")
    if mutated and not passed:
        return (
            "202_Test_Driven_Development.md § 202(e). Post-authorization "
            "verification: automated tests covering green implementation "
            "must be executed and pass."
        )
    if mutated and not linted:
        return (
            "202_Test_Driven_Development.md § 202(e). Post-authorization "
            "verification: applicable linters must pass on green changes."
        )
    return None


def find_tdd_stop_block_reason(payload: dict[str, Any]) -> str | None:
    """Return stop reason when turn concludes without meeting TDD checks."""
    state = load_state(payload)
    stage = state.get("tdd_stage", "idle")
    workspace_root = resolve_workspace_root(payload)

    if stage in {"red_pending_verification", "premature_green", "red_verified"}:
        mods = state.get("tdd_modified_tests", [])
        if mods and not any(is_git_dirty_path(p, workspace_root) for p in mods):
            state["tdd_stage"] = "idle"
            state["tdd_modified_tests"] = []
            persist_state(payload, state)
            return None

    if stage == "red_pending_verification":
        return (
            "202_Test_Driven_Development.md § 202(b)(1). Modified tests must "
            "be executed to verify a Valid Red Result prior to ending turn."
        )
    if stage == "premature_green":
        return (
            "202_Test_Driven_Development.md § 202(b)(4). Premature green "
            "execution detected: tests completed without assertion failure. "
            "New tests must verify absent functionality."
        )
    if stage == "red_verified" and not state.get("tdd_lint_verified"):
        return (
            "202_Test_Driven_Development.md § 202(d). Pre-presentation lint: "
            "all applicable linters must pass on modified tests before "
            "presentation."
        )
    if stage == "green_authorized":
        return find_green_authorized_block_reason(state)
    return None
