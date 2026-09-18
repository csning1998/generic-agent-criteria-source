---
name: skill-apply-gitlab-mr-labels
effort: medium
description: >
    Fill GitLab merge request label mapping JSON from group_labels and
    owner rules, then run the GitLab labels module. Use when the user
    asks to realign, apply, or rewrite GitLab MR labels from
    group-governance, or runs /skill-apply-gitlab-mr-labels.
metadata:
    short-description: "Fill and apply GitLab MR labels"
---

# Apply GitLab MR labels

Layer for delivery write. This file owns mapping tables for merge request labels.

## When to Use

The owner asked to realign, apply, or rewrite merge request labels under a GitLab group.

## Input Requirements

- Required: GitLab group path from the owner.
- Required: path to the Terraform file that declares `group_labels`.

Read `~/.grok/skills/modules/shared/write-gate.md`.

## Process

1. Extract allowlist keys from `group_labels` in the Terraform file. Do not invent a name that is absent from that map.
2. Fill module JSON. Execution keys are `mode`, `group`, `include_subgroups`, `sleep_s`, `only_if_changed`, and `allow_clear`. Put every mapping table under `tables`. Mapping tables live only in this layer.
3. Write `/tmp/skill-apply-gitlab-mr-labels/<run>/` with mode `0700` and `input.json` there.
4. Default `mode` is `dry-run`. Set `mode` to `apply` only when the write gate allows it.
5. Call `~/.grok/skills/skill-module-gitlab-mr-labels/SKILL.md` with that JSON.

Fill these tables unless the owner overrode a row in this turn.

`type_from_conv` maps the Conventional Commit type in the merge request title:

```json
{
    "feat": "type::feature",
    "fix": "type::fix",
    "hotfix": "type::fix",
    "docs": "type::documentation",
    "doc": "type::documentation",
    "refactor": "type::refactor",
    "test": "type::test",
    "perf": "type::enhancement",
    "build": "type::adhoc",
    "chore": "type::adhoc",
    "ci": "type::adhoc",
    "revert": "type::adhoc",
    "style": "type::adhoc"
}
```

`repo_area` is the fallback when title, scope, and existing labels do not yield `area::`:

```json
{
    "csning1998-lab/personal/on-premise-gitlab-deployment": "area::infrastructure",
    "csning1998-lab/meta-platform": "area::infrastructure",
    "csning1998-lab/parent-group-governance": "area::infrastructure",
    "csning1998-lab/personal/on-premise-agent": "area::infrastructure",
    "csning1998-lab/personal/generic-agent-criteria-source": "area::CI",
    "csning1998-lab/personal/second-brain": "area::frontend",
    "csning1998-lab/personal/app-content-matter": "area::frontend",
    "csning1998-lab/personal/monte-carlo-portfolio-trader": "area::backend",
    "csning1998-lab/template/template-project": "area::infrastructure",
    "csning1998-lab/template/template-project-fullstack": "area::infrastructure",
    "csning1998-lab/rug/ams-flight-ingestion": "area::backend",
    "csning1998-lab/rug/ams-flight-ingestion-merge": "area::backend"
}
```

`area_patterns` is first match wins against scope plus title:

```json
[
    {
        "pattern": "observab|lgtm|mimir|loki|grafana|alloy|telemetry|\\bmetric",
        "label": "area::observability"
    },
    {
        "pattern": "(?:^|[/(,])(?:fe|frontend|ui)(?:$|[/,)])|vue",
        "label": "area::frontend"
    },
    {
        "pattern": "(?:^|[/(,])(?:be|backend|api)(?:$|[/,)])",
        "label": "area::backend"
    },
    {
        "pattern": "(?:^|[/(,])(?:ci|pipeline)(?:$|[/,)])|gitlab-ci|ci-templates|catalog",
        "label": "area::CI"
    },
    {
        "pattern": "terraform|ansible|packer|vault|harbor|kube|k8s|libvirt|infra|pki|network|hook|selinux|hypervisor",
        "label": "area::infrastructure"
    }
]
```

`old_area` rewrites unscoped names that already mean an area. `title_contains` adds an orthogonal label. `selinux` adds `security`. `bang_adds` is `breaking-change`. `rename` maps `pending` to `status::pending`. `keep_prefixes` are `priority::`, `status::`, `action::`. `keep_exact` is the unscoped allowlist set: `security`, `breaking-change`, `do-not-merge`, `good first issue`, `help wanted`, `issue`.

## Output

Artifact `GitlabMrLabelResult` (same JSON as the module).

## Validation Checklist

- [ ] Allowlist keys came from `group_labels`
- [ ] Mapping tables were filled in this layer
- [ ] `glab` was not called except through the module
- [ ] `mode` `apply` ran only after an ask in this turn

## Backtrack Triggers

- Terraform file missing `group_labels`: stop.
- Module `ok` false: report `error` and stop.

## Example

Owner says realign `csning1998-lab` merge request labels. Layer writes `input.json` and calls the module.
