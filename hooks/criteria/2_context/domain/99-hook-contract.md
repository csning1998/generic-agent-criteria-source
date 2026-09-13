# Sub-doc 99. Hook Operating Contract

This file is the complete form of Section 10 in `ENGINEERING_PRINCIPLES.md`. The baseline date is 2026-08-18.

The PreToolUse hook is the only hook event that can deny a tool call. The Stop hook can block the agent from ending a turn. The SessionStart hook creates session state and injects no file. The UserPromptSubmit hook records owner leave phrases and injects no file. The PostToolUse hook on a read records the opened path. The PostToolUse hook on a skill-module write records the path and scans the file on disk.

The PreToolUse hook inspects the tool name, the target path, and the text about to be written. The PreToolUse hook does not classify work from the wording of the owner's task. Two different phrasings of the same mutation receive the same decision.

## Section 1. Prerequisite Reading

1. **Trigger Condition**. When the current session will mutate `terraform/`, `ansible/`, or `packer/` under a repository whose name appears in `planning/architecture_<repo>*.md`, or will mutate `planning/` itself, the executing Agent MUST first open `planning/decisions.md` and at least one matching `planning/architecture*.md` with the read-file tool. The file-name convention is `architecture_<repo>_<topic>.md`. A repository whose name does not appear in those file names is outside this gate. When `planning/` contains `architecture.md` and contains no `architecture_<repo>*.md` file, the PreToolUse hook treats every governed path as inside the gate.

2. **Post-read Checklist**. After those reads, and before the first mutation, the executing Agent MUST write four checks. The four checks are the planned move, the planned name, the DAG direction, and whether the mutation sits inside the current task. Completing the four checks only in working memory does not satisfy Section 1 item 2. The PreToolUse hook does not read the written checklist. The PreToolUse hook only records that the files were opened.

3. **Reading Cannot Be Substituted**. A search-result fragment does not count as a read. Context from an earlier session does not count as a read. Inferring content from a file name does not count as a read. The PreToolUse hook counts a path only after the read-file tool opened that path in the current session.

## Section 2. Generic Module Authorization

1. **Authorization Phrase**. A mutation of `terraform/modules/` or `ansible/roles/utils_*` requires one of the following phrases in an owner prompt of the current session. The phrases are `leave generic module` and `authorized to edit generic`. A mutating guest SQL command requires `allow guest sql`. A read-only guest `psql` session does not. The UserPromptSubmit hook records that phrase. A request such as `fix that module` does not record leave.

2. **Still Prohibited After Authorization**. After generic leave is recorded, the PreToolUse hook still denies a newly added environment alias, a newly added `vault.production` address, a newly added `vault = vault` map, and a newly added product token in a variable name, resource name, tag key, or output key. After guest SQL leave is recorded, the PreToolUse hook still denies a write that embeds `psql`, `ALTER USER`, or `community.postgresql` in a file.

3. **Authorization Scope**. Leave applies to the current session. When the owner prompt that carries the leave phrase also names a module path, the PreToolUse hook permits only a path that contains that name. When the owner prompt carries the leave phrase and names no module, the PreToolUse hook permits every generic-module path. Expanding the mutation to a module that the named list does not contain requires a new owner prompt that names that module.

## Section 3. Blocking Rules

### Item A. Blocking Conditions

1. The PreToolUse hook denies a write in each of the following cases.
    1. The target path is inside a repository covered by Section 1, and the current session has not opened the files that Section 1 requires.
    2. The target path is a generic module, and the current session has no leave that covers that path.
    3. The write adds an environment alias (`prod`, `stg`, `dev`) or adds `vault.production` or `vault = vault` inside a generic module.
    4. The write adds a product name to a variable name, resource name, tag key, or output key inside a generic module.
    5. The write adds a `local-exec` provisioner, a `remote-exec` provisioner, an Ansible `shell` or `command` task that lacks `changed_when` or `creates` or `removes`, a `psql` / `ALTER USER` / `community.postgresql` invocation inside a `terraform/`, `ansible/`, or `packer/` file, a mutating `psql` / `ALTER USER` invocation in any other write (including `scripts/`, a Makefile, and CI), or a mint (`random_password` or a vault-credential module call) inside a consumer layer. A read-only debug shell on a guest is outside this gate. Guest SQL that mutates state (password reset, dirty-flag clear) remains in scope.

A pre-existing fragment that already matched a forbidden pattern does not deny a write that only edits other lines. An image tag does not deny a write. A lock-file edit does not deny a write.

1. **Behavior After Blocking**. After a deny, the executing Agent MUST print the rule identifier and the line numbers from the deny reason. The executing Agent MUST NOT rewrite the payload so that the pattern no longer matches while the same action remains. A rewrite of that kind is itself a violation.

2. **Exceptions**. Owner intent for a time-bounded exception MUST be a named entry in `planning/decisions.md`. The named entry MUST state the scope and the end date. A comment in code MUST NOT declare an exception. The PreToolUse hook does not read `planning/decisions.md` for exceptions. The named entry therefore does not disable Item A. A local experiment that must pass Item A requires `ENGINEERING_PRINCIPLES_HOOK=0`.

## Section 4. Skill-module Statelessness

1. **PreToolUse**. When the write target path contains `skill-module-`, or a shell redirect, `tee`, `cp`, `mv`, or `sed -i` destination contains `skill-module-`, the PreToolUse hook scans the composed file text, any heredoc body, and `echo` / `printf` / `sed` payloads. The rest of the shell command is not file content. A `search_replace` compose is the current file with `old_string` replaced by `new_string`. Disk reads stay under `workspaceRoot` or `~/.grok`.
2. **PostToolUse**. After a successful mutation of a skill-module write target, the PostToolUse hook records that path and scans the file on disk.
3. **Stop**. When the turn ends, the Stop hook reads each recorded skill-module path. A remaining denied token blocks the stop. The executing Agent MUST rewrite the file so that only placeholders remain.
4. **Denied Tokens**. The hook denies a collection UUID, an absolute `/home/` or `$HOME/` owner path, the owner login, and the Failure Managements collection prefix `316919d4`. Placeholder tokens inside `<...>` are stripped before that identifier scan. The hook then parses JSON objects in the file with `json.JSONDecoder`. A mapping table key (`allowlist`, `type_from_conv`, `repo_area`, and the sibling keys) is denied when any string in that value is not a placeholder. An empty `{}` or `[]`, or a value whose strings are only placeholders, is allowed.
5. **Required Correction**. After a deny or a Stop block, the executing Agent MUST move those values into layer JSON. The module file MUST keep placeholders only.

## Section 5. Disabling

1. **How to Disable**. The owner disables the hook by setting `ENGINEERING_PRINCIPLES_HOOK=0`.

2. **Restrictions on Disabling**. `ENGINEERING_PRINCIPLES_HOOK=0` is allowed only on a local experiment. A CI job and any environment that produces a mergeable change MUST keep the hook enabled. A change produced while the hook is disabled MUST be re-checked with the hook enabled before the change is committed.

## Section 6. Behavioral Requirements for the Executing Agent

1. **Scope Must Not Expand**. The executing Agent MUST mutate only the range that the owner named. When the executing Agent finds a defect outside the named range, the executing Agent MUST report the defect in text and MUST NOT edit the out-of-range defect.

2. **Fact Verification**. Before the executing Agent states a version, a default, a flag name, or a deprecation status, the executing Agent MUST verify that claim. When verification fails, the executing Agent MUST write `目前缺乏足夠的最新資訊` and MUST stop on the unverified claim. The executing Agent MUST NOT fill the gap with a guess. The high-volatility list is Section 2 of `00-loading-protocol.md`.

3. **Rules Must Not Be Self-downgraded**. When a rule and convenience conflict, the executing Agent MUST follow the rule and MUST report the conflict. The executing Agent MUST NOT decide that a clause does not apply to the current case.
