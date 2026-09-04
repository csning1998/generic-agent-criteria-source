---
name: skill-module-gitlab-mr-discussions
effort: low
description: >
    Fetch, reply to, or resolve GitLab merge request discussion threads
    from JSON a layer already filled. Use when a skill- hands off that
    JSON, or when the user runs /skill-module-gitlab-mr-discussions.
metadata:
    short-description: "Fetch, reply, resolve GitLab MR discussions"
---

# Module GitLab MR discussions

## When to Use

A layer already filled `project`, `mr_iid`, and either `mode: "fetch"` or `mode: "apply"` with an `actions` list.

## Input Requirements

JSON from the calling layer. Read it from `payload_path` when that key is set.

Fetch call:

```json
{
    "project": "owner/repo",
    "mr_iid": 40,
    "mode": "fetch"
}
```

Apply call:

```json
{
    "project": "owner/repo",
    "mr_iid": 40,
    "mode": "apply",
    "allow_reply": false,
    "allow_resolve": false,
    "actions": [
        { "discussion_id": "abc123", "do": "resolve" },
        { "discussion_id": "def456", "do": "reply", "body": "text" },
        { "discussion_id": "ghi789", "do": "reply_and_resolve", "body": "text" }
    ]
}
```

`allow_reply` and `allow_resolve` are two independent gates. Neither implies the other. This module does not infer either flag from the actions list.

## Process

1. Refuse the call when `project` or `mr_iid` is missing. Return `ok` false.
2. Confirm `glab auth status`.
3. For `mode: "fetch"`: page `glab api projects/<project>/merge_requests/<mr_iid>/discussions` and return every discussion whose first note is not a system note.
4. For `mode: "apply"`: refuse the call when `actions` is missing. For each action:
    1. When `do` includes `reply` and `allow_reply` is not `true`, record `status: "refused"`, `reason: "allow_reply is false"`, and skip the reply.
    2. When `do` includes `resolve` and `allow_resolve` is not `true`, record `status: "refused"`, `reason: "allow_resolve is false"`, and skip the resolve.
    3. Otherwise `POST` the note when a reply is due, then `PUT resolved=true` when a resolve is due, and record `status: "done"`.
5. Never delete a note. Never call `git push`. Never touch a discussion ID absent from `actions`.

```bash
python3 scripts/discussions.py "<payload_path>"
```

## Output

Artifact `GitlabMrDiscussionsResult`.

```json
{
    "ok": true,
    "error": null,
    "mode": "apply",
    "discussions": [],
    "results": [
        {
            "discussion_id": "abc123",
            "do": "resolve",
            "status": "done",
            "reason": null
        }
    ]
}
```

`discussions` is filled only for `mode: "fetch"`.

## Validation Checklist

- [ ] No action ran whose gating flag (`allow_reply` or `allow_resolve`) was false
- [ ] No discussion outside the `actions` list was modified
- [ ] `git push` was not invoked
- [ ] `ok` is false when `glab` is not authenticated

## Backtrack Triggers

- `glab` not authenticated: `ok` false. The layer asks the owner to log in.
- A discussion ID not found: record that action `status: "failed"`, continue the remaining actions.

## Example

Layer sends `mode: "fetch"`. Module returns every open and resolved discussion. Layer sends `mode: "apply"` with `allow_resolve: true` and `allow_reply: false`; the module resolves the listed discussions and refuses every `reply` action in the same batch.
