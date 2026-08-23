# Criteria routing

Grok does not load this file at session start. Open it when a task hits more than one scenario, or when the distill table is not enough.

## Section 1. Path to spec

副檔名各自有繼承鏈。不要把 `*.ipynb` 與改磁碟的語言列成同一組。

### Item A. Mutate on disk

| Path glob                                          | Scenario id | Inherits                                                                                                                                                                                                                     |
| -------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `*.md` `*.mdx`                                     | markdown    | `lang-md.md`、`401-e-g_Style_and_Markings.md`、`202_Vocabulary_Prohibitions.md`                                                                                                                                              |
| `*.ts` `*.tsx`                                     | typescript  | `lang-ts.md`、`401-a-c_General_Coding_Standards.md`、`401-d_Comment_Standards.md`、`401-e-g_Style_and_Markings.md`、`401-h_Code_Comment_Decisions_and_Lifecycle.md`、`401-j-k_Secure_File_Editing_and_Identifier_Naming.md`  |
| `*.tf` `*.hcl` `*.tfvars` `*.tofu` `*.pkrvars.hcl` | hcl         | `lang-hcl.md`、`401-a-c_General_Coding_Standards.md`、`401-d_Comment_Standards.md`、`401-e-g_Style_and_Markings.md`、`401-h_Code_Comment_Decisions_and_Lifecycle.md`、`401-j-k_Secure_File_Editing_and_Identifier_Naming.md` |
| `terraform/modules/**` `ansible/roles/utils_*`     | (IaC hook)  | `~/.grok/hooks/principles/` via ENGINEERING_PRINCIPLES                                                                                                                                                                       |

全文在 `references/` 與 IaC hook。情境檔用 `load:` 繼承，不抄父正文。

### Item B. Notebook session

碰 `*.ipynb` 走 `notebook`。禁止改磁碟。以 Literature Programming 寫在 session。對話走 `reply`。本情境 `load:` 只有 `lang-ipynb.md` 與 cell 註解產物。

## Section 2. Prompt-semantic scenarios

面由 §301 的謂詞切。同一回合可以先規劃再執行。規劃階段走 §204(d) 與 §304。一旦本地或外部執行謂詞成立，改走 §205(f) 與 §306。

本地執行：非唯讀工具呼叫，且至少一個工作樹路徑的內容 hash（檔案位元組 digest）將改變。不含 `.git/`。`mtime`／mode 且位元組不變，不算。

外部執行：對外部系統的寫入（`git commit`、`git push`、MR、MCP、訊息、Issue、CI）。不看工作樹 hash。兩條都成立時，本地執行優先。

| When                                                              | Face     | Scenario id      | Enforce          |
| ----------------------------------------------------------------- | -------- | ---------------- | ---------------- |
| Dialogue, proposal, architecture, Accountability, read-only tools | planning | reply            | resident, stop   |
| User stops the system or names a dialogue violation               | planning | reply (§303)     | resident         |
| Debugging in the reply                                            | planning | reply (§402)     | resident         |
| Working-tree content hash will change (`.git/` excluded)          | execute  | local-mutate     | gate_until_read  |
| git push, git commit, git add, glab, gh MR, MCP write             | execute  | external-write   | permission, deny |
| Conventional commit artifact                                      | execute  | commit           | skill            |
| MR or PR body                                                     | execute  | mr               | skill            |
| Translation                                                       | execute  | translate        | skill            |
| APA or citations                                                  | planning | citation         | skill            |
| Assistant finished a turn                                         | planning | assistant-output | stop             |

§304 與 §204(d) 只在 planning。§205(f) 與 §306 只在 execute。`reply` 仍載 `205` 全文，(f) 的適用句把自己關在 execute。語氣 §201(b)(c) 在步間回報仍適用。

## Section 3. What is not wired yet

Resident distill, skill bodies, and the Claude thin shell are materialized by `hooks/bin/install-adapters.py`. Claude `.claude/rules`, Cursor `.mdc` files, and the Grok PreToolUse language gate are outside that installer. Those three adapters are not installed yet:

- Claude Code `.claude/rules/*.md` with `paths:` globs
- Cursor `.mdc` with `globs`
- Grok PreToolUse that denies a write until the matching spec was `read_file` this session

Until those exist, the executing Agent still opens the matching scenario file in Section 1 and the files listed in its `load:`, and does not preload unrelated scenarios.

## Section 4. Full criterion files

CLAUDE.md 按 TITLE 再按 `§` 切開，正文 1:1。刪減時改對應 `§` 檔。常駐 distill 不載入它們。子情境以 `load:` 繼承，禁止把條款全文抄進情境檔。§401 過肥，依連續字母再切，對齊 Item H 的 facet。

| File                                                                                                  | Clauses                                          |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| `101_The_Helpful_Assistant_Mandate.md` `102_MECE_Analytical_Requirement.md`                           | TITLE I                                          |
| `201_Objective_and_Impersonal_Tone.md` to `205_Accountability_Handling.md`                            | TITLE II                                         |
| `301_Default_State_and_Authorization_Boundaries.md` to `306_Minimalist_Reporting_and_Verification.md` | TITLE III                                        |
| `401-a-c_General_Coding_Standards.md`                                                                 | §401(a)(b)(c)                                    |
| `401-d_Comment_Standards.md`                                                                          | §401(d)                                          |
| `401-e-g_Style_and_Markings.md`                                                                       | §401(e)(f)(g)                                    |
| `401-h_Code_Comment_Decisions_and_Lifecycle.md`                                                       | §401(h)                                          |
| `401-i_Scenario-Specific_Compliance_Requirements.md`                                                  | §401(i)                                          |
| `401-j-k_Secure_File_Editing_and_Identifier_Naming.md`                                                | §401(j)(k)                                       |
| `402_Debug_Logs_and_Commit_Messages.md`                                                               | §402 debug replies. Commit artifacts are §401(i) |
| `403_Inline_Suggestion_and_Automation_Boundaries.md`                                                  | §403 IDE only                                    |
| `404_L2_Constraint.md`                                                                                | §404                                             |
| `lang-*.md`                                                                                           | Language-specific L2                             |
