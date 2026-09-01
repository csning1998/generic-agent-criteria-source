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
    - **(e) MD001 and Heading Sequence**：
        - Heading levels MUST increase in sequence. `####` is the only heading permitted under `###`. Skipping a level (e.g. `####` directly after `##`) is strictly prohibited. `#####` and deeper heading levels are prohibited. The deepest heading is H4, matching Notion Heading 4.
        - H2 headings (`##`) MUST use consecutive Arabic numerals (e.g. `Section 1.`, `Section 2.`).
        - H3 headings (`###`) MUST use an uppercase English letter paired with a type keyword. Technical documents and README-class files use `Task`, `Option`, or `Item` (e.g. `Task A.`, `Item A.`). Teaching and narrative files use `Step` (e.g. `Step A.`).
        - H4 headings (`####`) MUST inherit the type keyword of the parent H3 and MUST append an Arabic numeral (e.g. `Task A.1`, `Item A.1`, `Step A.1`).
    - **(f) Single H1 Limit**：Each Markdown file MAY contain only one H1 heading

3. Code Blocks & Fences
    - **(a) Language Declaration**：Every fenced code block MUST declare a language (for example `bash`, `yaml`, `json`). An unnamed triple-backtick block is prohibited
    - **(b) No Prose in Fences**：Expository prose inside a code block is prohibited. A code block MAY contain only executable code and standard comments
