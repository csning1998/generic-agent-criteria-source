# Python Function Naming Lexicon and Conventions

This document defines the normative lexicon and structural rules for function names across Python packages and test suites in this repository.

## Section 1. Leading Verb Operational Contract

Function names MUST use a leading verb without prepositional suffixes (§ 306). The leading verb determines the operational behavior, computational complexity, and side-effect expectations:

| Verb Category                   | Permitted Leading Verbs             | Operational Contract                                                                                                                                         | Prohibited Colloquial Verbs               |
| ------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------- |
| **Predicate (Boolean)**         | `is_`, `has_`, `matches_`, `are_`   | MUST return boolean (`True` or `False`). MUST NOT mutate state.                                                                                              | `check_`, `test_` (in prod), `flag_`      |
| **In-Memory Transformation**    | `extract_`, `compute_`, `derive_`   | Pure in-memory computation, extraction, or filtering. MUST NOT perform disk or network operations.                                                           | `get_`, `calc_`, `find_`                  |
| **Input Output Transformation** | `load_`, `parse_`, `render_`        | `load_` accesses disk or external data streams. `parse_` converts bytes or text to structured records. `render_` converts structured data to formatted text. | `read_`, `make_`, `build_`                |
| **Search / Resolution**         | `find_`, `resolve_`                 | `find_` returns matching element or `None`. `resolve_` calculates path/target with environmental or lookup state.                                            | `match_` (when returning item), `lookup_` |
| **State Mutation**              | `record_`, `persist_`, `reconcile_` | MUST perform deterministic state mutation on disk or shared memory.                                                                                          | `mark_`, `save_`, `do_`, `set_`           |
| **Diagnostics**                 | `inspect_`, `validate_`             | Evaluates adherence to specifications and returns structured drift tokens, findings, or raises validation errors.                                            | `check_`, `audit_`                        |
| **Policy Enforcement**          | `enforce_`, `require_`              | Enforces preconditions or policies by terminating execution or performing context injections on boundary violations.                                         | `gate_`, `ensure_` (when gating)          |
| **Event Hook**                  | `intercept_`, `dispatch_`           | Intercepts agent runtime lifecycle events or dispatches sub-handlers.                                                                                        | `handle_`, `process_`, `on_`              |

## Section 2. Test Function Naming Specification

Test functions MUST serve as executable specifications following the strict three-tier format:

```python
def test_<target_unit>_<condition_or_input>_<expected_behavior>(): ...
```

- `<target_unit>`: Exact normalized name of the function or component under test.
- `<condition_or_input>`: Precise setup, input state, or constraint.
- `<expected_behavior>`: Deterministic assertion outcome (`returns_...`, `aborts_without_mutation`, `raises_...`, `flags_violation`).
- Colloquial narrative terms (`happy_path`, `works`, `can_handle`, `fail`) are strictly prohibited in test function identifiers.
