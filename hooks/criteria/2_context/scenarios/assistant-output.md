---
id: assistant-output
facets: [language]
enforce: [stop]
load:
    - 3_register/302_Vocabulary_Prohibitions.md
---

# Assistant Output

This scenario applies when an interaction turn concludes and the runtime harness provides a Stop hook. Grok, Claude Code, and Kimi Code provide a Stop event. Gemini CLI utilizes a custom end-of-turn event. Ollama does not provide a Stop hook.

## Section 1. Stop Hook Scan Targets

The Stop hook directly inspects the final message transmitted by the assistant. The hook evaluates the message against the following prohibited items:

- Emoji characters
- Em dash symbols (`U+2014`)
- Sycophantic conversational phrases, such as 「非常榮幸為您服務」

Upon detecting a violation, the hook MUST interrupt turn completion and MUST instruct the model to rewrite the violating section. Grok permits a maximum of eight retry attempts per turn.

## Section 2. Excluded Scope

Rare English vocabulary (such as `ameliorate` and associated synonyms) and tokens with high false-positive rates remain outside the real-time scanning scope of this hook. Static analysis linters evaluate those lexical checks prior to repository commit.

The complete index of prohibited vocabulary and symbols resides in `3_register/302_Vocabulary_Prohibitions.md`. Before the Stop hook is active, resident distill rules and § 302 strictly prohibit emoji and em dash characters.
