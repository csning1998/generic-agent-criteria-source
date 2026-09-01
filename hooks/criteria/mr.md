---
id: mr
facets: [behavior]
enforce: [skill]
skill: mr-template
load:
    - references/401-i_Scenario-Specific_Compliance_Requirements.md
    - references/401-h_Code_Comment_Decisions_and_Lifecycle.md
---

# MR or PR body

完整條款在 `references/401-i_Scenario-Specific_Compliance_Requirements.md`（模板、Changes、Fixes）。執行步驟在 `~/.agents/skills/mr-template/SKILL.md`。先打開該 repository 的模板。

`401-h` 的 Prohibit WHAT 條款明文涵蓋「a session note about a code change」，Changes 段落每一條 MUST 只寫 WHY（設計動機、限制、取捨），不得覆述 `git diff` 已經呈現的 WHAT。
