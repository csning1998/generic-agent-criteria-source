---
id: languages
entries:
    - id: typescript
      medium: code
      path_glob: ["*.ts", "*.tsx"]
      target: 4_L2-trigger/typescript.md
      cursor_globs: "**/*.ts,**/*.tsx"
      load:
          - 4_L2-trigger/typescript.md
          - 3_register/303_General_Coding_Standards.md
          - 3_register/304_Comment_Standards.md
          - 3_register/306_Secure_File_Editing_and_Identifier_Naming.md
          - 3_register/307_L2_Constraint.md
    - id: go
      medium: code
      path_glob: ["*.go"]
      target: 4_L2-trigger/golang.md
      cursor_globs: "**/*.go"
      load:
          - 4_L2-trigger/golang.md
          - 3_register/303_General_Coding_Standards.md
          - 3_register/304_Comment_Standards.md
          - 3_register/306_Secure_File_Editing_and_Identifier_Naming.md
          - 3_register/307_L2_Constraint.md
    - id: hcl
      medium: code
      path_glob: ["*.tf", "*.hcl", "*.tfvars", "*.tofu", "*.pkrvars.hcl"]
      target: 4_L2-trigger/hcl.md
      cursor_globs: "**/*.tf,**/*.hcl,**/*.tfvars,**/*.tofu,**/*.pkrvars.hcl"
      load:
          - 4_L2-trigger/hcl.md
          - 3_register/303_General_Coding_Standards.md
          - 3_register/304_Comment_Standards.md
          - 3_register/306_Secure_File_Editing_and_Identifier_Naming.md
          - 3_register/307_L2_Constraint.md
    - id: yaml
      medium: code
      path_glob: ["*.yaml", "*.yml", "*.j2"]
      target: 4_L2-trigger/yaml.md
      cursor_globs: "**/*.yaml,**/*.yml,**/*.j2"
      load:
          - 4_L2-trigger/yaml.md
          - 3_register/303_General_Coding_Standards.md
          - 3_register/304_Comment_Standards.md
          - 3_register/306_Secure_File_Editing_and_Identifier_Naming.md
          - 3_register/307_L2_Constraint.md
    - id: markdown
      medium: prose
      path_glob: ["*.md", "*.mdx"]
      target: 4_L2-trigger/markdown.md
      cursor_globs: "**/*.md,**/*.mdx"
      load:
          - 4_L2-trigger/markdown.md
          - 3_register/305_Style_and_Markings.md
          - 3_register/302_Vocabulary_Prohibitions.md
    - id: notebook
      medium: notebook
      cursor_globs: "**/*.ipynb"
      load:
          - 4_L2-trigger/ipynb.md
          - 3_register/304_Comment_Standards.md
          - 3_register/305_Style_and_Markings.md
---

# Programming Language Specification Table

This document defines the mapping between working-tree path extensions, language-specific criteria, and media register bundles.

## Section 1. Structure and Dispatch Principles

This lookup table serves as the authoritative source for dispatching specifications based on file extensions.

The system determines the language criteria from `4_L2-trigger/` and the register bundle from `3_register/` concurrently based on file path attributes.

## Section 2. Media Classification and Register Associations

Output media categories are mutually exclusive and collectively exhaustive. The three media classes are code media, prose media, and notebook media.

Code media covers TypeScript, Go, HCL, and YAML. When writing code media files, the system MUST load the matching language specification from `4_L2-trigger/` and MUST attach the general coding standards from `3_register/` (`303_General_Coding_Standards.md`, `304_Comment_Standards.md`, `306_Secure_File_Editing_and_Identifier_Naming.md`, and `307_L2_Constraint.md`).

Prose media covers Markdown. When writing prose media files, the system MUST load `4_L2-trigger/markdown.md` and MUST attach technical prose standards (`305_Style_and_Markings.md`). Prose media strictly excludes general coding standards from § 303.

Notebook media covers Jupyter Notebook files. When interacting with `*.ipynb` files, the system MUST load `4_L2-trigger/ipynb.md` and MUST attach `304_Comment_Standards.md` and `305_Style_and_Markings.md`. Notebook media MUST NOT attach general coding standards from § 303. Disk mutation of `*.ipynb` files is prohibited by `notebook.md`.

## Section 3. Language Dispatch Reference Roster

- TypeScript: Classified as code media. Matching path globs include `*.ts` and `*.tsx`. Target specification is `4_L2-trigger/typescript.md`. Cursor rule glob is `**/*.ts,**/*.tsx`.
- Go: Classified as code media. Matching path glob is `*.go`. Target specification is `4_L2-trigger/golang.md`. Cursor rule glob is `**/*.go`.
- HCL: Classified as code media. Matching path globs include `*.tf`, `*.hcl`, `*.tfvars`, `*.tofu`, and `*.pkrvars.hcl`. Target specification is `4_L2-trigger/hcl.md`. Cursor rule glob is `**/*.tf,**/*.hcl,**/*.tfvars,**/*.tofu,**/*.pkrvars.hcl`.
- YAML: Classified as code media. Matching path globs include `*.yaml`, `*.yml`, and `*.j2`. Target specification is `4_L2-trigger/yaml.md`. Cursor rule glob is `**/*.yaml,**/*.yml,**/*.j2`.
- Markdown: Classified as prose media. Matching path globs include `*.md` and `*.mdx`. Target specification is `4_L2-trigger/markdown.md`. Cursor rule glob is `**/*.md,**/*.mdx`.
- Notebook: Classified as notebook media. Cursor rule glob is `**/*.ipynb`. Task scenario body, enforce keys, and gate path globs remain in `notebook.md`.

## Section 4. Jupyter Notebook Dispatch

Jupyter Notebook files remain outside the code media class and outside the prose media class. Cursor glob dispatch for `*.ipynb` uses the `notebook` entry in this table. The `notebook` entry MUST NOT declare `path_glob` since Claude and Grok gate routing remains in `notebook.md`. Direct modification of `*.ipynb` file bytes is strictly prohibited.
