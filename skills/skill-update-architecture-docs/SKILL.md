---
name: skill-update-architecture-docs
effort: medium
description: >
    Write an adjudicated fact into a project planning tree after an
    architecture discussion or a merged change. Use when the owner
    asks to update architecture documents, absorb a decision, sync
    planning after a merge request, or runs
    /skill-update-architecture-docs. Default is list-only. Writing
    requires an explicit ask in the current turn. Notion Task fill
    stays in skill-sync-gitlab-mrs-to-notion in the Second Brain repository.
metadata:
    short-description: "Write adjudicated facts into planning docs"
---

# Update architecture documents

Layer for planning write. This file owns how a fact is written once into the adjudication file and cited elsewhere.

## When to Use

The owner asked to update planning documents after a discussion or after a merge.

## Input Requirements

- Required: `planning_root` named in this turn.
- Required: either `ArchitectureConflictReport` from this session, or an adjudication the owner stated in this turn.
- Optional: `GitlabMrList` when the owner named a GitLab target.

Read `~/.grok/skills/modules/shared/write-gate.md`.

Default file names match `skill-inspect-architecture-docs`.

## Process

1. If this turn has no update ask, keep read-only and stop.
2. If `planning_root` is missing, ask for `planning_root` and stop.
3. If there is no `ArchitectureConflictReport` and the owner did not state a decision in this turn, run `skill-inspect-architecture-docs` first. Stop on any `open` finding.
4. Write the fact once into the adjudication file. Other planning files may cite that name or drop the stale sentence. Do not paste the same paragraph into every topic file.
5. Edit only files under `planning_root`. Do not edit a repository `documentation/` tree, or any other verified-implementation directory, unless the owner said the implementation was already verified in this turn.
6. When the owner asked to archive a merged GitLab merge request, call `skill-sync-gitlab-mrs-to-notion` in the Second Brain repository. Do not fill Task properties in this layer.
7. When the owner asked to archive a discussion that has no merge request, stop and ask which existing write layer to use. Do not invent a second Task fill table.

## Output

Artifact `ArchitectureDocsUpdated`.

```json
{
    "planning_root": "/absolute/path",
    "adjudication_file": "decisions.md",
    "wrote": ["decisions.md", "architecture.md"],
    "skipped_implementation_docs": true,
    "notion_handoff": null
}
```

`notion_handoff` is the write layer name when step 6 ran, else `null`.

## Validation Checklist

- [ ] Write ran only after an ask in this turn
- [ ] The new fact has one home in the adjudication file
- [ ] Implementation documentation was not edited
- [ ] Notion Task fields were not filled here

## Backtrack Triggers

- An `open` finding remains: return to `skill-inspect-architecture-docs` and stop.
- Owner asked to archive a discussion with no merge request: ask which write layer to call.
- Sync layer reports no create: keep the local write result and report that Notion handoff.

## Example

Owner says to write the deploy-order decision into `~/code/app/planning`. Layer updates `decisions.md` and removes the stale sentence from one topic file.
