---
name: skill-review-gitlab-mr-comments
effort: medium
description: >
    Fetch GitLab merge request review comments, verify each claim
    against the current repository or a live system before fixing
    code, then reply to or resolve threads only under a separate
    explicit ask for each. Use when the owner asks to investigate,
    triage, or address merge request comments, or runs
    /skill-review-gitlab-mr-comments.
metadata:
    short-description: "Verify MR review comments, fix, gate reply/resolve"
---

# Review GitLab MR comments

Layer for delivery write. This file owns the verify-then-fix decision and the reply/resolve gate. It does not own commit batching; hand a fix off to `skill-commit-soc` when the owner asks to commit.

## When to Use

The owner asked to investigate, triage, or address review comments on a named merge request.

## Input Requirements

- Required: `project` and `mr_iid` from the owner in this turn.
- Optional: a subset of discussion IDs or file paths the owner named. Absent that, this layer reads every unresolved thread.

Read `~/.grok/skills/modules/shared/write-gate.md`.

## Process

1. Fill `{"project": ..., "mr_iid": ..., "mode": "fetch"}` and call `~/.grok/skills/skill-module-gitlab-mr-discussions/SKILL.md`.
2. For each unresolved thread, read the file and line the thread names at its current committed state. Verify the claim against that content, a live command, or a test run. A thread MUST NOT be marked confirmed on the reviewer's wording alone.
3. Classify each thread `confirmed`, `refuted`, or `partial`. Cite the evidence for `confirmed` and for `refuted`: the file diff, the command run, and its output.
4. Apply a code fix for every `confirmed` and `partial` thread, in this turn, using the ordinary file-edit tools. This step is outside the module boundary.
5. Run the repository's own lint and validate commands against every file this layer touched. A thread whose fix fails that check stays `confirmed` but unresolved; report the failure instead of proceeding.
6. Build the `actions` list.
    1. A `confirmed` or `partial` thread whose fix passed defaults to `{"do": "resolve"}`.
    2. A `refuted` thread receives no action by default.
    3. Add `"reply"` to a `do` value, or add a `refuted` thread to `actions`, only when the owner asked for a reply on that thread in this turn.
7. Set `allow_resolve` to `true` only when the owner asked to resolve in this turn. Set `allow_reply` to `true` only when the owner separately asked to reply in this turn. An ask covering one flag MUST NOT set the other.
8. Fill `{"project": ..., "mr_iid": ..., "mode": "apply", "allow_reply": ..., "allow_resolve": ..., "actions": [...]}` and call the module.
9. When the owner later asks to remove a reply this layer posted, call the module's underlying `glab api DELETE` path directly; this module contract does not delete notes.

## Output

Artifact `GitlabMrCommentTriageResult`.

```json
{
    "threads": [
        {
            "discussion_id": "abc123",
            "file": "path/to/file",
            "verdict": "confirmed",
            "evidence": "one line naming the file, command, or output that settled it",
            "fix_applied": true,
            "action_taken": "resolve"
        }
    ]
}
```

## Validation Checklist

- [ ] Every `confirmed` and `refuted` verdict names its evidence
- [ ] `allow_reply` and `allow_resolve` were each set `true` only after their own explicit ask in this turn
- [ ] No `refuted` thread was resolved
- [ ] Lint and validate ran against every file this layer edited before that thread was marked resolved

## Backtrack Triggers

- Module `mode: "fetch"` returns `ok` false: stop and report.
- A `confirmed` fix fails lint or validate: leave the thread unresolved, report the failure, do not call `mode: "apply"` for that thread.
- The owner corrects a verdict this layer already applied: patch this file's classification step in the same turn.

## Example

Owner asks to investigate the comments on `!40`. Layer fetches twelve threads, confirms ten against live SSH and `terraform validate` evidence, refutes two against a live service-status check, and reports the verdicts. Owner separately asks to resolve the confirmed ten; layer sets `allow_resolve` true and `allow_reply` false, and calls the module. No reply is posted, since that ask never came.
