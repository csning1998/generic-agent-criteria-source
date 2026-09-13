---
id: commit
facets: [behavior]
enforce: [skill]
skill: conventional-commit
load:
    - 2_context/204_Scenario-Specific_Compliance_Requirements.md
    - 3_register/304_Comment_Standards.md
---

# Commit

This scenario governs Git commit artifacts. Complete requirements reside in `2_context/204_Scenario-Specific_Compliance_Requirements.md`. Operational procedures reside in `~/.agents/skills/conventional-commit/SKILL.md`. Dialogue replies during debugging remain outside this scenario and MUST follow § 205 under the `reply` scenario.

Under § 304(b), the prohibition against stating WHAT applies to all conversation logs and commit messages. The commit message body MUST record only WHY (architectural intent, known constraints, and design trade-offs). Restating WHAT `git diff` already displays is strictly prohibited.

Batched commit workflows under Grok home continue utilizing `~/.grok/skills/skill-commit-soc/`. That skill executes strictly within that directory tree and MUST NOT be duplicated into `~/.agents/skills/`.
