# Skills architecture

Read `~/.grok/docs/skill-system/README.md` before editing a skill. Upstream source and the reference list are `~/.grok/docs/skill-system/reference/NOTICE.md`.

A `skill-*` file is a layer. The layer fills JSON and owns field names. A `skill-module-*` file is stateless. The module receives JSON, maps that JSON onto one tool, and returns JSON. The module MUST NOT bake collection IDs, group paths, mapping tables, or owner home paths. A context contract is a catalog pack. Identifiers live in `03-identifiers.md` under that pack `docs_root`. The layer copies that ID. External layers are catalog sockets.

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

| Tier   | Kind   | Prefix          | Role                                                      |
| ------ | ------ | --------------- | --------------------------------------------------------- |
| Tier 1 | Meta   | `skill-meta-`   | Router, orchestrator, factory creator, artifact exporter. |
| Tier 2 | Layer  | `skill-layer-`  | Fill JSON. Sequence modules. Own destination fields.      |
| Tier 3 | Module | `skill-module-` | Stateless. Execute one tool. Return JSON.                 |

Frontmatter `effort` on each `SKILL.md` is the spawn budget. Roles live in `~/.grok/roles/`. `low` maps to `exec-low`. `medium` maps to `exec-medium`. Do not spawn bare `general-purpose` for those two values.

## Section 3. Contexts

### Item A. Media ingest

- Layers: `skill-layer-yt-dlp`, `skill-layer-buzz-transcribe`
- Modules: `skill-module-yt-dlp`, `skill-module-buzz-transcribe`, `skill-module-media-tags`
- Artifacts: `WatchMedia`, `TranscriptDone`, `MediaTags`

### Item B. Knowledge filing

- Modules: `skill-module-inspect-second-brain`, `skill-module-file-notion-resources`
- Artifacts: `SecondBrainLocate`, `NotionWriteResult`

External layers that call these modules are catalog sockets.

### Item C. Delivery

- Layers
    - `skill-layer-inspect-gitlab-mrs`
    - `skill-layer-apply-gitlab-mr-labels`
    - `skill-layer-review-gitlab-mr-comments`
- Modules
    - `skill-module-inspect-gitlab-mrs`
    - `skill-module-inspect-notion-tasks`
    - `skill-module-file-notion-resources`
    - `skill-module-gitlab-mr-labels`
    - `skill-module-gitlab-mr-discussions`
- Artifacts
    - `GitlabMrList`
    - `NotionTaskRows`
    - `GitlabMrLabelResult`
    - `GitlabMrCommentTriageResult`
    - `GitlabMrDiscussionsResult`

Task fill is catalog socket `task-fill`. The entity file sits under that pack `docs_root`. Label mapping tables live in `skill-layer-apply-gitlab-mr-labels`. Verdict evidence and the reply/resolve gate live in `skill-layer-review-gitlab-mr-comments`. `skill-layer-review-gitlab-mr-comments` hands SoC commit batching to `skill-layer-commit-soc`.

### Item D. Workspace

- Modules: `skill-module-drive-para`, `skill-module-local-gtd`
- Artifacts: `DriveCensus`, `LocalGtdResult`, `WorkspaceCensus`

An external census layer is a catalog socket.

### Item E. Tooling

- Layers: `skill-layer-update-antigravity`, `skill-layer-commit-soc`
- Modules: `skill-module-update-antigravity`, `skill-module-git-commit`
- Artifacts: `AntigravityResult`, `GitCommitResult`

`skill-layer-commit-soc` fills SoC commit batches. The module applies `git add` and `git commit` only when the layer sets `execute` true for generic-agent-criteria-source. The module never runs `git push`.

### Item F. Architecture documents

- Layers: `skill-layer-inspect-architecture-docs`, `skill-layer-update-architecture-docs`
- Modules: `skill-module-inspect-gitlab-mrs`
- Artifacts: `ArchitectureConflictReport`, `ArchitectureDocsUpdated`

Inspect is read-only. Update writes the planning tree after an ask. A merged merge request that the owner asked to archive calls catalog socket `task-fill`. Task fill stays on socket `task-fill` and in the entity file under that pack `docs_root`. These layers do not own Terraform DAG, security, test authoring, idempotency, or module-shape review.

### Item G. Meta engine and foundation

- Meta: `skill-meta-factory-creator`, `skill-meta-mcp-json`, `skill-meta-python-engine`
- Role: Universal agent operation protocols, MCP JSON fault-tolerant serialization, and sandbox deterministic Python compute engine.

### Item H. Intelligence and trend

- Modules: `skill-module-authority-search`, `skill-module-delta-comparator`, `skill-module-trend-style-normalizer`
- Role: Authoritative search recipes, baseline state diffing, and style and epistemic normalization.

### Item I. Calendar and scheduling

- Modules: `skill-module-google-calendar`
- Artifacts: `GoogleCalendarResult`

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
4. Leave a catalog pack unchanged unless a Notion entity itself changed.
