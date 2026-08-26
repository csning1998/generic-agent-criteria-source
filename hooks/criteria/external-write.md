---
id: external-write
facets: [behavior]
observables:
    command_prefix: ["git ", "glab ", "gh ", "terraform "]
    command_glob:
        [
            "git push",
            "git commit",
            "git add",
            "git fetch --prune",
            "git fetch -p",
            "git branch -D",
            "git branch -d",
            "git branch --delete",
            "git branch -m",
            "git branch --move",
            "git tag -d",
            "git tag --delete",
            "git remote add",
            "git remote remove",
            "git remote rm",
            "git remote set-url",
            "git checkout",
            "git switch",
            "git merge",
            "git rebase",
            "git reset",
            "git clean",
            "git stash pop",
            "git stash apply",
            "git stash drop",
            "git cherry-pick",
            "git revert",
            "git rm",
            "git mv",
            "git submodule update",
            "git config --global",
            "git config --unset",
            "git gc",
            "glab mr create",
            "glab mr update",
            "glab mr merge",
            "glab mr note",
            "glab mr close",
            "glab mr approve",
            "glab mr checkout",
            "glab issue create",
            "glab issue close",
            "gh pr create",
            "gh pr merge",
            "gh pr comment",
            "gh pr close",
            "gh pr checkout",
            "gh pr review",
            "gh issue create",
            "gh issue close",
            "gh api -X",
            "gh repo delete",
            "glab api -X",
            "glab api --method",
            "terraform apply",
            "terraform destroy",
            "terraform import",
            "terraform taint",
            "terraform untaint",
            "terraform force-unlock",
            "terraform state mv",
            "terraform state rm",
            "terraform state push",
            "terraform state replace-provider",
            "terraform workspace new",
            "terraform workspace delete",
        ]
    readonly_command_glob:
        [
            "git status",
            "git log",
            "git diff",
            "git show",
            "git branch -a",
            "git branch -v",
            "git branch -l",
            "git branch --list",
            "git branch -r",
            "git branch --show-current",
            "git fetch",
            "git tag -l",
            "git tag --list",
            "git remote -v",
            "git remote show",
            "git blame",
            "git ls-tree",
            "git ls-files",
            "git rev-parse",
            "git describe",
            "git shortlog",
            "git reflog show",
            "git stash list",
            "git stash show",
            "git cat-file",
            "git grep",
            "git config --get",
            "git config -l",
            "git config --list",
            "git worktree list",
            "git branch --contains",
            "glab mr view",
            "glab mr list",
            "glab mr diff",
            "glab issue view",
            "glab issue list",
            "glab ci view",
            "glab ci status",
            "glab repo view",
            "glab api",
            "gh pr view",
            "gh pr list",
            "gh pr diff",
            "gh pr checks",
            "gh issue view",
            "gh issue list",
            "gh repo view",
            "gh api",
            "terraform init",
            "terraform plan",
            "terraform validate",
            "terraform show",
            "terraform output",
            "terraform providers",
            "terraform version",
            "terraform graph",
            "terraform console",
            "terraform state list",
            "terraform state show",
            "terraform workspace list",
            "terraform workspace show",
        ]
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

判斷標準採用白名單制：

1. `readonly_command_glob` 列出的唯讀查詢可直接執行，其餘任何 `git`／`glab`／`gh`／`terraform` 指令，只要不在該白名單內，一律視為需要授權，不論是否出現在 `command_glob`
2. `command_glob` 只用來在 deny 時給出更精確的理由文字，不是判斷是否需要授權的依據
3. `git push --force`、`rm -rf` 之外的高風險字面（`git fetch --prune`／`-p`、`git branch -D`／`-d`／`-m`）額外列在 `command_glob` 供訊息辨識，但白名單制本身已經足以擋下任何未列舉的新寫入子指令
4. 以上僅在當次 owner 提示含執行片語時才可執行（`Approve`）。那層是 PreToolUse deny，已在 `hooks/adapters/claude/gate-check.py` 實作。

取得執行片語的方式是 Agent 主動呼叫 `AskUserQuestion`，核准選項標籤固定使用 `Approve`（加一個 Deny 選項），問題本文陳述即將執行的動作與其是否不可逆。禁止被動等待 owner 自己在自由文字裡剛好打出那個片語。`AskUserQuestion` 的回答會以 `tool_result` 型態進入 transcript，`gate-check.py` 的 `last_user_message` 會把同一個人類回合內、下一則真人文字之前的所有 `tool_result` 都累積進來比對，選項標籤本身即滿足片語比對，不需要額外動作。`去執行`／`跑這個`／`請執行`／`執行吧` 這類自由文字仍在 `EXEC_PHRASES` 內作為向下相容的備援比對，不是主要流程。deny 訊息本身已經內嵌這個流程的指示，機制失效時仍以 deny 訊息文字為準。

「寫 X」「產出 X」「準備 X」只出文字供審閱。普通本機改檔不是本情境。
