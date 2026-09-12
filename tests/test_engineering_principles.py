"""Regression tests for the IaC collaboration hook."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest
from engineering_principles.config import OLD_TEXT_MAX_BYTES
from engineering_principles.dispatch import handle_pre_tool_use
from engineering_principles.dispatch import handle_session_start
from engineering_principles.dispatch import handle_user_prompt
from engineering_principles.evaluate import apply_leave
from engineering_principles.evaluate import evaluate_write
from engineering_principles.evaluate import record_read
from engineering_principles.payload import command
from engineering_principles.payload import old_text
from engineering_principles.state import session_id


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
    reason = evaluate_write(
        payload, _module_path(workspace), "variable x {}", ""
    )
    assert reason is not None
    assert "Generic module" in reason


def test_generic_leave_still_blocks_product_and_vault(
    workspace: Path,
) -> None:
    """Leave does not permit product names or vault.production."""
    payload = _payload(workspace)
    apply_leave(payload, "leave generic module")
    module_path = _module_path(workspace)
    assert "cannot name a product" in (
        evaluate_write(
            payload, module_path, 'name = "harbor-origin/frontend"\n', ""
        )
        or ""
    )
    assert "vault.production" in (
        evaluate_write(
            payload, module_path, "provider = vault.production\n", ""
        )
        or ""
    )
    assert "Tautological" in (
        evaluate_write(
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
    apply_leave(payload, "leave generic module")
    module_path = _module_path(workspace)
    body = 'resource "vault_kv_secret_v2" "this" {}\n'
    assert "Architecture gate" in (
        evaluate_write(payload, module_path, body, "") or ""
    )
    planning = workspace / "planning"
    record_read(payload, str(planning / "decisions.md"))
    record_read(payload, str(planning / "architecture.md"))
    assert evaluate_write(payload, module_path, body, "") is None


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
        evaluate_write(
            payload, layer_path, 'resource "random_password" "db" {}\n', ""
        )
        or ""
    )
    assert "Secret ownership" in (
        evaluate_write(
            payload,
            layer_path,
            'source = "../../modules/vault-provisioning/vault-credential"\n',
            "",
        )
        or ""
    )
    assert (
        evaluate_write(
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
    assert "Section 3 Item A.5" in (evaluate_write(payload, "", "", sql) or "")
    assert evaluate_write(payload, "", "", "rg -n psql ansible/roles") is None
    assert (
        evaluate_write(
            payload, "", "", "git commit -m 'document ALTER USER flow'"
        )
        is None
    )
    assert (
        evaluate_write(payload, "", "", "ssh dbhost psql -c 'select 1'") is None
    )
    assert "Section 3 Item A.5" in (
        evaluate_write(
            payload, "", "", "psql -c 'ALTER USER postgres PASSWORD foo'"
        )
        or ""
    )
    apply_leave(payload, "allow guest sql")
    assert evaluate_write(payload, "", "", sql) is None


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
        evaluate_write(payload, new_bootstrapper, "locals {}\n", "") or ""
    )
    assert (
        evaluate_write(
            payload, str(origin_layer / "data.tf"), "locals {}\n", ""
        )
        is None
    )
    assert evaluate_write(payload, new_origin, "locals {}\n", "") is None


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
        evaluate_write(
            payload,
            str(play),
            existing + "- name: comment only\n  debug: msg=x\n",
            "",
            before=existing,
        )
        is None
    )
    assert "Section 3 Item A.5" in (
        evaluate_write(
            payload,
            str(play),
            existing + "- ansible.builtin.shell: wipe\n",
            "",
            before=existing,
        )
        or ""
    )
    assert "Section 3 Item A.5" in (
        evaluate_write(
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
        evaluate_write(
            payload,
            _layer_path(workspace),
            'locals { cmd = "ssh dbhost psql -c select 1" }\n',
            "",
        )
        or ""
    )
    script = str(workspace / "meta-platform/scripts/fix-db.sh")
    assert "Section 3 Item A.5" in (
        evaluate_write(
            payload,
            script,
            "psql -c 'ALTER USER postgres PASSWORD foo'\n",
            "",
        )
        or ""
    )
    assert (
        evaluate_write(
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
    assert evaluate_write(payload, fullstack, "locals {}\n", "") is None
    assert (
        evaluate_write(
            payload,
            _layer_path(workspace),
            'image = "goharbor/harbor-core:v2.13.1"\n',
            "",
        )
        is None
    )
    lock_path = str(workspace / "meta-platform/terraform/.terraform.lock.hcl")
    assert evaluate_write(payload, lock_path, "provider hashes\n", "") is None


def test_architecture_gate_on_fresh_session(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new session still requires planning reads on covered layers."""
    monkeypatch.setenv("GROK_SESSION_ID", "fresh-session")
    fresh = _payload(workspace, session="fresh-session")
    assert "Architecture gate" in (
        evaluate_write(fresh, _layer_path(workspace), "locals {}\n", "") or ""
    )
    fullstack = str(workspace / "personal/app-content-matter/terraform/main.tf")
    assert evaluate_write(fresh, fullstack, "locals {}\n", "") is None


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
        code = handle_pre_tool_use(deny_payload)
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
        code = handle_user_prompt(prompt_payload)
    assert code == 0
    assert buf.getvalue().strip() == ""
    buf = StringIO()
    with redirect_stdout(buf):
        handle_user_prompt(
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
        handle_session_start(start_payload)
    assert buf.getvalue().strip() == ""


def test_scoped_leave_and_local_exec(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Named leave does not cover another module. local-exec is denied."""
    monkeypatch.setenv("GROK_SESSION_ID", "scope-session")
    payload = _payload(workspace, session="scope-session")
    apply_leave(payload, "leave generic module vault-credential")
    planning = workspace / "planning"
    record_read(payload, str(planning / "decisions.md"))
    record_read(payload, str(planning / "architecture.md"))
    other = str(
        workspace
        / "meta-platform/terraform/modules/kvm-foundation-resources/main.tf"
    )
    assert "Section 3 Item A.2" in (
        evaluate_write(payload, other, "locals {}\n", "") or ""
    )
    assert "Section 3 Item A.5" in (
        evaluate_write(
            payload,
            _layer_path(workspace),
            'provisioner "local-exec" { command = "true" }\n',
            "",
        )
        or ""
    )


def test_old_text_cap_and_command_alias(workspace: Path) -> None:
    """Oversized files yield empty old text. cmd is a command alias."""
    huge = workspace / "huge-old.txt"
    huge.write_bytes(b"x" * (OLD_TEXT_MAX_BYTES + 1))
    assert old_text({}, str(huge)) == ""
    assert "psql" in command({"cmd": "ssh harbor psql -c 'select 1'"})


def test_missing_session_does_not_leak_leave(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ephemeral sessions do not share leave state."""
    monkeypatch.delenv("GROK_SESSION_ID", raising=False)
    bare = {"workspaceRoot": str(workspace), "cwd": str(workspace)}
    first_id = session_id(bare)
    second_id = session_id(bare)
    assert first_id != second_id
    assert first_id != "unknown"
    assert second_id != "unknown"
    leave_payload = {
        "hookEventName": "UserPromptSubmit",
        "workspaceRoot": str(workspace),
        "cwd": str(workspace),
    }
    apply_leave(leave_payload, "leave generic module")
    other_payload = {
        "hookEventName": "PreToolUse",
        "workspaceRoot": str(workspace),
        "cwd": str(workspace),
    }
    assert "Generic module" in (
        evaluate_write(
            other_payload, _module_path(workspace), "variable x {}", ""
        )
        or ""
    )
