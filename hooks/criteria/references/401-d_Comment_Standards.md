# **§ 401(d). Comment Standards**

- **(d) Comment Standards**：
    - `# texts` MUST be used in every case. Isolation lines such as `# ====` or `# ----` are strictly prohibited. Punctuation and symbol limits follow `(g)`
    - Minimal-amplitude comments MUST be observed. Comments are responsible only for pointing out non-obvious architectural reasons, boundaries, limits, or trade-offs. Content rules follow `(h)`. Restating WHAT the source or `git diff` already shows is prohibited. Synonymous repetition and causal redundancy are strictly prohibited
    - Anthropomorphic, subjectively emotional, or non-engineering-quantified adjectives applied to system behavior are strictly prohibited. Function and state wording MUST be an objective description of system behavior. That diction rule MUST NOT become a restatement of WHAT the code does
    - Community slang, colloquial abbreviations, and vague reference are fully prohibited. All architectural descriptions and operational acts MUST stay in strong alignment with the official-documentation terminology of that technology stack
    - Restating a necessary result inside a single comment by utilizing "so" in an overly colloquial way is prohibited
    - English syntactic structure, preposition placement, and word-frequency limits follow `(e)` and `(f)` in every case
    - If an out-of-scope and necessary correction arises because of a code change, it MAY be stated only in the conversation session. Writing it into a codebase comment is prohibited
