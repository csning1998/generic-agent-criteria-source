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
_SQL_IDENT = r"(?:\"[^\"]+\"|[a-zA-Z_][\w.\"$]*)"
_SQL_PRIV = (
    r"(?:SELECT|INSERT|UPDATE|DELETE|TRUNCATE|REFERENCES|TRIGGER|"
    r"CREATE|CONNECT|TEMPORARY|TEMP|EXECUTE|USAGE|MAINTAIN|"
    r"ALTER\s+SYSTEM)(?:\s*\([^)]+\))?"
)
_PREPOSITION_STOP = (
    r"(?:for|in|of|from|to|with|on|by|at|as|and|or|the|a|an|if)"
)
MUTATING_SQL_RE = re.compile(
    r"("
    r"\bALTER\s+(?:USER|ROLE)\b"
    r"|\bINSERT\s+INTO\b"
    rf"|\bUPDATE\s+{_SQL_IDENT}\s+"
    rf"(?:(?:AS\s+)?[a-zA-Z_]\w*\s+)?SET\s+(?:\([^)]+\)|{_SQL_IDENT})\s*="
    r"|\bDELETE\s+FROM\b"
    rf"|\bTRUNCATE\s+(?:TABLE\s+{_SQL_IDENT}|"
    rf"(?:ONLY\s+)?(?!{_PREPOSITION_STOP}\b){_SQL_IDENT}"
    r"(?:\s*(?:;|,|'|\"|$)|\s+(?:RESTART|CONTINUE|CASCADE|RESTRICT)\b))"
    r"|\bDROP\s+(?:DATABASE|TABLE|USER|ROLE|SCHEMA)\b"
    rf"|\bCREATE\s+(?:USER|ROLE)\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    rf"(?!{_PREPOSITION_STOP}\b){_SQL_IDENT}"
    r"|\b(?:GRANT|REVOKE(?:\s+GRANT\s+OPTION\s+FOR)?)\s+"
    rf"(?:ALL(?:\s+PRIVILEGES)?|{_SQL_PRIV}(?:\s*,\s*{_SQL_PRIV})*)\s+ON\b"
    r"|\b(?:GRANT|REVOKE(?:\s+ADMIN\s+OPTION\s+FOR)?)\s+"
    r"(?:pg_\w+|[a-zA-Z_][\w$]*_[a-zA-Z0-9_$]+|\"[^\"]+\")\s+"
    rf"(?:TO|FROM)\s+(?!(?:the|a|an)\b){_SQL_IDENT}"
    r")",
    re.I,
)
SQL_GRANT_REVOKE_RE = re.compile(
    rf"\b(?:GRANT|REVOKE)\s+(?:ALL\b|{_SQL_IDENT}\s+(?:ON|TO|FROM)\b)",
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
ALLOW_FULL_OVERWRITE_RE = re.compile(
    r"\ballow\s+full\s+overwrite\b",
    re.I,
)
GREEN_AUTH_RE = re.compile(
    r"(可以轉綠|轉綠|進入綠燈|執行綠燈|authorize green|proceed to green)",
    re.I,
)
QUOTED_SPAN_RE = re.compile(
    r"(「[^」\n]*」|『[^』\n]*』|\"[^\"\n]*\"|`[^`\n]*`)"
)
GREEN_NEGATION_RE = re.compile(
    r"(不要|不能|不可|禁止|不得|別|尚未|還沒|不准|勿|取代|"
    r"\bdon['\u2019]?t\b|\bdo\s+not\b|\bcannot\b|\bcan['\u2019]?t\b|"
    r"\bnever\b|\bnot\b|\bavoid\b|\bstop\b)",
    re.I,
)
GREEN_QUESTION_RE = re.compile(
    r"(?:[？?]|嗎|是否|何時|什麼時候|為何|為什麼|"
    r"\b(?:can\s+(?:we|i)|should\s+(?:we|i))\b)",
    re.I,
)
TEST_RUNNER_CMD_RE = re.compile(
    r"\b(py\.?test|(?:bun(?:\s+run)?|npm|go)\s+test|npx\s+(?:vitest|jest))\b"
)
LINTER_CMD_RE = re.compile(
    r"\b(ruff\s+(?:check|format)|eslint|tsc|ng\s+lint|golangci-lint|"
    r"bun\s+run\s+(?:lint|check|build))\b"
)
COMPOSITE_VERIFY_CMD_RE = re.compile(r"(?:^|[;&|/\s])pytest\.sh\b")
STOP_BYPASS_TERMINATION_REASONS = frozenset(
    {
        "USER_CANCELED",
        "ERROR",
        "MAX_INVOCATIONS",
        "MAX_FORCED_INVOCATIONS",
        "MAX_TOKEN_BUDGET_EXCEEDED",
        "TERMINAL_STEP_TYPE",
        "TERMINAL_CUSTOM_HOOK",
    }
)
MAX_STOP_CONTINUATIONS = 2
TDD_TEST_GLOBS = (
    "**/tests/**",
    "*_test.py",
    "*_test.go",
    "*.test.ts",
    "*.test.tsx",
    "*.spec.ts",
    "*.spec.tsx",
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
    "writefile",
    "replacefilecontent",
    "multireplacefilecontent",
    "editfile",
    "runcommand",
}
READ_TOOLS = {"readfile", "read", "viewfile"}
