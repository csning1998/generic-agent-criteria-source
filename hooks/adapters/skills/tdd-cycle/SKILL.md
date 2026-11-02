---
name: tdd-cycle
description: >
    Run a Test Driven Development cycle aligned to § 202.
    Use when the owner or project declares TDD, when writing tests or
    production code under that declaration, or when the tdd scenario
    gate loads this skill.
when-to-use: TDD, red green, failing test first, tdd-cycle
---

# TDD cycle

Process aligns to `2_context/202_Test_Driven_Development.md`.

1. Establish the minimal function shells, type signatures, and stub exports necessary for test compilation and module resolution.
2. Write the automated test which expresses the missing behavior.
3. Run the automated test and confirm the test fails with a logical assertion error rather than a compilation or missing module error.
4. Run every project linter and static typecheck which applies to the modified test and stub files. Resolve every failure in the same step before presenting the failing test result.
5. Present the failing assertion test output to the owner. Stop. Do not write production code for that behavior until the owner explicitly authorizes the green step in the same or a later turn.
6. After that authorization, write the minimal production change to satisfy the assertions. Re run the minimal automated test set. Re run every applicable project linter. Report results under § 111.

Hygiene work MUST be completed by the system. Asking the owner whether to fix a lint failure MUST NOT replace that fix. Mutations outside the authorized duty MUST NOT proceed.
