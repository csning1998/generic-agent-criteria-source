---
name: skill-commit-soc
effort: medium
description: >
    Fill batched git add and commit commands with Conventional Commit
    headers. Apply those commands only in the generic-agent-criteria-source
    tree. Elsewhere print the commands. Use when the owner asks to
    commit in SoC batches, or runs /skill-commit-soc.
metadata:
    short-description: "SoC git commits, grok-only apply"
---

# Commit SoC batches

Layer for local git write. This file owns batch grouping and commit headers.

## When to Use

The owner asked to commit current changes in separate concerns.

## Input Requirements

- Required: a git work tree.
- Optional: owner-named batches. When absent, this layer groups paths by concern.

Read `~/.grok/skills/modules/shared/write-gate.md`.

## Process

1. Read `git status` and `git diff --stat` in the work tree.
2. Group paths so each commit is one concern. Do not mix packaging, hook code, tests, CI, and docs in one commit.
3. Fill one header per batch. Format is `type(scope): description`. Total character count is less than 100. No body. Types follow `@commitlint/config-conventional`. Match existing headers in the repo log.
4. Set `execute` to true only when all of the following hold.
    1. The owner asked to commit in this turn.
    2. `git rev-parse --show-toplevel` is `$HOME/.grok`, or `origin` contains `generic-agent-criteria-source`.
5. Otherwise set `execute` to false.
6. Set `allow_push` to false always.
7. Write `/tmp/skill-commit-soc/<run>/input.json` with mode `0700`.
8. Call `~/.grok/skills/skill-module-git-commit/SKILL.md`.

Do not call `git push`. Do not ask the module to push.

## Output

Artifact `GitCommitResult` (same JSON as the module). When `execute` is false, report the printed commands for the owner to run.

## Validation Checklist

- [ ] Each commit message matches `type(scope): description` and is under 100 characters
- [ ] `allow_push` is false
- [ ] `execute` is true only for generic-agent-criteria-source after an ask in this turn
- [ ] `git push` was not invoked

## Backtrack Triggers

- Dirty index left from a failed commit: stop and report `git status`.
- Module `ok` false: report `error` and stop.

## Example

Owner says commit the Python split on this Grok tree. Layer fills one JSON batch list and the module runs `git add` plus `git commit` here. On another repo the same layer prints the commands instead.
