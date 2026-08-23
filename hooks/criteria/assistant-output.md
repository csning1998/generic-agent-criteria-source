---
id: assistant-output
facets: [language]
enforce: [stop]
load:
    - references/202_Vocabulary_Prohibitions.md
---

# Assistant output

This scenario applies when a turn ends and the harness still has a Stop hook. Grok, Claude Code, and Kimi Code have that event. Gemini CLI uses its own end-of-turn hook name. Ollama has none.

## Section 1. What the Stop hook will scan

The hook reads the assistant's last message (Grok field `lastAssistantMessage`, clipped at 32768 characters). It looks for a small, fixed set:

- emoji
- em dash (U+2014)
- fixed sycophancy strings, such as 「非常榮幸為您服務」

A hit blocks the stop and asks the model to rewrite that span. Grok allows at most 8 continuations per turn.

## Section 2. What this file does not scan

The English rare-word list (ameliorate and siblings) and high-false-positive tokens (我們, 優化) stay out of this hook. Those lists belong to Vale on files that enter git.

完整禁詞與符號表在 `references/202_Vocabulary_Prohibitions.md`。Stop hook 尚未實作。在接上之前，常駐 distill 與 §202 仍禁止 emoji 與 em dash。
