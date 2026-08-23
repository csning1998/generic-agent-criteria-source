---
id: notebook
facets: [coding]
observables:
    path_glob: ["*.ipynb"]
enforce: [gate_until_read]
load:
    - references/lang-ipynb.md
    - references/401-d_Comment_Standards.md
    - references/401-e-g_Style_and_Markings.md
    - references/401-h_Code_Comment_Decisions_and_Lifecycle.md
adapters:
    claude: { surface: rules, paths: ["**/*.ipynb"] }
    grok: { surface: gate_until_read }
---

# Notebook

碰 `.ipynb` 時適用。禁止改磁碟上的 notebook。以 Literature Programming 寫在 session。

對話與規劃走 `reply`（always）。本情境只載 Jupyter L2 與 cell 註解規則。不要把 TITLE I–III 再載一次。

## Section 1. Inheritance

- Jupyter L2：`lang-ipynb.md`
- Cell 註解產物：`401-d`、`401-e-g`、`401-h`

§403 是 IDE only，不在本情境。

## Section 2. Jupyter-only

- 不要改磁碟上的 `.ipynb`
- 以 Literature Programming 寫在 session
- 其餘 Jupyter L2 只在 `references/lang-ipynb.md`

Grok 先讀後寫的閘尚未實作。本情境仍禁止寫入 `.ipynb`。
