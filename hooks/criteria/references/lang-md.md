# **Markdown (`*.md`) Specific Standards**

> **CORE PRINCIPLE**: Output Markdown MUST comply 100% with markdownlint rules. AI-specific layout habits, meaningless tone marks, and symbol shortcuts are prohibited

1. Typography & Prose Strict Rules
    - **(a) Zero Dash Policy**：
        - The use of an Em dash (—), an En dash (–), or a fullwidth or halfwidth hyphen-minus (-) for supplementary explanation, a tone shift, or isolation of an aside is strictly prohibited
        - **Substitute**：Fullwidth parentheses `（）` MUST be used, or a comma MUST be used, or the text MUST be split into independent short sentences
    - **(b) Zero Arrow Policy**：
        - Any arrow symbol (e.g. `->`, `=>`, `-->`, `➔`, `➡️`) is strictly prohibited in prose and in lists. A zsh terminal text block is outside this limit. A math span delimited by `$` MAY contain arrow symbols. A fenced block whose language is `mermaid` MAY contain arrow symbols.
        - **Substitute**：Process order MUST use a standard ordered list (`1.`, `2.`) in every case. Cause, effect, or state transition MUST be written with full lexical words (for example 「進而導致」, 「轉換為」, 「接著」)
    - **(c) Prose Fluency**：
        - A parenthetical MUST remain a short supplement. A second independent sentence MUST be written as its own sentence. Use plain, compact American English with a clear subject-verb-object structure, or Traditional Chinese in Taiwan usage

2. Markdownlint Absolute Compliance
    - **(a) MD022/MD032**：
        - The line before and the line after each heading (`##`, `###`, `####`) MUST each leave "exactly one" blank line
        - The line before the start of a list and the line after the end of a list MUST each leave "one blank line" separating the list from the surrounding text
    - **(b) MD004**：
        - Unordered lists MAY use only the minus sign `-`. Mixing asterisks `*` or plus signs `+` is strictly prohibited
        - Exactly one space MUST follow the list marker before the text continues
    - **(c) MD007**：
        - Nested lists MUST use "4 spaces" of indent in every case. The use of 2 spaces or Tab is strictly prohibited
    - **(d) MD012/MD009**：
        - Consecutive blank lines in the full text have an upper bound of 1 line. Two or more consecutive blank lines are strictly prohibited
        - Meaningless trailing whitespace at line ends is absolutely prohibited
    - **(e) MD001**：
        - Heading levels MUST increase in sequence. `####` is the only heading permitted under `###`. Skipping a level (e.g. `####` directly after `##`) is strictly prohibited. `#####` and deeper heading levels are prohibited. The deepest heading is H4, matching Notion Heading 4.

3. Code Blocks & Fences
    - **(a) Language Declaration**：Every fenced code block MUST declare a language (for example `bash`, `yaml`, `json`). An unnamed triple-backtick block is prohibited
    - **(b) No Prose in Fences**：Expository prose inside a code block is prohibited. A code block MAY contain only executable code and standard comments
