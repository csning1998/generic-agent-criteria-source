---
name: tdd-cycle
description: >
    Run a Test Driven Development cycle aligned to §307.
    Use when the owner or project declares TDD, when writing tests or
    production code under that declaration, or when the tdd scenario
    gate loads this skill.
when-to-use: TDD, red green, failing test first, tdd-cycle
---

# TDD cycle

Process aligns to `references/307_Test_Driven_Development.md`.

1. Write the automated test which expresses the missing behavior.
2. Run the automated test and confirm the test fails for that missing behavior.
3. Run every project linter which applies to the modified test files. Resolve every lint failure in the same step before presenting the failing test result.
4. Present the failing test output to the owner. Stop. Do not write production code for that behavior until the owner explicitly authorizes the green step in the same or a later turn.
5. After that authorization, write the minimal production change. Re run the minimal automated test set. Re run every applicable project linter. Report results under §306.

Hygiene work MUST be completed by the system. Asking the owner whether to fix a lint failure MUST NOT replace that fix. Mutations outside the authorized duty MUST NOT proceed.
