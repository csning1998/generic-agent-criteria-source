---
id: tdd
facets: [coding, behavior]
observables:
    path_glob:
        - "**/tests/**"
        - "*_test.py"
        - "*_test.go"
        - "*.test.ts"
        - "*.test.tsx"
        - "*.spec.ts"
        - "*.spec.tsx"
    tools: [search_replace, write]
enforce: [skill, gate_until_read]
skill: tdd-cycle
load:
    - 1_model_behavior/111_Minimalist_Reporting_and_Verification.md
    - 2_context/202_Test_Driven_Development.md
---

# Test-Driven Development

This scenario governs test-driven development (TDD) mutation across test paths. Complete requirements reside in `2_context/202_Test_Driven_Development.md`. Operational procedures reside in `~/.agents/skills/tdd-cycle/SKILL.md`. Minimalist reporting and verification mechanisms follow `1_model_behavior/111_Minimalist_Reporting_and_Verification.md`.

When a mutating tool call first matches a test path pattern, the pre-check gate loads the specifications and skill instructions listed in `load:`.
