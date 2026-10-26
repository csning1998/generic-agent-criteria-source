"""Constants and compiled patterns for the IaC collaboration hook."""

from __future__ import annotations

import re


OLD_TEXT_MAX_BYTES = 1_048_576

GENERIC_MODULE_NAME_RE = re.compile(
    r"terraform/modules/[\w./-]+|utils_[a-z0-9_]+|"
    r"vault-credential|vault-pki-setup|vault-workload-identity",
    re.I,
)
ENV_ALIAS_RE = re.compile(r"\b(prod|stg|staging|dev|development)\b", re.I)
PROVISIONER_RE = re.compile(r'provisioner\s+"(local-exec|remote-exec)"')
ANSIBLE_SHELL_RE = re.compile(r"ansible\.builtin\.(shell|command)\b")
ANSIBLE_IDEMPOTENT_RE = re.compile(r"\b(changed_when|creates|removes)\b")
GOVERNED_DIR_PARTS = ("terraform", "ansible", "packer", "planning")
GENERIC_MODULE_RE = re.compile(
    r"(?:^|/)terraform/modules(?:/|$)|(?:^|/)ansible/roles/utils_[^/]+(?:/|$)"
)
SECRET_MINT_LAYER_RE = re.compile(
    r"(?:^|/)terraform/layers/[^/]*(?:vault|credential|pki|identity|approle)[^/]*",
    re.I,
)
PRODUCT_TOKEN_RE = re.compile(
    r"\b(harbor-origin|harbor_origin|harbor-bootstrapper|"
    r"harbor_bootstrapper|keycloak|gitlab-omnibus)\b",
    re.I,
)
TAUTOLOGICAL_PROVIDER_RE = re.compile(
    r"providers\s*=\s*\{[^}]*\bvault\s*=\s*vault\b[^}]*\}",
    re.S,
)
HARDCODED_VAULT_PRODUCTION_RE = re.compile(r"\bvault\.production\b")
RANDOM_PASSWORD_RE = re.compile(r'\bresource\s+"random_password"')
VAULT_CREDENTIAL_MODULE_RE = re.compile(
    r"modules/vault-provisioning/vault-credential|"
    r'source\s*=\s*"[^"]*vault-credential"'
)
IAC_SQL_RE = re.compile(
    r"(community\.postgresql|\bpostgresql_query\b|\bpostgresql_user\b|"
    r"\bansible\.builtin\.shell\b[^\n]{0,80}\bpsql\b|\bpsql\b|"
    r"\bALTER\s+(?:USER|ROLE)\b)",
    re.I,
)
MUTATING_SQL_RE = re.compile(
    r"("
    r"\bALTER\s+(?:USER|ROLE)\b"
    r"|\bINSERT\s+INTO\b"
    r"|\bUPDATE\s+\S+\s+SET\b"
    r"|\bDELETE\s+FROM\b"
    r"|\bTRUNCATE\s+"
    r"|\bDROP\s+(?:DATABASE|TABLE|USER|ROLE|SCHEMA)\b"
    r"|\bCREATE\s+(?:USER|ROLE)\b"
    r"|\bGRANT\s+"
    r"|\bREVOKE\s+"
    r")",
    re.I,
)
GUEST_SQL_CMD_RE = re.compile(
    r"(?:"
    r"(?:^|[;&|])\s*\bpsql\b"
    r"|"
    r"\bssh\b[^\n]{0,200}\bpsql\b"
    r"|"
    r"\bdocker\s+exec\b[^\n]{0,200}\bpsql\b"
    r"|"
    r"\bpsql\b[^\n]{0,200}\bALTER\s+(?:USER|ROLE)\b"
    r"|"
    r"\bssh\b[^\n]{0,200}\bALTER\s+(?:USER|ROLE)\b"
    r"|"
    r"\bdocker\s+exec\b[^\n]{0,200}\bALTER\s+(?:USER|ROLE)\b"
    r")",
    re.I,
)
READ_ONLY_CMD_RE = re.compile(
    r"^\s*(ls|ll|cat|less|head|tail|rg|grep|find|sed\s+-n|awk|"
    r"terraform\s+(fmt\s+-check|validate|plan|show|state\s+list|version)|"
    r"ansible-playbook\s+[^\n]*--check|git\s+(status|diff|log|show|rev-parse))\b"
)
WRITE_CMD_RE = re.compile(
    r"(?:\bsed\s+-i\b|\btee\b|\bmv\s|\bcp\s|\brm\s|\btruncate\b|"
    r"(?:^|[;&|])\s*(?:cat|printf|echo)\s.*>)"
)
LEAVE_GENERIC_RE = re.compile(
    r"(leave\s+generic\s+module|authorized\s+to\s+edit\s+generic)",
    re.I,
)
LEAVE_GUEST_SQL_RE = re.compile(
    r"allow\s+guest\s+sql",
    re.I,
)
BOOTSTRAPPER_NAME_RE = re.compile(r"bootstrapper", re.I)
ARCHITECTURE_STEM_RE = re.compile(r"^architecture_(.+)$")

MUTATING_TOOLS = {
    "write",
    "searchreplace",
    "multiedit",
    "edit",
    "runterminalcommand",
    "bash",
    "writetofile",
    "replacefilecontent",
    "multireplacefilecontent",
    "runcommand",
}
READ_TOOLS = {"readfile", "read", "viewfile"}
