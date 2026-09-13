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
    - 1_model_behavior/105_Accountability_Handling.md
    - 1_model_behavior/106_Default_Read_Only_and_Authorization.md
    - 1_model_behavior/111_Minimalist_Reporting_and_Verification.md
    - 2_context/201_Execute_Act_Predicates.md
adapters:
    grok: { surface: deny }
    claude: { surface: deny }
---

# External Write

- The execution face follows the external execute predicate defined in § 201 without inspecting working-tree content hashes. Execution ordering MUST follow § 105(f). Authorization boundaries MUST follow § 106. Post-execution reporting MUST follow § 111. During inter-step execution, § 109 and § 104(d) DO NOT apply.
- Destructive commands such as `git push --force` and `rm -rf` MUST never execute. Underlying permission layers MUST block those commands deterministically without failing open.
- Command evaluation follows an allow-list protocol:
    1. A read-only query command enumerated in `readonly_command_glob` MAY execute directly. Every other command prefixed with `git`, `glab`, `gh`, or `terraform` that does not appear in the allow list requires explicit authorization, regardless of whether the command appears in `command_glob`.
    2. Entries in `command_glob` serve exclusively to generate detailed rejection reasons and MUST NOT serve as the sole criterion for authorization.
    3. High-risk commands outside `git push --force` and `rm -rf` (such as `git fetch --prune`, `-p`, `git branch -D`, `-d`, and `-m`) are listed in `command_glob` for diagnostic identification. The allow list independently blocks unlisted mutating subcommands.
    4. Mutating operations MAY proceed only when the user prompt in the current turn includes an explicit execution phrase (such as `Approve`). The PreToolUse deny mechanism enforces this requirement, as implemented in `hooks/adapters/claude/gate-check.py`.
- Execution phrase retrieval branches by adapter platform:
    1. Claude Code environment: The Agent MUST proactively invoke `AskUserQuestion`, setting the approval option label to `Approve` alongside a `Deny` option. The question text MUST describe the pending action and whether the mutation is irreversible. Passively waiting for the user to type the phrase in conversational prose is prohibited. The selection from `AskUserQuestion` enters the transcript as a `tool_result`. The `extract_latest_user_prompt` function in `gate-check.py` aggregates all `tool_result` payloads within the current human turn, and the option label satisfies phrase verification directly. Conversational phrases such as 「去執行」, 「跑這個」, and 「請執行」 remain in `EXEC_PHRASES` for backward compatibility.
    2. Cursor environment: The PreToolUse hook in Cursor lacks a Claude-style `transcript_path`. When the current turn lacks an execution phrase, `gate-check.py` returns `permission: ask` for mutating `Shell` calls and listed GitLab or GitHub MCP write tools, delegating authorization to the native Cursor approval card. The Agent MUST NOT invoke `AskUserQuestion` to simulate execution phrases in Cursor.
- User instructions containing 「寫 X」, 「產出 X」, or 「準備 X」 MUST be interpreted as requests to draft text for review. Standard local file modifications remain outside this scenario.
