---
id: go
facets: [coding]
observables:
    path_glob: ["*.go"]
enforce: [gate_until_read]
load:
    - references/lang-go.md
    - references/401-a-c_General_Coding_Standards.md
    - references/401-d_Comment_Standards.md
    - references/401-e-g_Style_and_Markings.md
    - references/401-h_Code_Comment_Decisions_and_Lifecycle.md
    - references/401-j-k_Secure_File_Editing_and_Identifier_Naming.md
adapters:
    claude: { surface: rules, paths: ["**/*.go"] }
    cursor: { surface: mdc, globs: "**/*.go" }
    grok: { surface: gate_until_read }
    copilot: { surface: applyTo, glob: "**/*.go" }
    gemini: { surface: skill, fallback: description }
    ollama: { surface: concat }
---

# Go mutate

改 `*.go`（含 `_test.go`）之前，開啟 `references/lang-go.md` 與 §401 的實作、註解、英文、命名檔（`401-a-c_General_Coding_Standards.md`、`401-d_Comment_Standards.md`、`401-e-g_Style_and_Markings.md`、`401-h_Code_Comment_Decisions_and_Lifecycle.md`、`401-j-k_Secure_File_Editing_and_Identifier_Naming.md`）。`401-d_Comment_Standards.md` 與 `401-h_Code_Comment_Decisions_and_Lifecycle.md` 服從 `401-e-g_Style_and_Markings.md`。Grok 先讀後寫的閘尚未實作。
