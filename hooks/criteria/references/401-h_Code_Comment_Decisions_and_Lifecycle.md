# **§ 401(h). Code Comment Decisions and Lifecycle**

- **(h) Code Comment Decisions and Lifecycle**：
    - **Default to No Comments**：A comment is permitted only when the source cannot express the design motive. Typical motives are a non-obvious architectural constraint, an edge case, or a trade-off.
    - **Prohibit WHAT**：A comment MUST NOT restate behavior that the source or `git diff` already shows. Labeling an obvious algorithm with its name (for example writing that a binary-tree walk is a binary-tree walk) is prohibited. A session note about a code change follows the same rule.
    - **WHY including trade-offs**：A comment MAY state only the design motive, the constraint, and the trade-off that selected the chosen path. Trade-off reasoning is WHY. Implementation steps are WHAT.
    - **Three-Line Limit and Migration**：Comment text has a hard upper bound of three lines. An explanation that exceeds three lines, or that describes the operation of the system as a whole, MUST be migrated in full to a narrative file or a runbook. A technical document and a code comment MUST NOT carry that explanation.
    - **Single Claim**：The comment MUST express a single claim. A trade-off MAY appear when it is that claim. A catalog of discarded designs is prohibited. Syntactic compliance follows `(f)`.
    - **Final Comment Language Conversion**：Temporary use of zh-TW during development is permitted. Prior to opening an MR or PR, all comments MUST be converted in full into English that complies with this clause. Residual Chinglish or colloquial expression is prohibited.
