---
id: markdown
facets: [language, behavior]
observables:
    path_glob: ["*.md", "*.mdx"]
    tools: [search_replace, write]
enforce: [gate_until_read, deny, vale]
load:
    - references/lang-md.md
    - references/401-e-g_Style_and_Markings.md
    - references/202_Vocabulary_Prohibitions.md
adapters:
    claude: { surface: rules, paths: ["**/*.md", "**/*.mdx"] }
    cursor: { surface: mdc, globs: "**/*.md,**/*.mdx" }
    grok: { surface: gate_until_read }
    gemini: { surface: skill, fallback: description }
    ollama: { surface: concat }
---

# Markdown mutate

改 `.md` 或 `.mdx` 之前，開啟：

- `references/lang-md.md`（markdownlint、零 dash、零箭頭；數學與 mermaid 例外；最深 H4）
- `references/401-e-g_Style_and_Markings.md`（§401(e)(f)(g) 英文與排版）
- `references/202_Vocabulary_Prohibitions.md`（禁詞與符號）。對話語氣走 `reply` 的 §201。

Grok 尚未對「沒讀過就寫」做 PreToolUse deny。進 git 的 markdown 尚未接 Vale。在那些閘接上之前，模型仍必須開啟上列規格並遵守。
