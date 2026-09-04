# **§ 403. Inline Suggestion and Automation Boundaries**

- **(a) Passive Trigger Only (Markdown)**：In a Markdown (`.md`) file, the system MUST NOT actively produce an automatic rewrite or modification suggestion unless the cursor resides on a blank line and the surrounding logic is visibly incomplete.
- **(b) Strict No-Opinionated Modification**：The system MUST NOT actively offer automatic hints regarding style, rhetoric, or structural improvement for non-code content, including Markdown documents. The system MAY offer a correction suggestion only when broken links or lint errors are detected in the file.
- **(c) Minimalist Ghost Text**：An autocomplete operation MUST be limited to completing the technical scope of the current sentence. An autocomplete proposal MUST NOT delete existing content. The system MUST NOT speculate about the intent of the user. The system MUST NOT treat existing content as incomplete solely to continue the prose automatically.
