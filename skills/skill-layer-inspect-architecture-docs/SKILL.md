---
name: skill-layer-inspect-architecture-docs
effort: medium
description: >
    Read a project planning tree, find mutually exclusive claims,
    and stop on open conflicts. Use when the owner asks to review
    architecture documents, resolve planning conflicts, audit
    decisions against topic files, or runs
    /skill-layer-inspect-architecture-docs. Read-only. The write layer is
    /skill-layer-update-architecture-docs. Not a Terraform, security, or
    test-authoring skill.
metadata:
    short-description: "Review planning docs for open conflicts"
---

# Inspect architecture documents

Layer for planning read. This file owns conflict classes and the `ArchitectureConflictReport` field names.

## When to Use

The owner asked to review architecture or planning documents, or to list conflicts before an update.

## Input Requirements

- Required: `planning_root`, a directory the owner named in this turn.
- Optional: `GitlabMrList` when the owner named a GitLab group or `owner/repo`. Produce it in Process step 3.
- Optional: extra file names when the tree does not use the defaults.

Default file names when they exist under `planning_root`:

- Adjudication: `decisions.md`
- Overview: `architecture.md`
- Topics: `architecture_*.md`
- Work list: `To-do-list.md`

Do not assume a host path. Do not assume a cloud or on-prem product.

## Process

1. If `planning_root` is missing, ask for it and stop.
2. List Markdown files in that directory. Use the defaults above. If none of those names exist, ask the owner to name the adjudication file and the topic files.
3. When the owner named a GitLab group or `owner/repo`, fill `skill-module-inspect-gitlab-mrs` JSON. Keep `GitlabMrList`. When the owner named an `iid`, keep that record only. Take `summary_paragraph` with the rule in `skill-layer-inspect-gitlab-mrs`.
4. Read the adjudication file first. Treat it as the authority for any fact it already names.
5. Extract normative claims from the overview, topic files, and work list. Compare each claim to the adjudication file and to the other topic files.
6. Classify each finding. Use only these classes:
    - `requirement`: two normative statements cannot both hold
    - `ownership`: two parties claim exclusive ownership of one resource
    - `sequence`: a stated order contains a cycle
    - `authority`: two files both claim to be the source for the same fact
    - `lifecycle`: a secret or credential is specified to persist in a shared inspectable snapshot
    - `role_mix`: a verified-implementation file holds an unexecuted plan, or a plan file is treated as runtime truth

7. If the adjudication file already picks one side, emit `status` `stale` with the losing cite. Do not reopen it.
8. If this turn already contains an owner pick, emit `status` `ready_to_write`. Do not edit files.
9. Otherwise emit `status` `open`. List the colliding cites. Do not pick a side.
10. Do not compare the planning tree to application source unless the owner asked for an implementation audit in this turn.

## Output

Artifact `ArchitectureConflictReport`.

```json
{
    "planning_root": "/absolute/path",
    "adjudication_file": "decisions.md",
    "files_read": ["decisions.md", "architecture.md"],
    "gitlab_iid": null,
    "findings": [
        {
            "class": "requirement",
            "status": "open",
            "summary": "two files require opposite deploy orders",
            "cites": [
                { "path": "architecture.md", "claim": "..." },
                { "path": "architecture_topic.md", "claim": "..." }
            ]
        }
    ]
}
```

## Validation Checklist

- [ ] No planning file was written
- [ ] No application source was treated as a defect unless the
      owner asked for an implementation audit
- [ ] Every `open` finding has no chosen side
- [ ] GitLab text came from `GitlabMrList` when a repo was named

## Backtrack Triggers

- `planning_root` missing: ask and stop.
- Two adjudication files and no owner pick: ask which file is authority and stop.
- Inspect GitLab module `ok` false: report `error` and continue with local files only.

## Example

Owner names `~/code/app/planning` and asks to review conflicts. Layer reads that tree and returns `ArchitectureConflictReport`.
