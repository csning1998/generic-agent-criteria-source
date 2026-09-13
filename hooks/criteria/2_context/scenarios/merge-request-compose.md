---
id: mr
facets: [behavior]
observables:
    path_glob: ["merge-request.md", "pull_request.md", "*MERGE_REQUEST*"]
    tools: [search_replace, write]
enforce: [skill, gate_once]
skill: mr-template
load:
    - 2_context/204_Scenario-Specific_Compliance_Requirements.md
    - 3_register/304_Comment_Standards.md
    - 3_register/305_Style_and_Markings.md
    - 4_L2-trigger/markdown.md
---

# Merge Request or Pull Request Description

Authoring an MR or PR description MUST satisfy template conformity, Changes definitions, and Fixes definitions specified in `2_context/204_Scenario-Specific_Compliance_Requirements.md`. Operational procedures reside in `~/.agents/skills/mr-template/SKILL.md`. Before modifying text, the existing repository template MUST be inspected. The summary body MUST comply with § 305(b) paragraph cohesion and single-event sentence rules, following the formatting requirements in `4_L2-trigger/markdown.md`.

Under § 304(b), the prohibition against describing WHAT applies to all conversation logs and submission documentation. Every entry in the Changes section MUST document only WHY (architectural rationale, system constraints, and design trade-offs). Restating WHAT `git diff` already displays is strictly prohibited.

Before writing to `merge-request.md`, the PreToolUse `gate_once` mechanism loads the criteria files enumerated in `load:`. The Agent MUST verify the text against applicable register clauses prior to submission.
