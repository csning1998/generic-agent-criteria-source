---
id: commit
facets: [behavior]
enforce: [skill]
skill: conventional-commit
load:
    - references/401-i_Scenario-Specific_Compliance_Requirements.md
    - references/401-h_Code_Comment_Decisions_and_Lifecycle.md
---

# Commit

Commit 產物。完整條款在 `references/401-i_Scenario-Specific_Compliance_Requirements.md`。執行步驟在 `~/.agents/skills/conventional-commit/SKILL.md`。除錯回覆不是本情境，走 `reply` 的 §402。

`401-h` 的 Prohibit WHAT 條款明文涵蓋「a session note about a code change」，commit body MUST 只寫 WHY，不得覆述 `git diff` 已經呈現的 WHAT。

Grok 家目錄的 SoC 分批 commit 仍用 `~/.grok/skills/skill-commit-soc/`。那層只在該樹執行。不要把它複製進 `~/.agents/skills/`。
