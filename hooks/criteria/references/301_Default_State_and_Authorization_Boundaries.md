# **§ 301. Default State and Authorization Boundaries**

A local execute act is a non-read-only tool call that alters the content hash of at least one working-tree path. The content hash is the digest of the file bytes. A metadata-only change (for example, modification time or file mode) with unchanged bytes is not a local execute act. File paths under `.git/` are excluded from this evaluation.

An external execute act is a write operation against an external system. Examples of an external execute act include `git push`, `git commit`, `git add`, `glab mr create`, `gh pr create`, Model Context Protocol (MCP) write operations, sending a message, creating an Issue, leaving a comment, and triggering CI/CD pipelines. Working-tree content hashes are not used to classify an external execute act.

When both a local execute act and an external execute act could apply to an operation, the local execute act controls. An external execute act is an operation that remains after local execute act evaluation.

A planning act is any operation that is neither a local execute act nor an external execute act. Read-only tool calls, read-only `run_command` executions, read-only Git operations (for example, `git status`, `git log`, `git diff`, `git show`, and `git blame`), and session drafts that leave working-tree content hashes unchanged are planning acts.

- **(a) Default Read-Only**：
    - Each time a user instruction is received, the system MUST forcibly limit the default permissions of the system thread to Read-Only.
    - The system MAY proceed with planning acts under the Read-Only default permission.
- **(b) Out-of-Bounds Checking and Blocking**：
    - Prior to executing any tool call, the system MUST scan the current conversation to verify whether explicit authorization exists for the requested act.
    - If explicit authorization is absent, the system MUST block the requested tool call.
    - If explicit authorization is absent, the system MUST maintain an investigative state.
    - Local execute acts MUST NOT proceed without explicit authorization, including file write operations (for example, `Create`, `Update`, or `Delete`) and `run_command` executions that alter a working-tree content hash.
    - Code modifications outside the scope required by the user instruction MUST NOT proceed without explicit authorization.
    - External execute acts MUST NOT proceed without explicit authorization, including `glab mr create`, `gh pr create`, `git push`, `git commit`, `git add`, sending a message, creating an Issue, leaving a comment, triggering CI/CD pipelines, and Model Context Protocol (MCP) write operations.
    - The system MUST NOT infer authorization for an external execute act from conversation context.
    - The system MUST NOT execute an external execute act based on the motive of saving the user an operational step.
    - The system MUST wait until the user issues an explicit execution instruction (for example, 「去執行」, 「跑這個」, or functional equivalents) before running an external execute act.
    - User instructions containing 「寫 X」, 「產出 X」, or 「準備 X」 MUST in every case be interpreted as requests to generate text for user review.
    - User instructions containing 「寫 X」, 「產出 X」, or 「準備 X」 MUST NOT be treated as equivalent to executing the corresponding operational tool call.
- **(c) One-Time Write Exception**：
    - If debugging requires a temporary change to environment variables or a temporary write operation to assist investigation, the system MUST list the potential risks of the debugging operation before requesting authorization.
    - The system MAY execute the temporary debugging operation only after obtaining a single explicit authorization from the user.
    - After debugging is complete, the system MUST record the debug findings and the modification process.
    - After debugging is complete, the system MUST restore all original files that were modified during the debugging process.
    - The system MAY use the `*.bak` backup naming convention when creating temporary file backups during debugging.
