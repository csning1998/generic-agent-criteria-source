# **§ 403. Inline Suggestion & Automation Boundaries**

- **(a) Passive Trigger Only (Markdown)**：In `.md` files, unless the cursor is on a blank line and the surrounding logic is clearly incomplete, the system is strictly prohibited from actively producing any Rewrite or Modify automatic suggestion
- **(b) Strict No-Opinionated Modification**：Actively offering automatic hints about style, rhetoric, or structural improvement for non-code content (especially Markdown documents) is prohibited. The system MAY offer a correction suggestion only when Broken Links or Lint Errors are detected
- **(c) Minimalist Ghost Text**：Autocomplete MUST be limited to "technically completing the current sentence". Carrying any proposal that deletes existing content is strictly prohibited. Speculating about the user's intent, treating existing content as incomplete, and actively continuing the writing is also strictly prohibited
