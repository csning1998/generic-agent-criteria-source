# Skills architecture

Read `~/.grok/docs/skill-system/README.md` before editing a skill. Upstream source and the reference list are `~/.grok/docs/skill-system/reference/NOTICE.md`.

A `skill-*` file is a layer. The layer fills JSON and owns field names. A `skill-module-*` file is stateless. The module receives JSON, maps that JSON onto one tool, and returns JSON. The module MUST NOT bake collection IDs, group paths, mapping tables, or owner home paths. A context contract is an external `docs_root`. Identifiers live in `03-identifiers.md` under that `docs_root`. The layer copies that ID.

## Section 1. Contract

Every layer and every module uses these sections:

1. When to Use
2. Input Requirements
3. Process
4. Output (named artifact plus JSON)
5. Validation Checklist
6. Backtrack Triggers
7. Example

A later layer consumes a named artifact. The later layer does not reopen an upstream module to recompute a field.

If the Notion API changes, only `skill-module-file-notion-resources` changes. yt-dlp and Buzz modules stay untouched.

## Section 2. Naming

| Kind   | Prefix          | Role                                                 |
| ------ | --------------- | ---------------------------------------------------- |
| Layer  | `skill-`        | Fill JSON. Sequence modules. Own destination fields. |
| Module | `skill-module-` | Stateless. Execute one tool. Return JSON.            |

Frontmatter `effort` on each `SKILL.md` is the spawn budget. Roles live in `~/.grok/roles/`. `low` maps to `exec-low`. `medium` maps to `exec-medium`. Do not spawn bare `general-purpose` for those two values.

## Section 3. Contexts

### Item A. Media ingest

- Layers: `skill-yt-dlp`, `skill-buzz-transcribe`
- Modules: `skill-module-yt-dlp`, `skill-module-buzz-transcribe`, `skill-module-media-tags`
- Artifacts: `WatchMedia`, `TranscriptDone`, `MediaTags`, `VideoResourcePayload`

`skill-transcribe-youtube-video-to-notion-resources` lives in the Second Brain repository. `skill-transcribe-youtube-video-to-notion-resources` sequences download, transcribe, and Notion write. YouTube fill lives only in `skill-transcribe-youtube-video-to-notion-resources`.

### Item B. Knowledge filing

- Modules: `skill-module-inspect-second-brain`, `skill-module-file-notion-resources`
- Artifacts: `SecondBrainLocate`, `ResourceFiled`, `NotionWriteResult`

`skill-inspect-second-brain` and `skill-file-notion-resources` live in the Second Brain repository.

### Item C. Delivery

- Layers
    - `skill-inspect-gitlab-mrs`
    - `skill-apply-gitlab-mr-labels`
    - `skill-review-gitlab-mr-comments`
- Modules
    - `skill-module-inspect-gitlab-mrs`
    - `skill-module-inspect-notion-tasks`
    - `skill-module-file-notion-resources`
    - `skill-module-gitlab-mr-labels`
    - `skill-module-gitlab-mr-discussions`
- Artifacts
    - `GitlabMrList`
    - `NotionTaskRows`
    - `TaskFiled`
    - `GitlabMrLabelResult`
    - `GitlabMrCommentTriageResult`
    - `GitlabMrDiscussionsResult`

Task fill lives in `skill-sync-gitlab-mrs-to-notion` in the Second Brain repository, and in `tasks.md` under `docs_root`. Label mapping tables live in `skill-apply-gitlab-mr-labels`. Verdict evidence and the reply/resolve gate live in `skill-review-gitlab-mr-comments`. `skill-review-gitlab-mr-comments` hands SoC commit batching to `skill-commit-soc`.

### Item D. Workspace

- Modules: `skill-module-drive-para`, `skill-module-local-gtd`
- Artifacts: `DriveCensus`, `LocalGtdResult`, `WorkspaceCensus`

`skill-inspect-google-drive` lives in the Second Brain repository.

### Item E. Tooling

- Layers: `skill-update-antigravity`, `skill-commit-soc`
- Modules: `skill-module-update-antigravity`, `skill-module-git-commit`
- Artifacts: `AntigravityResult`, `GitCommitResult`

`skill-commit-soc` fills SoC commit batches. The module applies `git add` and `git commit` only when the layer sets `execute` true for generic-agent-criteria-source. The module never runs `git push`.

### Item F. Architecture documents

- Layers: `skill-inspect-architecture-docs`, `skill-update-architecture-docs`
- Modules: `skill-module-inspect-gitlab-mrs`
- Artifacts: `ArchitectureConflictReport`, `ArchitectureDocsUpdated`

Inspect is read-only. Update writes the planning tree after an ask. A merged merge request that the owner asked to archive is handed to `skill-sync-gitlab-mrs-to-notion` in the Second Brain repository. Task fill stays in `skill-sync-gitlab-mrs-to-notion` and in `tasks.md` under `docs_root`. These layers do not own Terraform DAG, security, test authoring, idempotency, or module-shape review.

## Section 4. Shared kernel

| File                           | Fact                                              |
| ------------------------------ | ------------------------------------------------- |
| `modules/shared/write-gate.md` | A write needs an explicit ask in the current turn |
| `modules/shared/notion-mcp.md` | Notion MCP bootstrap                              |

Collection IDs live in `03-identifiers.md` under `docs_root`.

## Section 5. After every run

Follow `~/.grok/docs/skill-system/README.md` Section 5. Publish the retrospective. Patch the owning file when a field or flag was wrong.

## Section 6. Adding work

Run The Algorithm in `docs/skill-system/README.md` Section 3 Item A before adding a file.

1. Question the requirement.
2. Delete a step when that removes the need for a new skill.
3. Edit the layer fill table or the module JSON map.
4. Leave the external context contract unchanged unless a Notion entity itself changed.
