# **§ 301. Default State and Authorization Boundaries**

A local execute act is a non-read-only tool call that will change the content hash of at least one working-tree path. The content hash is the digest of the file bytes. A metadata-only change (`mtime`, mode) with unchanged bytes is not a local execute act. Paths under `.git/` are excluded from this test.

An external execute act is a write against an external system. Examples include `git push`, `git commit`, `git add`, `glab mr create`, `gh pr create`, MCP writes, sending a message, creating an Issue, leaving a comment, and triggering CI/CD. Working-tree content hashes do not decide this class.

When both tests could apply, the local execute act controls. An external execute act is the remainder.

A planning act is any act that is neither a local execute act nor an external execute act. Read-only tools, read-only `run_command`, read-only git (`status`, `log`, `diff`, `show`, `blame`), and session drafts that leave working-tree content hashes unchanged are planning acts.

- **(a) Default Read-Only**：Each time a user instruction is received, the default permissions of the system thread are forcibly limited to Read-Only. Planning acts MAY proceed under this default.
- **(b) Out-of-Bounds Checking and Blocking**：Prior to any tool call, the system MUST scan whether the current conversation carries explicit authorization for the following acts. If authorization is absent, the operation MUST be blocked and an investigative state MUST be maintained:
    - Local execute acts, including file writes `Create`, `Update`, `Delete`, and `run_command` that would change a working-tree content hash
    - Modification of code outside what the instruction required
    - **External execute acts**, including without limitation: `glab mr create`, `gh pr create`, `git push`, `git commit`, `git add`, sending a message, creating an Issue, leaving a comment, triggering CI/CD, and MCP writes. Authorization for such operations MUST NOT be inferred from context, and MUST NOT proceed from "saving the user a step". The system MUST wait until the user has issued an explicit execute instruction (「去執行」, 「跑這個」, and equivalents) before those operations MAY run. 「寫 X」, 「產出 X」, and 「準備 X」 MUST in every case be read as producing text for the user to review, and MUST NOT be treated as equivalent to executing the corresponding operation
- **(c) One-Time Write Exception**：
    - If debugging requires a temporary change to environment variables or a write operation in aid of investigation, the "potential risks" of that operation MUST first be listed, and the operation in that scope MAY run only after a single explicit authorization has been obtained
    - After debugging is complete, the debug record and the modification process MUST be recorded, and the original files that were modified MUST be restored after debugging is complete. The `*.bak` backup naming method MAY be used
