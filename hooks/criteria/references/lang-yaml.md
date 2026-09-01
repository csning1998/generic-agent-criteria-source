# **YAML / Jinja2 (`*.yaml`, `*.yml`, `*.j2`) Specific Standards**

- **(a) Applicable Scope**：Includes Ansible playbooks, roles, `group_vars`, and Jinja2 templates rendered by Ansible
- **(b) Structure**：
    - A document MUST open with `---`
    - 2-space indent is mandatory. Tabs are strictly prohibited
    - A list item under a mapping key MUST NOT be additionally indented past the key, per the project's existing `yamllint` configuration
- **(c) Naming and Values**：
    - `snake_case` MUST be used for task names' variable references and for role/variable identifiers
    - Boolean literals MUST use `true`/`false`. `yes`/`no` and `True`/`False` are prohibited
    - A role's own variables MUST be prefixed with that role's name, matching this repository's existing `<role>_<purpose>` convention
- **(d) Idempotency and Task Design**：
    - A task that only inspects state MUST set `changed_when: false`
    - A privileged action MUST use `become: true` at the narrowest scope that needs it, not inherited from an unrelated outer block
    - A destructive or irreversible task MUST be guarded by a `when:` condition stating the exact precondition, not left unconditional
- **(e) Jinja2 Templating**：
    - A multi-line string concatenation MUST use the `~` operator inside a single `{{ }}` expression. A folded scalar (`>-`) or a backslash line continuation MUST NOT be used to concatenate a string, since either introduces a literal space at the line break
    - A secret value rendered into a template MUST NOT be logged; the task that produces it MUST set `no_log: true`
