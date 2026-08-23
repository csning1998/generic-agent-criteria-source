---
id: local-mutate
facets: [coding, behavior]
observables:
    tools: [search_replace, write]
    hash_mutate: working_tree
enforce: [gate_until_read]
load:
    - references/205_Accountability_Handling.md
    - references/301_Default_State_and_Authorization_Boundaries.md
    - references/306_Minimalist_Reporting_and_Verification.md
    - references/401-a-c_General_Coding_Standards.md
    - references/401-d_Comment_Standards.md
    - references/401-e-g_Style_and_Markings.md
    - references/401-h_Code_Comment_Decisions_and_Lifecycle.md
    - references/401-i_Scenario-Specific_Compliance_Requirements.md
    - references/401-j-k_Secure_File_Editing_and_Identifier_Naming.md
    - references/404_L2_Constraint.md
---

# Local mutate

執行面：§301 的本地執行謂詞。非唯讀工具呼叫，且至少一個工作樹路徑的內容 hash 將改變（不含 `.git/`）。`run_command` 若會改該 hash，屬本情境。指令順序 §205(f)，授權 §301，回報 §306。產物規則 §401 與 §404。§304 與 §204(d) 不適用於步間。除錯回覆走 `reply` 的 §402。§403 是 IDE only，不在本情境。

語言專屬規格（本機改檔）：

- Markdown：`markdown.md` 與 `references/lang-md.md`
- TypeScript：`typescript.md` 與 `references/lang-ts.md`
- HCL / Terraform：`hcl.md` 與 `references/lang-hcl.md`

`.ipynb` 不屬本情境。碰 notebook 時走 `notebook.md`。該情境禁止改磁碟，繼承鏈見該檔 `load:`。

普通本機改檔目前沒有 hook deny。副檔名先讀後寫的閘尚未實作。
