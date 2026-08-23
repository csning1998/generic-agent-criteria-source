# **§ 401(j)(k). Secure File Editing and Identifier Naming**

- **(j) Secure File Editing Protocols**：
    - When a file that the user has already edited in the same session is modified, a diff-based precise editing tool SHOULD be used first. Whole-file overwrite SHOULD be avoided
    - If whole-file overwrite cannot be avoided, the latest state MUST be confirmed prior to the write. Comments the user has already deleted MUST NOT be restored.
- **(k) Identifier Naming (Language-Agnostic)**：This clause applies to all programming languages (Go, TypeScript, JavaScript, Vue, Python, HCL, and equivalents) and is not limited to a single language. Colloquial preposition-suffix forms in function or variable names (e.g. `xFor`, `xOf`, `xFrom`) are prohibited. Verb-initial names SHOULD be adopted first (e.g. `resolveX`, `determineX`, `computeX`, `buildX`). Prior to adding an identifier, the verb convention of existing functions in the same file or the same module SHOULD first be inspected. An inconsistent name MUST NOT be created.
