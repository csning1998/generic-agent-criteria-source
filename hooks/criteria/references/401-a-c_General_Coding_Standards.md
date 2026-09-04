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
