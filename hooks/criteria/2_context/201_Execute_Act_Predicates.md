# **§ 201. Execute Act Predicates**

- **(a) Predicate Definitions**：
    - A local execute act is a non-read-only tool call which alters the content hash of at least one working-tree path. The content hash is the digest of the file bytes. A metadata-only change (for example, modification time or file mode) with unchanged bytes is not a local execute act. File paths under `.git/` are excluded from this evaluation.
    - An external execute act is a write operation against an external system. Examples of an external execute act include `git push`, `git commit`, `git add`, `glab mr create`, `gh pr create`, Model Context Protocol (MCP) write operations, sending a message, creating an Issue, leaving a comment, and triggering CI/CD pipelines. Working-tree content hashes are not used to classify an external execute act.
    - When both a local execute act and an external execute act could apply to an operation, the local execute act controls. An external execute act is an operation which remains after local execute act evaluation.
    - A planning act is any operation which is neither a local execute act nor an external execute act. Read-only tool calls, read-only `run_command` executions, read-only Git operations (for example, `git status`, `git log`, `git diff`, `git show`, and `git blame`), and session drafts which leave working-tree content hashes unchanged are planning acts.
- **(b) Disambiguation of Request Verbs**：
    - User instructions containing 「寫 X」, 「產出 X」, or 「準備 X」 MUST in every case be interpreted as requests to generate text for user review.
    - User instructions containing 「寫 X」, 「產出 X」, or 「準備 X」 MUST NOT be treated as equivalent to executing the corresponding operational tool call.
- **(c) Read-Before-Write Invariant**：
    - Prior to executing a local execute act on an existing working-tree path, the system MUST inspect that path using a read tool in the current session.
    - The system MUST compute and record the content hash of the inspected path.
    - The system MUST NOT mutate an existing working-tree path whose on-disk content hash differs from the recorded inspection hash.
- **(d) Block Replacement Invariant**：
    - A local execute act on an existing working-tree path MUST use block replacement operations (`replace_file_content` or `multi_replace_file_content`).
    - Whole-file replacement of an existing working-tree path via `write_to_file` with `Overwrite: true` is strictly prohibited.
- **(e) Overwrite Leave Exemption**：
    - The constraint in clause (d) is lifted ONLY when the user prompt in the current turn explicitly contains the phrase `allow full overwrite`.
    - Authorization from a prior turn or metadata field MUST NOT satisfy this exemption.
