---
id: local-mutate
facets: [coding, behavior]
observables:
    tools: [search_replace, write]
    hash_mutate: working_tree
enforce: [gate_until_read]
load:
    - 1_model_behavior/105_Accountability_Handling.md
    - 1_model_behavior/111_Minimalist_Reporting_and_Verification.md
    - 2_context/201_Execute_Act_Predicates.md
---

# Local Mutate Scenario Specification

This scenario governs local execution acts which modify working-tree file bytes.

## Section 1. Scope and Predicate Evaluation

- This scenario evaluates strictly under the local execute predicate defined in § 201.
- Any non-read-only tool call that causes an actual modification to the content hash of a working-tree path triggers this scenario.
- Execution ordering MUST follow § 105(f). Authorization boundaries MUST follow § 106. Reporting MUST follow § 111.

## Section 2. Separation of Concerns and External Attachments

- Specific programming language rules are dispatched exclusively by `languages.md`. This scenario MUST NOT hold language-specific clauses.
- Test-driven development workflows are governed independently by `test-driven-development.md`. This scenario MUST NOT preload TDD clauses.
- Merge request and commit message formatting requirements are governed independently by `merge-request-compose.md` and `commit.md` via § 204.
