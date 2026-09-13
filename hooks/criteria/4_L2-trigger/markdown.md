# **§ 404(md). Markdown (`*.md`) Specific Standards**

> **CORE PRINCIPLE**：Markdown files MUST comply with markdownlint rules and structural fence boundaries.

## Section 1. Structural Heading and List Rules

- **(a) MD022 and MD032 Compliance**：
    - Exactly one blank line MUST precede and MUST follow each heading.
    - Exactly one blank line MUST precede the start of a list and MUST follow the end of a list.

- **(b) MD004 Marker Rule**：
    - An unordered list MUST use only the minus sign `-` as the list marker.
    - Mixing asterisks `*` or plus signs `+` is prohibited.
    - Exactly one space MUST follow the list marker before list item text begins.

- **(c) MD007 Indentation Rule**：
    - A nested list MUST use four spaces of indentation for each nesting level.
    - Two spaces and tab characters are prohibited for list indentation.

- **(d) MD009 and MD012 Spacing Rules**：
    - Consecutive blank lines in markdown documents MUST NOT exceed one blank line.
    - Trailing whitespace at the end of a line is prohibited.

- **(e) MD001 Heading Sequence**：
    - Heading levels MUST increase in sequence without skipping levels.
    - The deepest heading level is H4 (`####`). Deeper headings are prohibited.
    - H2 headings (`##`) MUST use consecutive Arabic numerals (for example `Section 1.`, `Section 2.`).
    - H3 headings (`###`) MUST pair an uppercase English letter with a type keyword (`Task`, `Option`, `Item`, or `Step`).
    - H4 headings (`####`) MUST inherit the type keyword of the parent H3 and append an Arabic numeral (for example `Task A.1`, `Step A.1`).

- **(f) Single H1 Constraint**：Each markdown document MUST contain at most one H1 heading.

## Section 2. Code Block and Fence Rules

- **(a) Language Declaration**：Every fenced code block MUST declare an explicit language identifier.

- **(b) Prohibition of Prose in Fences**：Expository prose inside a code block is prohibited.
