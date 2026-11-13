"""Test-Driven Development (TDD) gate and state machine enforcement (§ 202)."""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import os
import re
import subprocess
from pathlib import Path
from pathlib import PurePath
from typing import Any

from engineering_principles.config import COMPOSITE_VERIFY_CMD_RE
from engineering_principles.config import GREEN_AUTH_RE
from engineering_principles.config import GREEN_NEGATION_RE
from engineering_principles.config import GREEN_QUESTION_RE
from engineering_principles.config import LINTER_CMD_RE
from engineering_principles.config import MUTATING_TOOLS
from engineering_principles.config import QUOTED_SPAN_RE
from engineering_principles.config import TDD_TEST_GLOBS
from engineering_principles.config import TEST_RUNNER_CMD_RE
from engineering_principles.payload import extract_command
from engineering_principles.payload import extract_tool_input
from engineering_principles.payload import load_command_execution_outcome
from engineering_principles.payload import load_latest_user_request_record
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
    try:
        tree = ast.parse(clean)
        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.If,
                    ast.IfExp,
                    ast.For,
                    ast.AsyncFor,
                    ast.While,
                    ast.Match,
                ),
            ):
                return False
            if isinstance(node, ast.Return) and node.value is not None:
                return False
            if isinstance(node, ast.Assign) and isinstance(
                node.value, (ast.BinOp, ast.Call)
            ):
                return False
        return True
    except SyntaxError:
        if re.search(r"\b(if|elif|while|for|match|case|switch)\b", clean):
            return False
        if re.search(r"\breturn\s+[^\n#]+", clean):
            return False
    return True


def is_affirmative_green_authorization(prompt: str) -> bool:
    """Return True if prompt affirms green transition outside quotes."""
    if not prompt or not prompt.strip():
        return False
    unquoted = QUOTED_SPAN_RE.sub(" ", prompt)
    clauses = re.split(r"(?<=[？?。\n!！;；,，])\s*", unquoted)
    for clause in clauses:
        text = clause.strip()
        if not text or not GREEN_AUTH_RE.search(text):
            continue
        if GREEN_NEGATION_RE.search(text) or GREEN_QUESTION_RE.search(text):
            continue
        return True
    return False


def _compute_auth_key(prompt: str, turn_key: str) -> str:
    """Compute a stable deduplication key for one owner authorization."""
    if turn_key:
        return turn_key
    digest = hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()[:16]
    return f"raw:{digest}"


def record_tdd_prompt_authorization(
    payload: dict[str, Any], prompt: str, *, turn_key: str = ""
) -> bool:
    """Record owner green authorization when affirmative and unconsumed."""
    if not is_affirmative_green_authorization(prompt):
        return False
    state = load_state(payload)
    stage = state.get("tdd_stage", "idle")
    if stage not in {
        "red_verified",
        "red_pending_verification",
        "premature_green",
    }:
        return False
    auth_key = _compute_auth_key(prompt, turn_key)
    consumed = [str(item) for item in state.get("tdd_consumed_auth_keys", [])]
    if auth_key in consumed:
        return False
    state["tdd_stage"] = "green_authorized"
    state["tdd_tests_passed_in_green"] = False
    state["tdd_lint_verified"] = False
    state["tdd_prod_mutated_in_green"] = False
    consumed.append(auth_key)
    state["tdd_consumed_auth_keys"] = consumed[-20:]
    persist_state(payload, state)
    return True


def find_tdd_write_deny_reason(
    payload: dict[str, Any], path: str, text: str
) -> str | None:
    """Return deny reason if writing production code violates TDD stages."""
    if not path:
        return None
    workspace_root = resolve_workspace_root(payload)
    if not is_tdd_production_path(path, workspace_root):
        return None

    reconcile_tdd_pending_commands(payload)
    state = load_state(payload)
    stage = state.get("tdd_stage", "idle")
    if stage == "green_authorized":
        return None

    prompt, turn_key = load_latest_user_request_record(payload)
    if prompt and record_tdd_prompt_authorization(
        payload, prompt, turn_key=turn_key
    ):
        return None

    if stage in {"red_pending_verification", "premature_green"}:
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


def _reconcile_green_completion(state: dict[str, Any]) -> None:
    """Transition green_authorized stage to idle when all checks pass."""
    if (
        state.get("tdd_prod_mutated_in_green")
        and state.get("tdd_tests_passed_in_green")
        and state.get("tdd_lint_verified")
    ):
        state["tdd_stage"] = "idle"
        state["tdd_modified_tests"] = []


def record_tdd_test_runner(
    state: dict[str, Any], stage: str, has_error: bool
) -> bool:
    """Record test runner result and update stage accordingly."""
    if stage in {"red_pending_verification", "red_verified", "premature_green"}:
        state["tdd_stage"] = "red_verified" if has_error else "premature_green"
        return True
    if stage == "green_authorized":
        state["tdd_tests_passed_in_green"] = not has_error
        if not has_error:
            _reconcile_green_completion(state)
        return True
    return False


def record_tdd_linter(
    state: dict[str, Any], stage: str, has_error: bool
) -> bool:
    """Record linter execution and advance idle stage when complete."""
    state["tdd_lint_verified"] = not has_error
    if not has_error and stage == "green_authorized":
        _reconcile_green_completion(state)
    return True


def parse_shell_command_segments(command: str) -> list[str]:
    """Split a compound shell command into individual trimmed segments."""
    if not command:
        return []
    parts = re.split(r"\s*(?:&&|\|\||;)\s*", command)
    return [part.strip() for part in parts if part.strip()]


def _inspect_failure_component(output_text: str) -> str:
    """Classify compound command failure into lint, test, or both."""
    if not output_text:
        return "both"
    has_test_fail = bool(
        re.search(
            r"\b\d+\s+failed\b|===+\s*FAILURES\s*===+|"
            r"AssertionError|ERROR\s+collecting",
            output_text,
        )
    )
    has_lint_fail = bool(
        re.search(
            r"Found \d+ error|\b[EWFD]\d{3,4}\s|"
            r"\b\d+\s+files?\s+would be reformatted|would reformat",
            output_text,
        )
    )
    if has_lint_fail and not has_test_fail:
        return "lint_failed"
    if has_test_fail:
        return "test_failed"
    return "both"


def record_tdd_command(
    state: dict[str, Any],
    command: str,
    has_error: bool,
    stage: str,
    *,
    output_text: str = "",
) -> bool:
    """Record test runner and linter commands from shell tool executions."""
    segments = parse_shell_command_segments(command)
    has_composite = any(COMPOSITE_VERIFY_CMD_RE.search(s) for s in segments)
    has_test = has_composite or any(
        TEST_RUNNER_CMD_RE.search(s) for s in segments
    )
    has_lint = has_composite or any(LINTER_CMD_RE.search(s) for s in segments)
    if not has_test and not has_lint:
        return False

    changed = False
    if not has_error:
        if has_test:
            changed = record_tdd_test_runner(state, stage, False) or changed
        if has_lint:
            changed = record_tdd_linter(state, stage, False) or changed
        return changed

    if has_test and has_lint:
        kind = _inspect_failure_component(output_text)
        if kind == "lint_failed":
            return record_tdd_linter(state, stage, True)
        if kind == "test_failed":
            if "All checks passed!" in output_text:
                changed = record_tdd_linter(state, stage, False) or changed
            return record_tdd_test_runner(state, stage, True) or changed
        changed = record_tdd_test_runner(state, stage, True) or changed
        return record_tdd_linter(state, stage, True) or changed

    if has_test:
        changed = record_tdd_test_runner(state, stage, True) or changed
    if has_lint:
        changed = record_tdd_linter(state, stage, True) or changed
    return changed


def _record_pending_command(
    state: dict[str, Any], payload: dict[str, Any], command: str, stage: str
) -> bool:
    """Store un-flushed TDD command metadata for post-tool reconciliation."""
    segments = parse_shell_command_segments(command)
    is_tdd_cmd = any(
        COMPOSITE_VERIFY_CMD_RE.search(s)
        or TEST_RUNNER_CMD_RE.search(s)
        or LINTER_CMD_RE.search(s)
        for s in segments
    )
    if not is_tdd_cmd:
        return False
    pending = list(state.get("tdd_pending_commands") or [])
    pending.append(
        {
            "command": command,
            "step_idx": payload.get("stepIdx"),
            "pre_stage": stage,
            "pre_tests_passed_in_green": bool(
                state.get("tdd_tests_passed_in_green")
            ),
            "pre_lint_verified": bool(state.get("tdd_lint_verified")),
        }
    )
    state["tdd_pending_commands"] = pending[-10:]
    return True


def reconcile_tdd_pending_commands(payload: dict[str, Any]) -> None:
    """Re-evaluate pending TDD commands once transcript/step outputs flush."""
    state = load_state(payload)
    pending = state.get("tdd_pending_commands")
    if not isinstance(pending, list) or not pending:
        return

    transcript_path = payload.get("transcriptPath") or payload.get(
        "transcript_path"
    )
    remaining: list[dict[str, Any]] = []
    changed = False
    for item in pending:
        if not isinstance(item, dict):
            changed = True
            continue
        cmd = str(item.get("command") or "")
        step_idx = item.get("step_idx")
        if (
            not cmd
            or isinstance(step_idx, bool)
            or not isinstance(step_idx, int)
        ):
            changed = True
            continue
        probe = {
            "transcriptPath": transcript_path,
            "stepIdx": step_idx,
            "toolInput": {"CommandLine": cmd},
        }
        outcome, output_text = load_command_execution_outcome(probe)
        if outcome is None:
            remaining.append(item)
            continue
        changed = True
        if not outcome:
            continue
        pre_stage = str(
            item.get("pre_stage") or state.get("tdd_stage") or "idle"
        )
        if pre_stage in {
            "red_pending_verification",
            "red_verified",
            "premature_green",
        }:
            eval_stage = pre_stage
        elif pre_stage == "green_authorized" and state.get(
            "tdd_prod_mutated_in_green"
        ):
            state["tdd_stage"] = "green_authorized"
            state["tdd_tests_passed_in_green"] = bool(
                item.get("pre_tests_passed_in_green")
            )
            state["tdd_lint_verified"] = bool(item.get("pre_lint_verified"))
            eval_stage = "green_authorized"
        else:
            eval_stage = str(state.get("tdd_stage") or "idle")
        record_tdd_command(
            state, cmd, True, eval_stage, output_text=output_text
        )

    if changed:
        state["tdd_pending_commands"] = remaining[-10:]
        persist_state(payload, state)


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
        payload_cmd = extract_command(extract_tool_input(payload))
        if not payload_cmd or payload_cmd == command:
            outcome, output_text = load_command_execution_outcome(payload)
            has_error = (
                outcome if outcome is not None else bool(payload.get("error"))
            )
            if (
                outcome is None
                and not has_error
                and (
                    payload.get("transcriptPath")
                    or payload.get("transcript_path")
                )
            ):
                changed = (
                    _record_pending_command(state, payload, command, stage)
                    or changed
                )
        else:
            has_error = bool(payload.get("error"))
            output_text = ""
        changed = (
            record_tdd_command(
                state, command, has_error, stage, output_text=output_text
            )
            or changed
        )

    if changed:
        persist_state(payload, state)


def resolve_git_repo_root(path: str, workspace_root: Path) -> Path | None:
    """Find the enclosing git repository root for target path or workspace."""
    candidates: list[Path] = []
    if path:
        raw = Path(path).expanduser()
        target = raw if raw.is_absolute() else workspace_root / raw
        base = Path(os.path.abspath(target))
        candidates.append(base if base.is_dir() else base.parent)
    candidates.append(Path(os.path.abspath(workspace_root)))

    for start in candidates:
        for ancestor in (start, *start.parents):
            if (ancestor / ".git").exists():
                return ancestor
    return None


def is_git_dirty_path(path: str, workspace_root: Path) -> bool:
    """Return True if path holds uncommitted or untracked changes in git."""
    repo_root = resolve_git_repo_root(path, workspace_root)
    if repo_root is None:
        return True
    raw = Path(path).expanduser()
    target = raw if raw.is_absolute() else workspace_root / raw
    target_arg = os.path.abspath(target)
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--", target_arg],
            cwd=repo_root,
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
    reconcile_tdd_pending_commands(payload)
    state = load_state(payload)
    stage = state.get("tdd_stage", "idle")
    workspace_root = resolve_workspace_root(payload)

    if stage in {"red_pending_verification", "premature_green", "red_verified"}:
        mods = state.get("tdd_modified_tests", [])
        if mods and not any(is_git_dirty_path(p, workspace_root) for p in mods):
            state["tdd_stage"] = "idle"
            state["tdd_modified_tests"] = []
            state["tdd_pending_commands"] = []
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
