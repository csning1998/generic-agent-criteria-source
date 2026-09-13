---
id: notebook
facets: [coding]
observables:
    path_glob: ["*.ipynb"]
enforce: [gate_until_read]
load:
    - 4_L2-trigger/ipynb.md
    - 3_register/304_Comment_Standards.md
    - 3_register/305_Style_and_Markings.md
adapters:
    claude: { surface: rules, paths: ["**/*.ipynb"] }
    grok: { surface: gate_until_read }
---

# Notebook

This scenario applies when interacting with `.ipynb` files. Direct modification of notebook files on disk is strictly prohibited. All demonstrations MUST be presented as literate programming within the conversation session.

General dialogue and planning follow the `reply` scenario. This scenario loads only Jupyter L2 criteria and cell comment standards.

## Section 1. Inherited Specifications

- Jupyter language-specific criteria: `4_L2-trigger/ipynb.md`
- Cell comment and text standards: `3_register/304_Comment_Standards.md` and `3_register/305_Style_and_Markings.md`
- Cursor glob dispatch: `languages.md` entry `notebook`

Inline suggestion and automation boundaries under § 112 govern model behavior and remain outside this scenario.

## Section 2. Jupyter-Specific Constraints

- Modifying `.ipynb` file bytes on disk is strictly prohibited.
- All presentation MUST follow literate programming practices within the conversation session.
- Complete Jupyter syntax and cell constraints reside in `4_L2-trigger/ipynb.md`.

Until the read-before-write gate in Grok is active, this scenario maintains the prohibition against writing to `.ipynb` files on disk.
