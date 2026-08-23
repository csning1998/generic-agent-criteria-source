---
id: external-write
facets: [behavior]
observables:
    command_glob: ["git push", "git commit", "git add", "glab mr", "gh pr"]
    external_mutate: true
enforce: [permission, deny]
load:
    - references/205_Accountability_Handling.md
    - references/301_Default_State_and_Authorization_Boundaries.md
    - references/306_Minimalist_Reporting_and_Verification.md
adapters:
    grok: { surface: deny }
    claude: { surface: deny }
---

# External write

執行面：§301 的外部執行謂詞。不看工作樹內容 hash。指令順序 §205(f)，授權 §301，回報 §306。§304 與 §204(d) 不適用於步間。

`git push --force` 與 `rm -rf` MUST never run。那些預定寫進 permission deny，該層不 fail open。

`git push`、`git commit`、`glab mr create`、`gh pr create`、以及 MCP 寫入，僅在當次 owner 提示含執行片語時才可跑（去執行、跑這個）。那層預定是 PreToolUse deny，尚未實作。

「寫 X」「產出 X」「準備 X」只出文字供審閱。普通本機改檔不是本情境。
