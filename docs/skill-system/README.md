# Skill system

Agent reads this tree before writing or changing a `skill-*` or `skill-module-*` file.

The catalog is `~/.grok/contexts.toml`. The template is `config/contexts.example.toml`. One `[context.<id>]` table declares one external pack. One `[socket.<id>]` table names the pack and the layer skill. This tree records pack ids and socket ids. Pack repositories stay outside this tree. This tree is the skill writing contract. This tree is not a Notion locate path.

The Input, Output, Validation, and Backtrack section names come from ForceInjection `domain-driven-design-skills` under Apache License 2.0. Source repository: `https://github.com/ForceInjection/domain-driven-design-skills`. Copied English files live in `reference/`. The file map and APA list are in `reference/NOTICE.md`. Layer, module, `/tmp` payload, effort roles, and The Algorithm are owner work.

## Section 1. Where the files live

| Path                                             | Role                                                                                                                                                                   |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `~/.grok/docs/skill-system/`                     | Constraints Agent loads on every skill edit                                                                                                                            |
| `~/.grok/vendor/domain-driven-design-skills/`    | Git clone of `https://github.com/ForceInjection/domain-driven-design-skills` (commit `2f3b6b18becdd95a03f465059e4e9cffa3c7e170`). Not on the Grok skill discovery path |
| `reference/NOTICE.md`                            | Copyright notice, file map, and reference list                                                                                                                         |
| `reference/LICENSE`                              | Apache License 2.0 text from that repository                                                                                                                           |
| `reference/docs/ddd-skill-system-design.en.md`   | Upstream design document, section 1.3                                                                                                                                  |
| `reference/skills/interface-example.SKILL.en.md` | Copy of upstream `skills/ddd-contexts/SKILL.en.md`                                                                                                                     |

Do not copy `ddd-scope` through `ddd-openspec-bridge` into `~/.grok/skills/`. Those nine skills are a modeling pipeline. The owner already holds the model in an external context contract.

## Section 2. Interface taken from ForceInjection

A layer `SKILL.md` uses these sections. Source is `reference/docs/ddd-skill-system-design.en.md` section 1.3.

1. When to Use
2. Input Requirements (name the upstream skill that produced each artifact)
3. Process
4. Output (artifact name plus JSON structure)
5. Validation Checklist
6. Backtrack Triggers
7. Example

A later skill consumes a named artifact. The later skill does not reopen an upstream module to recompute a field.

## Section 3. Owner flavor

### Item A. The Algorithm

Apply these five steps in order on every change. Do not skip to a later step.

1. Question every requirement. Name who asked for the requirement in this workspace.
2. Delete any part or step that is not required.
3. Simplify what remains.
4. Accelerate cycle time.
5. Automate last.

A retrospective that lists five next patches has skipped step 2.

### Item B. Layer

A `skill-*` that calls module skills is a layer.

The layer owns variable names, fill rules, and the Notion (or later gRPC) property list. The layer collects each module JSON and builds the next module input.

Every layer `SKILL.md` MUST set frontmatter `effort` to `low`, `medium`, or `high`. That value is the spawn budget for delegated work. The parent GUI session may stay on high or extra high.

When spawning a child for that skill, map `effort` as follows.

| `effort` | `subagent_type`                                              |
| -------- | ------------------------------------------------------------ |
| `low`    | `exec-low`                                                   |
| `medium` | `exec-medium`                                                |
| `high`   | `general-purpose` only when the owner asked for a high child |

Do not spawn bare `general-purpose` for `low` or `medium`. That child inherits the parent extra-high budget. If `exec-low` fails a mapped call, respawn once as `exec-medium`.

### Item C. Module

- A module `SKILL.md` MUST set `effort: low`.
- A `skill-module-*` file receives JSON. The module maps that JSON onto one tool (yt-dlp, Buzz, Notion MCP, later an HTTP or gRPC client) and returns JSON.
- **A MODULE MUST BE ONLY STATELESS.**
    - The module MUST NOT bake collection IDs, group paths, mapping tables, or owner home paths into the module contract. Input examples use placeholders the layer replaces.
    - A module MUST NOT decide page property values, page content, or relation targets.
    - A module MUST NOT read a context contract to invent fill values.

### Item D. Isolation

If the Notion API changes, only the Notion module changes. yt-dlp and Buzz modules stay untouched.

If the owner later replaces Notion with a self-hosted API, only the write module changes. Layer fill tables stay.

## Section 4. Catalog handoff

A catalog socket names an external layer. The layer file stays outside this tree.

1. The layer calls modules in this tree and keeps each module artifact.
2. The layer writes one payload file under `/tmp/<socket id>/<id>/` with mode `0700`.
3. The layer sends `payload_path`. The module reads the file at `payload_path`. The module does not accept page fields inline. The agent MUST NOT paste payload fields into a tool call.

Do not paste payload field values into a `SKILL.md`.

## Section 5. After every run

After a layer or module run ends, success or fail, Agent MUST publish a retrospective in that turn. A green run still gets the block.

### Item A. Review

1. What ran. Name the layer, the modules, and the `/tmp/...` artifact directory.
2. Facts. Exit codes, CUDA, lookup hit or miss, page url, payload path.
3. Breaks and drift. Only what this run observed.
4. Next patch. Run The Algorithm. One owning file. Delete first.
5. Leave alone. What this run does not rewrite.

Write the review to `/tmp/<layer>/<id>/retrospective.json` when a `/tmp` run directory already exists.

### Item B. Write-back

When a run fails or the owner corrects a boundary, patch the file that owns the field in the same turn. Do not leave the lesson only in chat.

| Failure class      | Owning file                                |
| ------------------ | ------------------------------------------ |
| Wrong fill         | The layer skill                            |
| Wrong tool flags   | The module skill                           |
| Notion entity rule | the entity file under the pack `docs_root` |

## Section 6. Load order when editing skills

1. This file
2. `reference/NOTICE.md` when citing or copying upstream text
3. `reference/docs/ddd-skill-system-design.en.md` section 1.3
4. `~/.grok/skills/ARCHITECTURE.md`

## Section 7. References

ForceInjection. (2026). _Domain-driven design skills_ (Commit 2f3b6b18becdd95a03f465059e4e9cffa3c7e170) [Computer software]. GitHub. <https://github.com/ForceInjection/domain-driven-design-skills>

The complete file map is `reference/NOTICE.md`.
