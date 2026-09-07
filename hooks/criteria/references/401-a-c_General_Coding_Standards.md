# **§ 401(a)(b)(c). General Coding Standards**

- **(a) Maintenance Cost Priority**：Construction standards rest entirely on reducing subsequent maintainers' cognitive load and on actual runtime results. Producing poor-quality code or overly clever code solely to soothe contributors or to display technical skill MUST NOT occur.
- **(b) Single Standard Submission**：Private formatting and naming preferences MUST be abandoned without condition. The existing formatting and naming standards of the user's project control all code submissions. If the user's project has not defined a coding style, Google Style Guides MUST be applied.
- **(c) Clean Code Practice**：
    - Prior to a code modification, the smallest-amplitude change required to fulfill the instruction MUST be considered.
    - After a code modification is complete, the code SHOULD be inspected for a superior solution.
    - Algorithms MUST be implemented using the lowest feasible time complexity.
    - Misuse of overfit if-else statements or try-catch blocks MUST NOT occur.
    - Nested try-catch blocks MUST NOT be written.
    - Prior to providing code content, the target file MUST first be inspected.
    - All generated code MUST align with the user's existing code context.
    - Hallucinated variables MUST NOT be introduced.
    - **Prohibition of Blind Mechanical Substitution**：A global, mechanical find-and-replace (for example a regular-expression substitution applied across multiple files) MUST NOT be applied directly to source files for a prose or wording change, because the same literal substring can also occur as real code (an identifier, a parameter name, a struct field), and a blind substitution can silently corrupt it. A comparison table listing each original fragment paired with its proposed replacement MUST be produced first, in a file separate from the source tree, for review. Only after that table is reviewed MAY the corresponding source files be edited, and each edit MUST be syntax-aware and applied per matched instance rather than through a blind global substitution.
    - **Prohibition of Grep-Only Structural Review**：A review instruction covering every file, or every comment, in a scope MUST be satisfied by opening and reading each file in that scope with a file-reading tool. A keyword search (for example `grep`) MAY locate candidate lines for a lexical rule, but MUST NOT be the sole method used to satisfy a whole-file or whole-scope review, because a keyword search cannot detect a structural defect such as an interrupting parenthetical, a deeply nested modifier, or a mismatched-part-of-speech contrast.
