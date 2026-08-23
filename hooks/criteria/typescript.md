---
id: typescript
facets: [coding]
observables:
    path_glob: ["*.ts", "*.tsx"]
enforce: [gate_until_read]
load:
    - references/lang-ts.md
    - references/401-a-c_General_Coding_Standards.md
    - references/401-d_Comment_Standards.md
    - references/401-e-g_Style_and_Markings.md
    - references/401-h_Code_Comment_Decisions_and_Lifecycle.md
    - references/401-j-k_Secure_File_Editing_and_Identifier_Naming.md
adapters:
    claude: { surface: rules, paths: ["**/*.ts", "**/*.tsx"] }
    cursor: { surface: mdc, globs: "**/*.ts,**/*.tsx" }
    grok: { surface: gate_until_read }
    copilot: { surface: applyTo, glob: "**/*.{ts,tsx}" }
    gemini: { surface: skill, fallback: description }
    ollama: { surface: concat }
---

# TypeScript mutate

改 `.ts` 或 `.tsx` 之前，開啟 `references/lang-ts.md` 與 §401 的實作、註解、英文、命名檔（`401-a-c_General_Coding_Standards.md`、`401-d_Comment_Standards.md`、`401-e-g_Style_and_Markings.md`、`401-h_Code_Comment_Decisions_and_Lifecycle.md`、`401-j-k_Secure_File_Editing_and_Identifier_Naming.md`）。`401-d_Comment_Standards.md` 與 `401-h_Code_Comment_Decisions_and_Lifecycle.md` 服從 `401-e-g_Style_and_Markings.md`。Grok 先讀後寫的閘尚未實作。
