---
name: conventional-commit
description: >
    Draft Conventional Commit headers of the form type(scope): description.
    Use when the owner asks for a commit message, Conventional Commit, or /commit
    outside the skills-xai-supergrok SoC batch flow.
when-to-use: commit message, Conventional Commit, git commit
---

# Conventional Commit

The commit header format MUST follow `type(scope): description`. Commit types MUST conform to `@commitlint/config-conventional`. The header MUST state why the change was made in addition to what was changed. The header length SHOULD remain under 100 characters when required by repository convention.

Executing `git commit` or `git add` MUST NOT occur unless the owner explicitly requested execution in the current turn via an authorized phrase such as 「去執行」 or 「跑這個」. Executing `git push` is strictly prohibited.

SoC batched commits on the Grok home tree MUST remain in `~/.grok/skills/skill-commit-soc/`. This skill MUST NOT replace that layer.
