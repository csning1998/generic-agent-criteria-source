---
name: skill-inspect-gitlab-mrs
effort: low
description: >
    Enumerate GitLab merge requests with glab and return a stable field
    contract (iid, title, web_url, merged_at, description). Use when the
    user asks to inspect, list, or pull GitLab MRs, or runs
    /skill-inspect-gitlab-mrs. Read-only. The write layer is
    skill-sync-gitlab-mrs-to-notion in the Second Brain repository.
metadata:
    short-description: "List GitLab MRs via glab"
---

# Inspect GitLab MRs

Layer for delivery read on GitLab.

## When to Use

The owner asked to list or inspect merge requests.

## Input Requirements

- Required: group or `owner/repo` from the owner in this turn.

## Process

1. If the target is missing, ask for the target.
2. Fill module JSON and call `~/.grok/skills/skill-module-inspect-gitlab-mrs/SKILL.md`.

```json
{
    "target_type": "repo",
    "target": "owner/repo",
    "state": "merged"
}
```

`state` is `merged` unless the owner named another state.

1. When the owner asked for descriptions, fill `summary_paragraph` from each `description`. Take the first paragraph after `## Summary` or `## Description`. If neither heading exists, use the first non-heading paragraph. Normalize `\r\n` to `\n`. Reject a bare heading such as `## Changes`.

## Output

Artifact `GitlabMrList` plus optional `summary_paragraph` on each record.

## Validation Checklist

- [ ] Timezone conversion was not applied here
- [ ] No Notion page was created

## Backtrack Triggers

- Module `ok` false: report `error` and stop.

## Example

`/skill-inspect-gitlab-mrs` plus a repo path lists merged MRs.
