---
id: hcl
facets: [coding]
observables:
    path_glob: ["*.tf", "*.hcl", "*.tfvars", "*.tofu", "*.pkrvars.hcl"]
enforce: [gate_until_read]
load:
    - references/lang-hcl.md
    - references/401-a-c_General_Coding_Standards.md
    - references/401-d_Comment_Standards.md
    - references/401-e-g_Style_and_Markings.md
    - references/401-h_Code_Comment_Decisions_and_Lifecycle.md
    - references/401-j-k_Secure_File_Editing_and_Identifier_Naming.md
adapters:
    claude: { surface: rules, paths: ["**/*.tf", "**/*.hcl", "**/*.tfvars"] }
    cursor: { surface: mdc, globs: "**/*.tf,**/*.hcl,**/*.tfvars,**/*.tofu,**/*.pkrvars.hcl" }
    grok: { surface: gate_until_read }
---

# HCL mutate

改 `*.tf` / `*.hcl` / `*.tfvars` / `*.tofu` 之前，開啟：

- `references/lang-hcl.md`（HCL 專屬）
- §401 實作、註解、英文、命名：`401-a-c_General_Coding_Standards.md`、`401-d_Comment_Standards.md`、`401-e-g_Style_and_Markings.md`、`401-h_Code_Comment_Decisions_and_Lifecycle.md`、`401-j-k_Secure_File_Editing_and_Identifier_Naming.md`

共用模組 leave、planning 先讀、guest SQL 仍由既有 IaC hook（`engineering_principles.evaluate`）處理。不要在本檔重做那些檢查。Grok 先讀後寫的閘尚未實作。
