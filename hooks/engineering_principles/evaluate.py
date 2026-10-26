"""Write-gate evaluation for governed IaC and planning mutations."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from engineering_principles.config import ALLOW_FULL_OVERWRITE_RE
from engineering_principles.config import ANSIBLE_IDEMPOTENT_RE
from engineering_principles.config import ANSIBLE_SHELL_RE
from engineering_principles.config import ENV_ALIAS_RE
from engineering_principles.config import GENERIC_MODULE_NAME_RE
from engineering_principles.config import GENERIC_MODULE_RE
from engineering_principles.config import GUEST_SQL_CMD_RE
from engineering_principles.config import HARDCODED_VAULT_PRODUCTION_RE
from engineering_principles.config import IAC_SQL_RE
from engineering_principles.config import LEAVE_GENERIC_RE
from engineering_principles.config import LEAVE_GUEST_SQL_RE
from engineering_principles.config import MUTATING_SQL_RE
from engineering_principles.config import PRODUCT_TOKEN_RE
from engineering_principles.config import PROVISIONER_RE
from engineering_principles.config import RANDOM_PASSWORD_RE
from engineering_principles.config import READ_ONLY_CMD_RE
from engineering_principles.config import TAUTOLOGICAL_PROVIDER_RE
from engineering_principles.config import VAULT_CREDENTIAL_MODULE_RE
from engineering_principles.config import WRITE_CMD_RE
from engineering_principles.manifest import ManifestError
from engineering_principles.manifest import PlanningManifest
from engineering_principles.manifest import find_governing_specifications
from engineering_principles.manifest import find_planning_manifest
from engineering_principles.manifest import find_specifications_in_command
from engineering_principles.manifest import load_planning_manifest
from engineering_principles.paths import find_planning_root
from engineering_principles.paths import is_ansible_path
from engineering_principles.paths import is_consumer_layer
from engineering_principles.paths import is_generic_module
from engineering_principles.paths import is_governed_path
from engineering_principles.paths import is_iac_path
from engineering_principles.paths import is_introduced_bootstrapper_name
from engineering_principles.paths import is_planning_gate_required
from engineering_principles.paths import is_self_path
from engineering_principles.paths import load_architecture_repo_tokens
from engineering_principles.paths import normalize_posix
from engineering_principles.payload import extract_latest_user_request
from engineering_principles.payload import extract_tool_input
from engineering_principles.payload import normalize_tool
from engineering_principles.state import load_state
from engineering_principles.state import persist_state
from engineering_principles.state import resolve_workspace_root


def has_added_match(before: str, after: str, pattern: re.Pattern[str]) -> bool:
    """Return True when after introduces a new pattern hit."""
    if not after or not pattern.search(after):
        return False
    before_hits = len(pattern.findall(before)) if before else 0
    after_hits = len(pattern.findall(after))
    return after_hits > before_hits


def compute_file_sha256(path: Path) -> str:
    """Return the SHA-256 digest of the on-disk file bytes."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def record_read(payload: dict[str, Any], path: str) -> dict[str, Any]:
    """Record that the session opened a path with the read tool."""
    state = load_state(payload)
    resolved = str(Path(path).expanduser())
    reads = [str(item) for item in state.get("read_paths", [])]
    if resolved not in reads:
        reads.append(resolved)
    state["read_paths"] = reads

    tool_input_data = extract_tool_input(payload)
    is_partial = bool(
        tool_input_data.get("StartLine")
        or tool_input_data.get("EndLine")
        or tool_input_data.get("ContentOffset")
    )
    candidate = Path(path).expanduser()
    if not is_partial and candidate.is_file():
        read_hashes = state.setdefault("read_hashes", {})
        digest = compute_file_sha256(candidate.resolve())
        if digest:
            read_hashes[str(candidate.resolve())] = digest

    persist_state(payload, state)
    return state


def record_mutation(payload: dict[str, Any], path: str) -> None:
    """Update recorded on-disk content hash after a successful tool mutation."""
    if not path:
        return
    candidate = Path(path).expanduser()
    if not candidate.is_file():
        return
    state = load_state(payload)
    read_hashes = state.setdefault("read_hashes", {})
    digest = compute_file_sha256(candidate.resolve())
    if digest:
        read_hashes[str(candidate.resolve())] = digest
    persist_state(payload, state)


def record_leave(payload: dict[str, Any], prompt: str) -> dict[str, Any]:
    """Record owner leave phrases from the current prompt."""
    state = load_state(payload)
    changed = False
    if prompt and prompt != state.get("last_prompt"):
        state["last_prompt"] = prompt
        changed = True
    if LEAVE_GENERIC_RE.search(prompt):
        state["generic_leave"] = True
        named = [
            item.group(0) for item in GENERIC_MODULE_NAME_RE.finditer(prompt)
        ]
        if named:
            existing = [
                str(item) for item in state.get("generic_leave_modules", [])
            ]
            for item in named:
                if item not in existing:
                    existing.append(item)
            state["generic_leave_modules"] = existing
        changed = True
    if LEAVE_GUEST_SQL_RE.search(prompt):
        state["guest_sql_leave"] = True
        changed = True
    if changed:
        persist_state(payload, state)
    return state


def has_generic_leave_cover(state: dict[str, Any], path: str) -> bool:
    """Return True when session leave covers this generic module path."""
    if not state.get("generic_leave"):
        return False
    modules = [str(item) for item in state.get("generic_leave_modules", [])]
    if not modules:
        return True
    posix_path = normalize_posix(path)
    return any(fragment in posix_path for fragment in modules)


def has_env_alias_in_generic(text: str) -> bool:
    """Return True when an environment alias is hardcoded in the text."""
    for line in text.splitlines():
        if not ENV_ALIAS_RE.search(line):
            continue
        if re.search(r"(forbid|MUST NOT|do not)", line, re.I):
            continue
        if line.lstrip().startswith("#"):
            continue
        return True
    return False


def render_cite(
    rule: str,
    text: str,
    pattern: re.Pattern[str] | None,
    message: str,
) -> str:
    """Build a deny reason with optional matching line numbers."""
    lines: list[str] = []
    if pattern is not None and text:
        for index, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                lines.append(str(index))
    location = f" lines {', '.join(lines)}" if lines else ""
    return (
        f"99-hook-contract.md {rule}{location}. {message} "
        "Do not rewrite the content to evade this rule."
    )


def load_manifest_status(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return the planning manifest or its error, or None without one."""
    starts = [resolve_workspace_root(payload)]
    if payload.get("cwd"):
        starts.append(Path(str(payload["cwd"])))
    for start in starts:
        try:
            found = find_planning_manifest(start)
            if found is not None:
                return {"manifest": load_planning_manifest(found)}
        except ManifestError as error:
            return {"manifest_error": str(error)}
    return None


def _resolve_read_set(state: dict[str, Any]) -> set[str]:
    reads: set[str] = set()
    for item in state.get("read_paths", []):
        path = Path(str(item)).expanduser()
        reads.add(str(path))
        try:
            reads.add(str(path.resolve()))
        except OSError:
            continue
    return reads


def _is_read(path: Path, reads: set[str]) -> bool:
    try:
        return str(path) in reads or str(path.resolve()) in reads
    except OSError:
        return str(path) in reads


def find_missing_manifest_reason(
    target: str,
    status: dict[str, Any],
    state: dict[str, Any],
    is_command: bool,
) -> str | None:
    """Return a deny reason when manifest-required reads are missing."""
    if "manifest_error" in status:
        if not is_governed_path(target):
            return None
        return render_cite(
            "Section 3 Item A.1",
            "",
            None,
            "The planning manifest is invalid, so the architecture gate "
            f"cannot resolve the required reads: {status['manifest_error']}. "
            "Fix the manifest before mutating this tree.",
        )
    manifest: PlanningManifest = status["manifest"]
    specs = (
        find_specifications_in_command(manifest, target)
        if is_command
        else find_governing_specifications(manifest, target)
    )
    if specs is None:
        return None
    reads = _resolve_read_set(state)
    missing: list[str] = []
    if not _is_read(manifest.adjudication, reads):
        missing.append(str(manifest.adjudication))
    if specs:
        missing += [str(s.path) for s in specs if not _is_read(s.path, reads)]
    elif not any(_is_read(s.path, reads) for s in manifest.specifications):
        shown = [str(s.path) for s in manifest.specifications[:4]]
        missing.append("at least one of: " + ", ".join(shown))
    if not missing:
        return None
    return render_cite(
        "Section 3 Item A.1",
        "",
        None,
        "Architecture gate: read these files with read_file before mutating "
        "this covered tree: "
        + "; ".join(missing)
        + ". Then state move, name, DAG, and whether this edit is in scope.",
    )


def inspect_planning_status(
    payload: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """Return whether required planning files have been opened."""
    planning = find_planning_root(resolve_workspace_root(payload))
    if planning is None:
        cwd = payload.get("cwd")
        if cwd:
            planning = find_planning_root(Path(str(cwd)))
    if planning is None:
        return {
            "planning_root": None,
            "decisions_required": False,
            "architecture_required": False,
            "decisions_read": True,
            "architecture_read": True,
        }
    decisions = planning / "decisions.md"
    architecture_files = sorted(planning.glob("architecture*.md"))
    reads = {
        str(Path(item).expanduser()) for item in state.get("read_paths", [])
    }
    decisions_read = (not decisions.is_file()) or str(decisions) in reads
    architecture_read = (not architecture_files) or any(
        str(item) in reads for item in architecture_files
    )
    return {
        "planning_root": str(planning),
        "decisions_required": decisions.is_file(),
        "architecture_required": bool(architecture_files),
        "decisions_read": decisions_read,
        "architecture_read": architecture_read,
        "decisions_path": str(decisions) if decisions.is_file() else None,
        "architecture_paths": [str(item) for item in architecture_files],
        "repo_tokens": load_architecture_repo_tokens(planning),
    }


def find_missing_planning_reason(
    path: str, status: dict[str, Any]
) -> str | None:
    """Return a deny reason when required planning reads are missing."""
    root = status.get("planning_root")
    if root is None:
        return None
    if not is_planning_gate_required(path, Path(str(root))):
        return None
    missing: list[str] = []
    if status["decisions_required"] and not status["decisions_read"]:
        missing.append(status["decisions_path"])
    if status["architecture_required"] and not status["architecture_read"]:
        shown = status.get("architecture_paths") or []
        missing.append(
            "at least one of: " + ", ".join(shown[:4])
            if shown
            else "planning/architecture*.md"
        )
    if not missing:
        return None
    return render_cite(
        "Section 3 Item A.1",
        "",
        None,
        "Architecture gate: read these files with read_file before mutating "
        "this covered tree: "
        + "; ".join(missing)
        + ". Then state move, name, DAG, and whether this edit is in scope.",
    )


def find_guest_sql_command_reason(
    state: dict[str, Any], command: str
) -> str | None:
    """Return a deny reason for a mutating guest SQL shell command."""
    if not command or not GUEST_SQL_CMD_RE.search(command):
        return None
    if not MUTATING_SQL_RE.search(command):
        return None
    if state.get("guest_sql_leave"):
        return None
    return render_cite(
        "Section 3 Item A.5",
        command,
        MUTATING_SQL_RE,
        "Mutating guest SQL is forbidden. Do not run ALTER USER, "
        "password reset, or other state changes to repair IaC drift. "
        "Read-only psql debug does not need leave. Owner phrase for a "
        "mutating guest command: allow guest sql.",
    )


def find_command_without_path_reason(
    payload: dict[str, Any],
    state: dict[str, Any],
    command: str,
) -> str | None:
    """Return a deny reason for a shell mutation that names no file path."""
    if WRITE_CMD_RE.search(command) and GENERIC_MODULE_RE.search(
        normalize_posix(command)
    ):
        if not has_generic_leave_cover(state, command):
            return render_cite(
                "Section 3 Item A.2",
                command,
                GENERIC_MODULE_RE,
                "A shell write targeting terraform/modules or "
                "ansible/roles/utils_* needs owner leave this session. "
                "Owner phrase: leave generic module.",
            )
    if READ_ONLY_CMD_RE.search(command):
        return None
    if not WRITE_CMD_RE.search(command):
        return None
    manifest_status = load_manifest_status(payload)
    if manifest_status is not None:
        return find_missing_manifest_reason(
            command, manifest_status, state, is_command=True
        )
    if is_governed_path(command):
        return find_missing_planning_reason(
            command, inspect_planning_status(payload, state)
        )
    return None


def find_ansible_shell_reason(path: str, text: str, before: str) -> str | None:
    """Return a deny reason for a new non-idempotent Ansible shell task."""
    if not is_ansible_path(path):
        return None
    if not has_added_match(before, text, ANSIBLE_SHELL_RE):
        return None
    if ANSIBLE_IDEMPOTENT_RE.search(text):
        return None
    return render_cite(
        "Section 3 Item A.5",
        text,
        ANSIBLE_SHELL_RE,
        "ansible.builtin.shell and command require changed_when, "
        "creates, or removes.",
    )


def _has_sql_doc_exception(text: str) -> bool:
    """Return True when the text only forbids SQL rather than invoking it."""
    return bool(re.search(r"(forbid|MUST NOT|do not).{0,40}psql", text, re.I))


def find_iac_sql_reason(path: str, text: str, before: str) -> str | None:
    """Return a deny reason for IaC that embeds psql or postgresql."""
    if not is_iac_path(path):
        return None
    if not has_added_match(before, text, IAC_SQL_RE):
        return None
    if _has_sql_doc_exception(text):
        return None
    return render_cite(
        "Section 3 Item A.5",
        text,
        IAC_SQL_RE,
        "terraform, ansible, and packer files must not invoke psql, "
        "ALTER USER, or community.postgresql to patch guest state.",
    )


def find_mutating_sql_file_reason(
    path: str, text: str, before: str
) -> str | None:
    """Return a deny reason for a non-IaC file that embeds mutating SQL."""
    if is_iac_path(path):
        return None
    if not has_added_match(before, text, MUTATING_SQL_RE):
        return None
    if _has_sql_doc_exception(text):
        return None
    return render_cite(
        "Section 3 Item A.5",
        text,
        MUTATING_SQL_RE,
        "A script, Makefile, or CI file must not invoke ALTER USER or "
        "other mutating SQL to patch declaration drift.",
    )


def find_write_deny_reason(
    payload: dict[str, Any],
    path: str,
    text: str,
    command: str,
    before: str = "",
) -> str | None:
    """Return a deny reason for a forbidden write, or None to allow."""
    state = load_state(payload)
    if path and is_self_path(path):
        return None

    reason = find_guest_sql_command_reason(state, command)
    if reason:
        return reason

    if command and not path:
        return find_command_without_path_reason(payload, state, command)

    if not path:
        return None

    if is_generic_module(path) and not has_generic_leave_cover(state, path):
        return render_cite(
            "Section 3 Item A.2",
            "",
            None,
            f"Generic module {path} is shared. Do not edit it without owner "
            "leave for this module in this session. Owner phrase: "
            "leave generic module.",
        )

    if is_generic_module(path) and has_generic_leave_cover(state, path):
        if has_added_match(before, text, HARDCODED_VAULT_PRODUCTION_RE):
            return render_cite(
                "Section 3 Item A.3",
                text,
                HARDCODED_VAULT_PRODUCTION_RE,
                "Generic module still cannot hardcode vault.production. "
                "The caller binds the Vault provider.",
            )
        if has_added_match(before, text, TAUTOLOGICAL_PROVIDER_RE):
            return render_cite(
                "Section 3 Item A.3",
                text,
                TAUTOLOGICAL_PROVIDER_RE,
                "Tautological providers map vault = vault is forbidden.",
            )
        if has_added_match(before, text, PRODUCT_TOKEN_RE):
            return render_cite(
                "Section 3 Item A.4",
                text,
                PRODUCT_TOKEN_RE,
                "Generic module still cannot name a product in variables, "
                "resources, tags, or outputs. The caller supplies those "
                "values.",
            )
        if has_env_alias_in_generic(text) and (
            not before or not has_env_alias_in_generic(before)
        ):
            return render_cite(
                "Section 3 Item A.3",
                text,
                ENV_ALIAS_RE,
                "Generic module still cannot hardcode environment aliases "
                "such as prod, stg, or dev.",
            )

    if path and is_introduced_bootstrapper_name(path):
        return (
            "99-hook-contract.md Section 3 Item A.4. Name gate: do not create "
            "a new path that still says bootstrapper. Existing leftover paths "
            "may stay until the planned rename. "
            "Do not rewrite the content to evade this rule."
        )

    if is_consumer_layer(path) and (
        has_added_match(before, text, RANDOM_PASSWORD_RE)
        or has_added_match(before, text, VAULT_CREDENTIAL_MODULE_RE)
    ):
        return render_cite(
            "Section 3 Item A.5 / ENGINEERING_PRINCIPLES Section 3",
            text,
            RANDOM_PASSWORD_RE
            if RANDOM_PASSWORD_RE.search(text)
            else VAULT_CREDENTIAL_MODULE_RE,
            "Secret ownership: random_password and vault-credential writes "
            "belong in a vault, credential, pki, identity, or approle layer. "
            "This consumer layer reads a Vault path.",
        )

    if has_added_match(before, text, TAUTOLOGICAL_PROVIDER_RE):
        return render_cite(
            "Section 3 Item A.3",
            text,
            TAUTOLOGICAL_PROVIDER_RE,
            "Tautological providers map vault = vault is forbidden.",
        )

    if has_added_match(before, text, PROVISIONER_RE):
        return render_cite(
            "Section 3 Item A.5",
            text,
            PROVISIONER_RE,
            "local-exec and remote-exec are forbidden in automation.",
        )

    reason = find_ansible_shell_reason(path, text, before)
    if reason:
        return reason
    reason = find_iac_sql_reason(path, text, before)
    if reason:
        return reason
    reason = find_mutating_sql_file_reason(path, text, before)
    if reason:
        return reason

    manifest_status = load_manifest_status(payload)
    if manifest_status is not None:
        return find_missing_manifest_reason(
            path, manifest_status, state, is_command=False
        )
    if is_governed_path(path):
        return find_missing_planning_reason(
            path, inspect_planning_status(payload, state)
        )
    return None


def is_governed_working_tree_file(
    payload: dict[str, Any], candidate: Path
) -> bool:
    """Return True if candidate is an existing file inside the workspace."""
    if not candidate.is_file():
        return False
    workspace_root = resolve_workspace_root(payload).resolve()
    try:
        resolved = candidate.resolve()
        if not resolved.is_relative_to(workspace_root):
            return False
    except (ValueError, OSError):
        return False
    if ".git" in resolved.parts:
        return False
    artifact_dir = payload.get("artifactDirectoryPath")
    if artifact_dir:
        try:
            brain_root = Path(str(artifact_dir)).expanduser().resolve()
            if resolved.is_relative_to(brain_root):
                return False
        except (ValueError, OSError):
            pass
    return True


def find_drift_gate_reason(payload: dict[str, Any], path: str) -> str | None:
    """Enforce working-tree drift and overwrite invariants (§ 201(c)(d)(e))."""
    if not path:
        return None
    candidate = Path(path).expanduser()
    if not is_governed_working_tree_file(payload, candidate):
        return None

    tool = normalize_tool(payload)
    resolved_str = str(candidate.resolve())

    if tool == "writetofile":
        latest_request = extract_latest_user_request(payload)
        if not ALLOW_FULL_OVERWRITE_RE.search(latest_request):
            return (
                "201_Execute_Act_Predicates.md § 201(d). Whole-file "
                f"replacement via write_to_file on existing working-tree "
                f"path '{path}' is prohibited. Use replace_file_content or "
                "multi_replace_file_content. To allow full overwrite, the "
                "prompt in the current turn must contain 'allow full "
                "overwrite' (§ 201(e))."
            )

    if tool in {"replacefilecontent", "multireplacefilecontent"}:
        state = load_state(payload)
        read_hashes = state.get("read_hashes", {})
        if resolved_str not in read_hashes:
            return (
                "201_Execute_Act_Predicates.md § 201(c). Read-before-write "
                f"invariant: path '{path}' must be inspected in full with a "
                "read tool (e.g. view_file) in the current session before "
                "mutation."
            )
        current_hash = compute_file_sha256(candidate.resolve())
        recorded_hash = read_hashes[resolved_str]
        if current_hash != recorded_hash:
            return (
                "201_Execute_Act_Predicates.md § 201(c). Working-tree drift "
                f"detected: current on-disk content hash of '{path}' does not "
                "match the hash recorded during inspection in this session. "
                "Re-inspect before mutation."
            )

    return None
