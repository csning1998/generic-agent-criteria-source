---
id: mr-review
facets: [behavior]
enforce: [skill]
skill: mr-review
load:
    - 2_context/203_Merge_Request_Review_Handling.md
---

# Merge Request Review Handling

This scenario governs the investigation, triage, and resolution of merge request review comments. Complete requirements reside in `2_context/203_Merge_Request_Review_Handling.md`. Operational procedures reside in `~/.agents/skills/mr-review/SKILL.md`.

This scenario is prompt-semantic (analogous to `commit` and `citation`). When the user requests investigation, classification, or resolution of MR review comments, this scenario and associated skills activate without relying on `path_glob`. Submitting a comment reply and resolving a discussion thread are distinct external operations. Each operation MUST receive explicit authorization from the user in the current turn.
