---
id: reply
facets: [behavior, language]
observables:
    always: true
enforce: [resident, stop]
load:
    - references/101_The_Helpful_Assistant_Mandate.md
    - references/102_MECE_Analytical_Requirement.md
    - references/201_Objective_and_Impersonal_Tone.md
    - references/202_Vocabulary_Prohibitions.md
    - references/203_Psychological_and_Conversational_Boundaries.md
    - references/204_Factual_and_Citation_Basis.md
    - references/205_Accountability_Handling.md
    - references/303_Mandatory_Halt_and_Review.md
    - references/304_Decision_Convergence_and_Paradigm_Resolution.md
    - references/402_Debug_Logs_and_Commit_Messages.md
skill: null
---

# Reply

規劃與對話。每一則回覆的語氣都適用。當回合若即將或正在進行 §301 的本地或外部執行，§304 與 §204(d) 不適用於步間回報，改走 `local-mutate` / `external-write` 與 §205(f)、§306。

完整條款在 `load:` 所列檔，刪減時改那些檔：

- TITLE I：`101`、`102`
- 對話與規劃：`201` 至 `204`、`303`、`304`。資訊蒐集與調查走 §204(d)
- 咎責：`205`（其中 (f) 只在執行情境生效）
- 除錯回覆：`402`

常駐 distill 仍是 `~/.agents/AGENTS.md` 的短句。Turn 結束後的符號掃描見 `assistant-output.md`。
