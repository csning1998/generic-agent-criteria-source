# Criteria Routing Specification

This document defines the routing architecture of the criteria system. Global mandates, contextual scenarios, register requirements, and language-specific rules MUST remain decoupled across independent axes.

## Section 1. Directory Structure and Responsibilities

The criteria repository partitions all specifications across four mutually exclusive and collectively exhaustive (MECE) directories:

1. `1_model_behavior/`: Model behavior specifications (§ 101 through § 112). This directory defines identity disambiguation, analytical methodology, authorization boundaries, priority management, mandatory halt controls, and verification reporting. The system MUST adhere to these rules by default across all operations.
2. `2_context/`: Context and scenario specifications (§ 201 through § 205, the `scenarios/` directory, and the `domain/` directory). This directory defines task-specific triggers, skill invocations, semantic request disambiguation, and architectural domain principles. Operations include merge request authoring, review comment triage, commit generation, test-driven development, local mutation, and external writes. Architectural domain principles reside in `2_context/domain/`. Language path glob mappings reside in `2_context/scenarios/languages.md`.
3. `3_register/`: Register specifications (§ 301 through § 307). This directory defines dialogue register, vocabulary restrictions, general coding standards, code comment lifecycles, prose formatting, and language-agnostic identifier naming. These clauses dictate the professional tone and structural quality of all generated text.
4. `4_L2-trigger/`: Language-specific specifications (`golang.md`, `typescript.md`, `hcl.md`, `yaml.md`, `markdown.md`, and `ipynb.md`). A file in this directory MUST be loaded only when the matching file extension is detected according to `languages.md`.

## Section 2. Path Patterns and Language Dispatch (Item A. Mutate on Disk)

File path extensions which alter disk contents MUST be dispatched through `2_context/scenarios/languages.md` to the corresponding language specification in `4_L2-trigger/`. The matching register bundle from `3_register/` MUST attach according to the medium classification:

| Path Pattern                                                                            | Scenario ID | Medium Type | Inherited Specifications                                                                                                                                                                                            |
| --------------------------------------------------------------------------------------- | ----------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `*.md` `*.mdx`                                                                          | markdown    | prose       | `4_L2-trigger/markdown.md`, `3_register/305_Style_and_Markings.md`, `3_register/302_Vocabulary_Prohibitions.md`                                                                                                     |
| `*.ts` `*.tsx`                                                                          | typescript  | code        | `4_L2-trigger/typescript.md`, `3_register/303_General_Coding_Standards.md`, `3_register/304_Comment_Standards.md`, `3_register/306_Secure_File_Editing_and_Identifier_Naming.md`, `3_register/307_L2_Constraint.md` |
| `*.go`                                                                                  | go          | code        | `4_L2-trigger/golang.md`, `3_register/303_General_Coding_Standards.md`, `3_register/304_Comment_Standards.md`, `3_register/306_Secure_File_Editing_and_Identifier_Naming.md`, `3_register/307_L2_Constraint.md`     |
| `*.tf` `*.hcl` `*.tfvars` `*.tofu` `*.pkrvars.hcl`                                      | hcl         | code        | `4_L2-trigger/hcl.md`, `3_register/303_General_Coding_Standards.md`, `3_register/304_Comment_Standards.md`, `3_register/306_Secure_File_Editing_and_Identifier_Naming.md`, `3_register/307_L2_Constraint.md`        |
| `*.yaml` `*.yml` `*.j2`                                                                 | yaml        | code        | `4_L2-trigger/yaml.md`, `3_register/303_General_Coding_Standards.md`, `3_register/304_Comment_Standards.md`, `3_register/306_Secure_File_Editing_and_Identifier_Naming.md`, `3_register/307_L2_Constraint.md`       |
| `**/tests/**` `*_test.py` `*_test.go` `*.test.ts` `*.test.tsx` `*.spec.ts` `*.spec.tsx` | tdd         | test        | `2_context/202_Test_Driven_Development.md`, `1_model_behavior/111_Minimalist_Reporting_and_Verification.md`                                                                                                         |

Mutating disk bytes for Jupyter Notebook (`*.ipynb`) files is strictly prohibited. Jupyter Notebook interactions MUST follow `2_context/scenarios/notebook.md` and MUST appear as literate programming within the conversation session.

## Section 3. Prompt-Semantic Scenarios

The operational face MUST be partitioned using the predicates defined in § 201. A single turn MAY plan before executing. Planning replies MUST follow § 104(d) due diligence and § 109 recommendation convergence. When a local execute act or an external execute act triggers, the system MUST transition to § 105(f) execution order and § 111 minimalist reporting:

- Local execute: A non-read-only tool call which alters the working-tree content hash (digest of file bytes, excluding `.git/`). A metadata-only modification with unchanged bytes is not a local execute act.
- External execute: A write operation targeting an external system, including `git commit`, `git push`, merge request operations, MCP writes, outbound messages, issue creation, and CI pipeline triggers.
- When both a local execute act and an external execute act apply, the local execute act MUST take precedence.

| Triggering Context                                                | Operational Face | Scenario ID      | Enforcement Mechanism                         |
| ----------------------------------------------------------------- | ---------------- | ---------------- | --------------------------------------------- |
| Dialogue, proposal, architecture, accountability, read-only tools | planning         | reply            | Resident distill, stop mechanism              |
| The user halts execution or cites a dialogue violation            | planning         | reply (§ 108)    | Resident distill                              |
| Investigation and evidence extraction during debugging            | planning         | reply (§ 205)    | Resident distill                              |
| Working-tree content hash alteration (excluding `.git/`)          | execute          | local-mutate     | gate_until_read                               |
| git push, commit, add, glab, gh, MCP write                        | execute          | external-write   | Permission check, deny mechanism              |
| Conventional Commit artifact generation                           | execute          | commit           | Skill invocation (conventional-commit)        |
| Merge request or pull request description authoring               | execute          | mr               | Skill invocation (mr-template), gate_once     |
| Merge request review comment triage and investigation             | execute          | mr-review        | Skill invocation (mr-review)                  |
| Test-driven development test suite mutation                       | execute          | tdd              | Skill invocation (tdd-cycle), gate_until_read |
| Non-code text translation                                         | execute          | translate        | Skill invocation (translate)                  |
| Academic citation or external source verification                 | planning         | citation         | Skill invocation (citation)                   |
| Turn completion and assistant message inspection                  | planning         | assistant-output | Stop hook scan                                |

## Section 4. Full Criterion File Roster

Each specification file represents an authoritative, independent source. Duplication of full criterion text within scenario files is prohibited:

- `1_model_behavior/`:
    - `101_The_Helpful_Assistant_Mandate.md`
    - `102_MECE_Analytical_Requirement.md`
    - `103_Psychological_and_Conversational_Boundaries.md`
    - `104_Factual_and_Citation_Basis.md`
    - `105_Accountability_Handling.md`
    - `106_Default_Read_Only_and_Authorization.md`
    - `107_Response_Priority_and_Time_Management.md`
    - `108_Mandatory_Halt_and_Review.md`
    - `109_Decision_Convergence_and_Paradigm_Resolution.md`
    - `110_Non-Code_Operations.md`
    - `111_Minimalist_Reporting_and_Verification.md`
    - `112_Inline_Suggestion_and_Automation_Boundaries.md`
- `2_context/`:
    - `201_Execute_Act_Predicates.md`
    - `202_Test_Driven_Development.md`
    - `203_Merge_Request_Review_Handling.md`
    - `204_Scenario-Specific_Compliance_Requirements.md`
    - `205_Debug_Logs_and_Commit_Messages.md`
    - `scenarios/`: Contains eleven scenario files and `languages.md`
    - `domain/`: Contains `ENGINEERING_PRINCIPLES.md` and technology-stack architecture principles (`00-loading-protocol.md`, `40-identity-and-secrets.md`, `50-terraform.md`, `51-ansible.md`, `52-packer-vagrant.md`, `60-kubernetes-and-helm.md`, `61-container-runtime-and-selinux.md`, `62-service-mesh-and-network.md`, `70-cloud-providers.md`, `71-virtualization-onprem.md`, `80-stateful-and-quorum.md`, `90-gitops-and-observability.md`, `99-hook-contract.md`, and `SOURCES.md`)
- `3_register/`:
    - `301_Objective_and_Impersonal_Tone.md`
    - `302_Vocabulary_Prohibitions.md`
    - `303_General_Coding_Standards.md`
    - `304_Comment_Standards.md`
    - `305_Style_and_Markings.md`
    - `306_Secure_File_Editing_and_Identifier_Naming.md`
    - `307_L2_Constraint.md`
- `4_L2-trigger/`:
    - `golang.md`
    - `hcl.md`
    - `ipynb.md`
    - `markdown.md`
    - `typescript.md`
    - `yaml.md`
