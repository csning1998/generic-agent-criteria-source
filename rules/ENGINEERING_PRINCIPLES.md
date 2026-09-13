# Collaboration Principles

This document defines resident, cross-project collaboration rules that remain invariant across products. Technology-stack architecture principles reside in `~/.agents/criteria/2_context/domain/` and MUST be loaded only when the current task requires that stack.

## Section 1. Read Adjudication First

Before modifying `terraform/`, `ansible/`, or `packer/` directories governed by `planning/architecture_<repo_name>*.md`, or before modifying `planning/` itself, the system MUST inspect `planning/decisions.md` and at least one corresponding `architecture*.md` specification. Following that inspection, the system MUST record migrations, identifier naming, the directed acyclic graph (DAG), and the current scope in writing. Repositories not referenced in architecture filenames are exempt from this requirement.

Modifying files prior to inspection introduces unadjudicated naming conventions and dependency cycles into shared paths.

## Section 2. Shared Modules Stay Generic

Shared modules (`terraform/modules/`, `ansible/roles/utils_*`) MUST declare only resource structures. Environment aliases and product identifiers MUST be passed in by callers. Modifying a shared module is prohibited unless the prompt contains the explicit execution phrase `leave generic module`.

Modifying a shared module for a single caller spreads business logic across all consuming callers.

## Section 3. One Owner Mints Secrets

Every secret MUST have exactly one designated owner responsible for generation. Dependent layers MUST only reference the generated secret. A consumer layer MUST NOT declare `random_password` and MUST NOT invoke a minting module.

Generating secrets within a consumer layer causes loss of the sole decryption key for durable data when transient layers are rebuilt.

## Section 4. Repair Declarations at the Source

When reality drifts from declarations, the system MUST modify the declaration source or MUST halt after an assertion failure. Introducing `psql`, `ALTER USER`, or `local-exec` into plays, Terraform configurations, Packer templates, standalone scripts, Makefiles, or CI pipelines as remediation steps is strictly prohibited. Read-only debugging on guest systems remains outside the hook gate. Modifying passwords or clearing dirty states using guest SQL masks declarative drift, causing repeated drift during subsequent deployments. Such commands require the turn-specific authorization phrase `allow guest sql` from the owner and MUST NOT be written to disk files.

## Section 5. Stay In Scope

Execution MUST be confined strictly to the designated scope. Defects identified outside the designated scope MUST be reported in dialogue text without modifying out-of-scope files.

Modifications outside the assigned scope prevent verification from aligning with the active adjudication.

## Section 6. Verify Before Stating Versions

Version numbers, default values, command-line flags, and deprecation states MUST be verified against official documentation prior to citation. When verifiable sources are absent, the system MUST declare insufficient information and MUST halt at that point.

Citing versions from unverified memory outputs invalid flags and obsolete defaults.

The PreToolUse hook blocks only statically verifiable actions defined in Section 1 through Section 4. Modifying shared modules requires the phrase `leave generic module` in the prompt. Disabling the hook requires setting `ENGINEERING_PRINCIPLES_HOOK=0`.
