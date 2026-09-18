---
name: agent-ssot-discrepancies
status: temporary
updated: 2026-08-19
---

# Terminal agent SSoT discrepancies (draft)

Working note from 2026-08-19. Not an architecture adjudication. Delete or replace after the owner decides the SSoT layout.

Owner intent recorded in that session. Grok is the entity home for skills and for standing rules. Claude Code and Google Antigravity (agy) point at Grok. Ollama stays out of live sync.

## Section 1. Claims that match this machine

- `~/.claude/CLAUDE.md` is injected whole at Claude Code start. `~/.claude/lang_*.md` is opened only when the model follows § 404 in that file.
- Ollama `SYSTEM` is baked at `ollama create`. A later edit of a markdown rule file does not update a live model.
- `hooks/bin/engineering-principles.py` injects nothing on `SessionStart` and `UserPromptSubmit`. `hooks/principles/*.md` is opened by the model. `PreToolUse` denies by compiled regex on tool arguments.
- Claude Code can follow a symlink under `~/.claude/skills/` to another directory that holds `SKILL.md`.
- Grok `Stop` input includes `lastAssistantMessage`. The current `hooks/engineering-principles.json` does not register `Stop`. `PostToolUse` matches `Read` and `read_file` only.

## Section 2. Claims that conflict with this Grok Build

### Item A. Skills are not hardcoded in Grok CLI source

A web search mixed in `superagent-ai/grok-cli`. This install is Grok Build. Owner skills live at `~/.grok/skills/<name>/SKILL.md`. Discovery also scans `~/.claude/skills/` when Claude compatibility is on. Source is `docs/user-guide/08-skills.md`.

### Item B. Grok already has a global rules root

`$GROK_HOME/rules/` (default `~/.grok/rules/`) loads for every project. The standing file is `rules/ENGINEERING_PRINCIPLES.md`. Source is `docs/user-guide/12-project-rules.md`.

Putting § 101 through § 404 into that directory recreates the full-dump cost on Grok.

### Item C. Entity home is Grok, not `AGENTS.md` under `~/.claude`

An earlier Claude write-up put the body in `AGENTS.md` and had Grok consume Claude's home directory. That inverts the owner intent.

Entity paths for this design.

- Skills `~/.grok/skills/<name>/`
- Standing rules `~/.grok/rules/`
- Hard gates `hooks/bin/` plus `hooks/engineering-principles.json`
- Stack notes `hooks/principles/` (not session-injected)

Claude points at those paths (`@import` or symlink). Antigravity skill directories are split (`~/.gemini/config/skills/` and siblings). That split is unproven on this host.

### Item D. Shared hook process is not proven

Grok scans `~/.claude/settings.json` hooks as a compatibility source (`docs/user-guide/10-hooks.md`). Reusing `engineering-principles.py` as one binary is possible. Claude Code stdout and exit-code contract is not verified against `code.claude.com/docs/en/hooks` in this note.

## Section 3. Three enforcement layers (agreed in session)

1. `PreToolUse`. Structural rules on tool arguments. Regex. Deny before the call.
2. `PostToolUse` and `Stop`. Pattern rules on model-produced text (file body, commit message, assistant reply). Rewrite or block after the fact. This layer is incomplete on Grok today.
3. Skills. Rules that need task context and cannot be a closed pattern set. Description stays in context. Body loads when the task matches.

Disciplinary markdown still exists. It is not sufficient as context-only self-check. A hook must apply the same patterns at layer 2.

## Section 4. Load cost map on Grok today

| Surface              | Load                             | Role                                   |
| -------------------- | -------------------------------- | -------------------------------------- |
| `~/.grok/rules/*.md` | Every session                    | Short standing collaboration only      |
| `hooks/principles/`  | Model opens the file             | Stack notes. Missed open means no rule |
| `~/.grok/skills/`    | Description always. Body on task | Procedures and language or file norms  |
| `PreToolUse`         | Process                          | Argument deny                          |
| Assistant prose      | Almost none                      | Gap named in Section 3 item 2          |

## Section 5. Open checks

1. Claude Code `Stop` payload and whether it exposes the last assistant message.
2. Antigravity global skills path after a symlink from `~/.grok/skills/`.
3. Whether Sonar should be added to `generic-agent-criteria-source` `.gitlab-ci.yml`.

## Section 6. Tracked idempotency gaps

These remain open. A later apply can drift if they stay unclosed.

1. `evaluate_write` returns immediately when `is_self_path` is true. `~/.grok/terraform/` therefore skips the IaC write gate. A side-channel edit in that tree is not denied by PreToolUse.
2. `allow guest sql` still permits a mutating guest SQL command for the rest of the session. A second apply of the declared IaC can overwrite that guest repair. The phrase is an owner override, not a durable exception. Durable exceptions stay in `planning/decisions.md`.
