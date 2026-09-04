# Sub-doc 51. Ansible

Sections 1 through 9 of `ENGINEERING_PRINCIPLES.md` apply to this file. The baseline date is 2026-08-18.

## Section 1. Version and Compatibility

### Item A. ansible-core Breaking Changes

ansible-core 2.19 introduced Data Tagging and a rewritten templating engine. That change is breaking. A non-string conditional, a value passed through a Jinja macro, a `default()` after `deepcopy`, and a loop input that is not a list raise an error after 2.19. Those inputs used to pass silently.

Official source URL is <https://docs.ansible.com/projects/ansible-core/devel/porting_guides/porting_guide_core_2.19.html>

ansible-core 2.20 (Ansible 13) deprecated `INJECT_FACTS_AS_VARS`. The controller requires Python 3.12 or newer.

Before the executing Agent writes or edits a playbook, the executing Agent MUST confirm the ansible-core version of the target environment and MUST follow the porting guide for that version. Templating behavior from 2.18 and earlier MUST NOT be assumed.

1. **Collection Pinning**. `requirements.yml` MUST pin each collection version. A module call MUST use an FQCN such as `ansible.builtin.copy`. A bare name such as `copy` is forbidden.

## Section 2. Idempotency

1. **Module Precedence**. When a module exists for an operation, the task MUST use that module. `ansible.builtin.shell` and `ansible.builtin.command` are allowed only when no module exists. Those two modules MUST also set `creates`, `removes`, or `changed_when`, so that the task is idempotent and reports change correctly.

2. **changed_when and failed_when**. A `shell` or `command` task that lacks `changed_when` violates Section 2 Item A of `ENGINEERING_PRINCIPLES.md`. That omission makes `--check` and a convergence test meaningless.

3. **Automatic Reset Prohibited**. A task that detects a broken service and then re-initializes a data directory is forbidden. A task that detects an unhealthy cluster and then rebuilds that cluster is forbidden. Section 2 Item C of `ENGINEERING_PRINCIPLES.md` applies. The task MUST assert and fail.

## Section 3. Variables and Scope

1. **Explicit Precedence**. An implicit override that relies on Ansible variable precedence is forbidden. The same variable name MUST NOT appear in `group_vars`, `host_vars`, `vars`, and `set_fact` as a means of covering one value with another.

2. **Naming Prefix**. A variable that is internal to a role MUST use the role name as a prefix. The public contract of a role MUST be declared in `defaults/main.yml` with a type note. `vars/main.yml` MAY hold only constants that the caller MUST NOT override.

3. **Generic Roles**. Every path under `ansible/roles/utils_*` follows Section 3 of `ENGINEERING_PRINCIPLES.md`. A generic role MUST NOT look up an environment-specific inventory group. A generic role MUST NOT branch on an environment alias.

## Section 4. Inventory and Connections

1. **Inventory Is a Declaration**. The output of a dynamic inventory plugin MUST be reproducible. A playbook MUST NOT call `add_host` to create a host that changes the topology of a later play, unless that host was created in the current run and `planning/` already records that flow.

2. **Delegation**. `delegate_to` MUST name a concrete host or a concrete group member. `delegate_to` MUST NOT name an expression that changes with the moment of execution. Ansible evaluates `delegate_to` before the task condition. A skipped task that points at an undefined variable still fails.

## Section 5. Execution and Verification

1. **Check Mode Must Work**. Every role MUST complete under `--check --diff` without a false error. A task that cannot support check mode MUST set `check_mode: false` and MUST state the reason.

2. **Convergence Verification**. CI MUST run the play twice. The second run MUST report zero changed tasks. A task that reports changed on the second run is a defect.

3. **Serialization**. A change to a quorum component (see `80-stateful-and-quorum.md`) MUST set `serial: 1` or a stricter value, and MUST set `max_fail_percentage: 0`.

## Section 6. Sensitive Values

1. **Vault File Precedence**. A secret MUST use a file-level ansible-vault. An inline vault string is forbidden. Under templating after 2.19, an inline vault variable and a file vault variable do not behave the same on a re-render path.

2. **no_log**. A task that handles a secret MUST set `no_log: true`. The executing Agent MUST also confirm that an error from that task does not write the secret into the journal.
