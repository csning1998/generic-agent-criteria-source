"""Regression tests for the IaC collaboration hook."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest
from engineering_principles.config import OLD_TEXT_MAX_BYTES
from engineering_principles.dispatch import intercept_pre_tool_use
from engineering_principles.dispatch import intercept_session_start
from engineering_principles.dispatch import intercept_user_prompt
from engineering_principles.evaluate import find_write_deny_reason
from engineering_principles.evaluate import record_leave
from engineering_principles.evaluate import record_read
from engineering_principles.manifest import ManifestError
from engineering_principles.manifest import find_governing_specifications
from engineering_principles.manifest import load_planning_manifest
from engineering_principles.payload import extract_command
from engineering_principles.payload import load_old_text
from engineering_principles.state import extract_session_id


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a planning tree and isolate hook state."""
    planning = tmp_path / "planning"
    planning.mkdir()
    (planning / "decisions.md").write_text("adjudication\n", encoding="utf-8")
    (planning / "architecture.md").write_text("overview\n", encoding="utf-8")
    (planning / "architecture_meta-platform.md").write_text(
        "meta-platform\n", encoding="utf-8"
    )
    monkeypatch.setenv(
        "ENGINEERING_PRINCIPLES_STATE_DIR", str(tmp_path / "state")
    )
    monkeypatch.setenv("GROK_SESSION_ID", "test-session")
    monkeypatch.setenv("GROK_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("ENGINEERING_PRINCIPLES_HOOK", raising=False)
    monkeypatch.delenv("GROK_HOOK_EVENT", raising=False)
    return tmp_path


def _payload(tmp_path: Path, session: str = "test-session") -> dict:
    return {
        "hookEventName": "PreToolUse",
        "sessionId": session,
        "workspaceRoot": str(tmp_path),
        "cwd": str(tmp_path),
    }


def _module_path(tmp_path: Path) -> str:
    return str(
        tmp_path / "meta-platform/terraform/modules/vault-provisioning/"
        "vault-credential/resources.tf"
    )


def _layer_path(tmp_path: Path) -> str:
    return str(
        tmp_path
        / "meta-platform/terraform/layers/platform-harbor-frontend/main.tf"
    )


def test_generic_module_denied_without_leave(workspace: Path) -> None:
    """Shared modules need owner leave before a write."""
    payload = _payload(workspace)
    reason = find_write_deny_reason(
        payload, _module_path(workspace), "variable x {}", ""
    )
    assert reason is not None
    assert "Generic module" in reason


def test_generic_leave_still_blocks_product_and_vault(
    workspace: Path,
) -> None:
    """Leave does not permit product names or vault.production."""
    payload = _payload(workspace)
    record_leave(payload, "leave generic module")
    module_path = _module_path(workspace)
    assert "cannot name a product" in (
        find_write_deny_reason(
            payload, module_path, 'name = "harbor-origin/frontend"\n', ""
        )
        or ""
    )
    assert "vault.production" in (
        find_write_deny_reason(
            payload, module_path, "provider = vault.production\n", ""
        )
        or ""
    )
    assert "Tautological" in (
        find_write_deny_reason(
            payload,
            module_path,
            "providers = { vault = vault }\n",
            "",
        )
        or ""
    )


def test_generic_write_needs_architecture_then_allows(
    workspace: Path,
) -> None:
    """A clean generic write still needs planning reads first."""
    payload = _payload(workspace)
    record_leave(payload, "leave generic module")
    module_path = _module_path(workspace)
    body = 'resource "vault_kv_secret_v2" "this" {}\n'
    assert "Architecture gate" in (
        find_write_deny_reason(payload, module_path, body, "") or ""
    )
    planning = workspace / "planning"
    record_read(payload, str(planning / "decisions.md"))
    record_read(payload, str(planning / "architecture.md"))
    assert find_write_deny_reason(payload, module_path, body, "") is None


def test_consumer_secret_and_mint_layer(workspace: Path) -> None:
    """Consumer layers cannot mint. Mint layers may call vault-credential."""
    payload = _payload(workspace)
    planning = workspace / "planning"
    record_read(payload, str(planning / "decisions.md"))
    record_read(payload, str(planning / "architecture.md"))
    layer_path = _layer_path(workspace)
    mint_path = str(
        workspace
        / "meta-platform/terraform/layers/foundation-vault-bastion/main.tf"
    )
    assert "Secret ownership" in (
        find_write_deny_reason(
            payload, layer_path, 'resource "random_password" "db" {}\n', ""
        )
        or ""
    )
    assert "Secret ownership" in (
        find_write_deny_reason(
            payload,
            layer_path,
            'source = "../../modules/vault-provisioning/vault-credential"\n',
            "",
        )
        or ""
    )
    assert (
        find_write_deny_reason(
            payload,
            mint_path,
            'source = "../../modules/vault-provisioning/vault-credential"\n',
            "",
        )
        is None
    )


def test_guest_debug_and_readonly_commands(workspace: Path) -> None:
    """Read-only guest psql is allowed. Mutating SQL needs leave."""
    payload = _payload(workspace)
    sql = "ssh harbor psql -c 'ALTER USER postgres PASSWORD foo'"
    assert "Section 3 Item A.5" in (
        find_write_deny_reason(payload, "", "", sql) or ""
    )
    assert (
        find_write_deny_reason(payload, "", "", "rg -n psql ansible/roles")
        is None
    )
    assert (
        find_write_deny_reason(
            payload, "", "", "git commit -m 'document ALTER USER flow'"
        )
        is None
    )
    assert (
        find_write_deny_reason(payload, "", "", "ssh dbhost psql -c 'select 1'")
        is None
    )
    assert "Section 3 Item A.5" in (
        find_write_deny_reason(
            payload, "", "", "psql -c 'ALTER USER postgres PASSWORD foo'"
        )
        or ""
    )
    record_leave(payload, "allow guest sql")
    assert find_write_deny_reason(payload, "", "", sql) is None


def test_legacy_harbor_origin_name_gate(workspace: Path) -> None:
    """New bootstrapper paths are denied. harbor-origin trees stay."""
    payload = _payload(workspace)
    planning = workspace / "planning"
    record_read(payload, str(planning / "decisions.md"))
    record_read(payload, str(planning / "architecture.md"))
    origin_layer = (
        workspace
        / "meta-platform/terraform/layers/platform-harbor-origin-frontend"
    )
    origin_layer.mkdir(parents=True)
    new_bootstrapper = str(
        workspace
        / "meta-platform/terraform/layers/new-harbor-bootstrapper/main.tf"
    )
    new_origin = str(
        workspace / "meta-platform/terraform/layers/new-harbor-origin/main.tf"
    )
    assert "Name gate" in (
        find_write_deny_reason(payload, new_bootstrapper, "locals {}\n", "")
        or ""
    )
    assert (
        find_write_deny_reason(
            payload, str(origin_layer / "data.tf"), "locals {}\n", ""
        )
        is None
    )
    assert (
        find_write_deny_reason(payload, new_origin, "locals {}\n", "") is None
    )


def test_ansible_and_iac_sql(workspace: Path) -> None:
    """New Ansible shell without idempotence and IaC psql are denied."""
    payload = _payload(workspace)
    planning = workspace / "planning"
    record_read(payload, str(planning / "decisions.md"))
    record_read(payload, str(planning / "architecture.md"))
    play = (
        workspace
        / "meta-platform/ansible/roles/platform_harbor/tasks/keep.yaml"
    )
    play.parent.mkdir(parents=True, exist_ok=True)
    existing = "- name: already present\n  ansible.builtin.shell: echo hi\n"
    play.write_text(existing, encoding="utf-8")
    assert (
        find_write_deny_reason(
            payload,
            str(play),
            existing + "- name: comment only\n  debug: msg=x\n",
            "",
            before=existing,
        )
        is None
    )
    assert "Section 3 Item A.5" in (
        find_write_deny_reason(
            payload,
            str(play),
            existing + "- ansible.builtin.shell: wipe\n",
            "",
            before=existing,
        )
        or ""
    )
    assert "Section 3 Item A.5" in (
        find_write_deny_reason(
            payload,
            str(
                workspace / "meta-platform/ansible/roles/platform_harbor/tasks/"
                "C-deploy.yaml"
            ),
            "- ansible.builtin.shell: psql -c 'select 1'\n",
            "",
        )
        or ""
    )
    assert "Section 3 Item A.5" in (
        find_write_deny_reason(
            payload,
            _layer_path(workspace),
            'locals { cmd = "ssh dbhost psql -c select 1" }\n',
            "",
        )
        or ""
    )
    script = str(workspace / "meta-platform/scripts/fix-db.sh")
    assert "Section 3 Item A.5" in (
        find_write_deny_reason(
            payload,
            script,
            "psql -c 'ALTER USER postgres PASSWORD foo'\n",
            "",
        )
        or ""
    )
    assert (
        find_write_deny_reason(
            payload,
            str(workspace / "meta-platform/scripts/probe.sh"),
            "psql -c 'select 1'\n",
            "",
        )
        is None
    )


def test_uncovered_repo_and_lockfile(workspace: Path) -> None:
    """Uncovered repos, image tags, and lockfiles are allowed."""
    payload = _payload(workspace)
    planning = workspace / "planning"
    record_read(payload, str(planning / "decisions.md"))
    record_read(payload, str(planning / "architecture.md"))
    fullstack = str(workspace / "personal/app-content-matter/terraform/main.tf")
    assert find_write_deny_reason(payload, fullstack, "locals {}\n", "") is None
    assert (
        find_write_deny_reason(
            payload,
            _layer_path(workspace),
            'image = "goharbor/harbor-core:v2.13.1"\n',
            "",
        )
        is None
    )
    lock_path = str(workspace / "meta-platform/terraform/.terraform.lock.hcl")
    assert (
        find_write_deny_reason(payload, lock_path, "provider hashes\n", "")
        is None
    )


def test_architecture_gate_on_fresh_session(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new session still requires planning reads on covered layers."""
    monkeypatch.setenv("GROK_SESSION_ID", "fresh-session")
    fresh = _payload(workspace, session="fresh-session")
    assert "Architecture gate" in (
        find_write_deny_reason(fresh, _layer_path(workspace), "locals {}\n", "")
        or ""
    )
    fullstack = str(workspace / "personal/app-content-matter/terraform/main.tf")
    assert find_write_deny_reason(fresh, fullstack, "locals {}\n", "") is None


def test_dispatch_generic_deny_and_silent_hooks(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PreToolUse denies generic writes. Prompt hooks inject nothing."""
    monkeypatch.setenv("GROK_SESSION_ID", "dispatch-session")
    monkeypatch.setenv("GROK_WORKSPACE_ROOT", str(workspace))
    deny_payload = {
        "hookEventName": "PreToolUse",
        "sessionId": "dispatch-session",
        "workspaceRoot": str(workspace),
        "cwd": str(workspace),
        "toolName": "search_replace",
        "toolInput": {
            "file_path": _module_path(workspace),
            "new_string": "locals {}\n",
        },
    }
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_pre_tool_use(deny_payload)
    assert code == 2
    assert "Generic module" in buf.getvalue()

    prompt_payload = {
        "hookEventName": "UserPromptSubmit",
        "sessionId": "dispatch-session",
        "workspaceRoot": str(workspace),
        "cwd": str(workspace),
        "prompt": "Handle the terraform layer secret lifecycle",
    }
    buf = StringIO()
    with redirect_stdout(buf):
        code = intercept_user_prompt(prompt_payload)
    assert code == 0
    assert buf.getvalue().strip() == ""
    buf = StringIO()
    with redirect_stdout(buf):
        intercept_user_prompt(
            {**prompt_payload, "prompt": "How is the weather today"}
        )
    assert buf.getvalue().strip() == ""

    start_payload = {
        "hookEventName": "SessionStart",
        "sessionId": "dispatch-session",
        "workspaceRoot": str(workspace),
        "cwd": str(workspace),
    }
    buf = StringIO()
    with redirect_stdout(buf):
        intercept_session_start(start_payload)
    assert buf.getvalue().strip() == ""


def test_scoped_leave_and_local_exec(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Named leave does not cover another module. local-exec is denied."""
    monkeypatch.setenv("GROK_SESSION_ID", "scope-session")
    payload = _payload(workspace, session="scope-session")
    record_leave(payload, "leave generic module vault-credential")
    planning = workspace / "planning"
    record_read(payload, str(planning / "decisions.md"))
    record_read(payload, str(planning / "architecture.md"))
    other = str(
        workspace
        / "meta-platform/terraform/modules/kvm-foundation-resources/main.tf"
    )
    assert "Section 3 Item A.2" in (
        find_write_deny_reason(payload, other, "locals {}\n", "") or ""
    )
    assert "Section 3 Item A.5" in (
        find_write_deny_reason(
            payload,
            _layer_path(workspace),
            'provisioner "local-exec" { command = "true" }\n',
            "",
        )
        or ""
    )


def test_load_old_text_cap_and_extract_command_alias(workspace: Path) -> None:
    """Oversized files yield empty old text. cmd is a command alias."""
    huge = workspace / "huge-old.txt"
    huge.write_bytes(b"x" * (OLD_TEXT_MAX_BYTES + 1))
    assert load_old_text({}, str(huge)) == ""
    assert "psql" in extract_command({"cmd": "ssh harbor psql -c 'select 1'"})


_MANIFEST = """\
version = 1
adjudication = "decisions.md"

[[specifications]]
path = "architecture/example-platform.md"
governs = ["lab/example-platform"]

[[specifications]]
path = "architecture/example-consumer.md"
governs = ["lab/example-consumer"]
"""


@pytest.fixture
def manifest_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a planning tree that declares its layout in a manifest."""
    planning = tmp_path / "notes"
    (planning / "architecture").mkdir(parents=True)
    (planning / "decisions.md").write_text("adjudication\n", encoding="utf-8")
    for name in ("example-platform", "example-consumer"):
        (planning / "architecture" / f"{name}.md").write_text(
            f"{name}\n", encoding="utf-8"
        )
    (planning / "planning.manifest.toml").write_text(
        _MANIFEST, encoding="utf-8"
    )
    monkeypatch.setenv(
        "ENGINEERING_PRINCIPLES_STATE_DIR", str(tmp_path / "state")
    )
    monkeypatch.setenv("GROK_SESSION_ID", "manifest-session")
    monkeypatch.setenv("GROK_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("ENGINEERING_PRINCIPLES_HOOK", raising=False)
    monkeypatch.delenv("GROK_HOOK_EVENT", raising=False)
    return tmp_path


def _manifest_layer(tmp_path: Path, repo: str) -> str:
    return str(tmp_path / f"lab/{repo}/terraform/layers/example-layer/main.tf")


def test_manifest_gate_requires_governing_specification(
    manifest_workspace: Path,
) -> None:
    """A governed path needs the adjudication and its own specification."""
    payload = _payload(manifest_workspace, session="manifest-session")
    planning = manifest_workspace / "notes"
    layer = _manifest_layer(manifest_workspace, "example-platform")
    reason = find_write_deny_reason(payload, layer, "locals {}\n", "")
    assert "Architecture gate" in (reason or "")
    assert "architecture/example-platform.md" in (reason or "")
    record_read(payload, str(planning / "decisions.md"))
    record_read(payload, str(planning / "architecture/example-consumer.md"))
    assert "Architecture gate" in (
        find_write_deny_reason(payload, layer, "locals {}\n", "") or ""
    )
    record_read(payload, str(planning / "architecture/example-platform.md"))
    assert find_write_deny_reason(payload, layer, "locals {}\n", "") is None


def test_manifest_gate_matches_path_prefix_not_substring(
    manifest_workspace: Path,
) -> None:
    """A sibling whose name extends a governed repo name is not governed."""
    payload = _payload(manifest_workspace, session="manifest-session")
    sibling = _manifest_layer(manifest_workspace, "example-platform-extra")
    assert find_write_deny_reason(payload, sibling, "locals {}\n", "") is None


def test_manifest_gate_exempts_undeclared_repository(
    manifest_workspace: Path,
) -> None:
    """A repository without a specification is outside the gate."""
    payload = _payload(manifest_workspace, session="manifest-session")
    other = _manifest_layer(manifest_workspace, "example-unlisted")
    assert find_write_deny_reason(payload, other, "locals {}\n", "") is None


def test_manifest_gate_on_planning_tree(manifest_workspace: Path) -> None:
    """Planning edits need the adjudication and any one specification."""
    payload = _payload(manifest_workspace, session="manifest-session")
    planning = manifest_workspace / "notes"
    target = str(planning / "architecture/example-consumer.md")
    assert "Architecture gate" in (
        find_write_deny_reason(payload, target, "text\n", "") or ""
    )
    record_read(payload, str(planning / "decisions.md"))
    record_read(payload, str(planning / "architecture/example-platform.md"))
    assert find_write_deny_reason(payload, target, "text\n", "") is None


def test_manifest_gate_covers_shell_write(manifest_workspace: Path) -> None:
    """A shell write naming a governed repository needs the same reads."""
    payload = _payload(manifest_workspace, session="manifest-session")
    command = "sed -i s/a/b/ lab/example-consumer/terraform/layers/x/main.tf"
    reason = find_write_deny_reason(payload, "", "", command)
    assert "architecture/example-consumer.md" in (reason or "")


def test_invalid_manifest_fails_closed(manifest_workspace: Path) -> None:
    """A manifest that names a missing specification denies governed writes."""
    payload = _payload(manifest_workspace, session="manifest-session")
    planning = manifest_workspace / "notes"
    (planning / "architecture/example-platform.md").unlink()
    layer = _manifest_layer(manifest_workspace, "example-platform")
    reason = find_write_deny_reason(payload, layer, "locals {}\n", "")
    assert "planning manifest" in (reason or "")


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        ('governed_dirs = "terraform"\n', "governed_dirs"),
        ("governed_dirs = 5\n", "governed_dirs"),
        ("governed_dirs = []\n", "governed_dirs"),
        ('governed_dirs = ["terraform", ""]\n', "governed_dirs"),
    ],
)
def test_manifest_rejects_malformed_governed_dirs(
    manifest_workspace: Path, extra: str, message: str
) -> None:
    """A malformed governed_dirs value is a manifest error, not a crash."""
    manifest = manifest_workspace / "notes" / "planning.manifest.toml"
    body = manifest.read_text(encoding="utf-8")
    head, rest = body.split("\n", 1)
    manifest.write_text(f"{head}\n{extra}{rest}", encoding="utf-8")
    with pytest.raises(ManifestError, match=message):
        load_planning_manifest(manifest)
    payload = _payload(manifest_workspace, session="manifest-session")
    layer = _manifest_layer(manifest_workspace, "example-platform")
    reason = find_write_deny_reason(payload, layer, "locals {}\n", "")
    assert "planning manifest" in (reason or "")


def test_manifest_rejects_specification_entry_that_is_not_a_table(
    manifest_workspace: Path,
) -> None:
    """A scalar entry in specifications is a manifest error, not a crash."""
    manifest = manifest_workspace / "notes" / "planning.manifest.toml"
    manifest.write_text(
        'version = 1\nadjudication = "decisions.md"\nspecifications = ["a"]\n',
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match=r"specifications\[0\]"):
        load_planning_manifest(manifest)
    payload = _payload(manifest_workspace, session="manifest-session")
    layer = _manifest_layer(manifest_workspace, "example-platform")
    reason = find_write_deny_reason(payload, layer, "locals {}\n", "")
    assert "planning manifest" in (reason or "")


def test_manifest_governed_dir_ignores_workspace_ancestors(
    tmp_path: Path,
) -> None:
    """A governed name above the workspace does not govern the whole tree."""
    workspace = tmp_path / "packer" / "workspace"
    planning = workspace / "notes"
    planning.mkdir(parents=True)
    (planning / "decisions.md").write_text("adjudication\n", encoding="utf-8")
    (planning / "spec.md").write_text("spec\n", encoding="utf-8")
    (planning / "planning.manifest.toml").write_text(
        'version = 1\nadjudication = "decisions.md"\n\n'
        '[[specifications]]\npath = "spec.md"\ngoverns = ["lab/example"]\n',
        encoding="utf-8",
    )
    manifest = load_planning_manifest(planning / "planning.manifest.toml")
    docs = workspace / "lab/example/docs/README.md"
    layer = workspace / "lab/example/terraform/main.tf"
    assert find_governing_specifications(manifest, str(docs)) is None
    assert find_governing_specifications(manifest, str(layer)) is not None


def test_missing_session_does_not_leak_leave(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ephemeral sessions do not share leave state."""
    monkeypatch.delenv("GROK_SESSION_ID", raising=False)
    bare = {"workspaceRoot": str(workspace), "cwd": str(workspace)}
    first_id = extract_session_id(bare)
    second_id = extract_session_id(bare)
    assert first_id != second_id
    assert first_id != "unknown"
    assert second_id != "unknown"
    leave_payload = {
        "hookEventName": "UserPromptSubmit",
        "workspaceRoot": str(workspace),
        "cwd": str(workspace),
    }
    record_leave(leave_payload, "leave generic module")
    other_payload = {
        "hookEventName": "PreToolUse",
        "workspaceRoot": str(workspace),
        "cwd": str(workspace),
    }
    assert "Generic module" in (
        find_write_deny_reason(
            other_payload, _module_path(workspace), "variable x {}", ""
        )
        or ""
    )
