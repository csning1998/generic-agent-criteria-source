---
id: reply
facets: [behavior, language]
observables:
    always: true
enforce: [resident, stop]
load:
    - 1_model_behavior/101_The_Helpful_Assistant_Mandate.md
    - 1_model_behavior/102_MECE_Analytical_Requirement.md
    - 1_model_behavior/103_Psychological_and_Conversational_Boundaries.md
    - 1_model_behavior/104_Factual_and_Citation_Basis.md
    - 1_model_behavior/105_Accountability_Handling.md
    - 1_model_behavior/107_Response_Priority_and_Time_Management.md
    - 1_model_behavior/108_Mandatory_Halt_and_Review.md
    - 1_model_behavior/109_Decision_Convergence_and_Paradigm_Resolution.md
    - 2_context/205_Debug_Logs_and_Commit_Messages.md
    - 3_register/301_Objective_and_Impersonal_Tone.md
    - 3_register/302_Vocabulary_Prohibitions.md
skill: null
---

# Reply

This scenario governs planning and dialogue interactions. The register requirements apply to every reply transmitted by the system.

When a local execute act or an external execute act under § 201 is pending or in progress during the current turn, § 109 recommendation convergence and § 104(d) investigation rules DO NOT apply to inter-step reporting. Inter-step messaging is governed by `local-mutate`, `external-write`, § 105(f), and § 111.

## Section 1. Clause Mapping Roster

- Core behavior and analytical standards: `1_model_behavior/101_The_Helpful_Assistant_Mandate.md`, `102_MECE_Analytical_Requirement.md`, and `103_Psychological_and_Conversational_Boundaries.md`
- Factual and citation boundaries: `1_model_behavior/104_Factual_and_Citation_Basis.md` (investigation follows Item (d)), `107_Response_Priority_and_Time_Management.md`, `108_Mandatory_Halt_and_Review.md`, and `109_Decision_Convergence_and_Paradigm_Resolution.md`
- Accountability handling: `1_model_behavior/105_Accountability_Handling.md` (Item (f) applies during execution)
- Debugging dialogue: `2_context/205_Debug_Logs_and_Commit_Messages.md`
- Dialogue register standards: `3_register/301_Objective_and_Impersonal_Tone.md` and `302_Vocabulary_Prohibitions.md`

Standing distill rules reside in `AGENT_CRITERIA.md`. Post-turn symbol scanning rules reside in `assistant-output.md`.
