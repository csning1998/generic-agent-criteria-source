# Generic Agent Criteria Source

This repository serves as the Single Source of Truth for agent behavior rules, contextual scenarios, engineering register standards, and technology domain principles. The repository materializes these specifications into runtime environments across multiple agent hosts, including Claude Code, Cursor, Gemini, and Grok.

```mermaid
graph TD
    SSOT[generic-agent-criteria-source] --> AXIS1["1_model_behavior<br/>Global Invariants: § 101 - § 112"]
    SSOT --> AXIS2["2_context<br/>Task Scenarios and Domain Principles"]
    SSOT --> AXIS3["3_register<br/>Register and Technical Style: § 301 - § 307"]
    SSOT --> AXIS4["4_L2-trigger<br/>Language-Specific Rules"]

    AXIS2 --> CONTEXT_CORE["§ 201 - § 205: Execution Predicates and Scenarios"]
    AXIS2 --> DOMAIN["2_context/domain/<br/>Architecture Principles: 40-Secrets to 99-Contract"]
    AXIS2 --> SCENARIOS["2_context/scenarios/<br/>Task Scenarios and languages.md Dispatch Table"]

    SCENARIOS -.->|"Path Glob and Extension"| AXIS4
    AXIS3 -.->|"Medium Classification"| AXIS4
```

## Section 0. Operational Commands and Verification

### Item A. Adapter Status Inspection and Materialization

The installer operates in read-only inspection mode by default. Materializing files requires the explicit `apply` verb:

1. **Inspect adapter status without modifying state**

    ```bash
    uv run python hooks/bin/install-adapters.py check
    ```

2. **Materialize and reconcile allow-listed adapter files**

    ```bash
    uv run python hooks/bin/install-adapters.py apply
    ```

### Item B. Test Execution

The test suite validates adapter synchronization, scenario parsing, hook gate decisions, and register scanning. Execute unit and integration tests by:

```bash
.venv/bin/pytest -v
```

### Item C. Static Analysis and Linting

Code modifications across Python modules and test files must comply with project formatting and import order constraints. Verify Python source compliance by:

```bash
ruff check .
```

## Section 1. Four-Axis Criteria Architecture

The criteria system decouples requirements across four mutually exclusive and collectively exhaustive directories. Global mandates remain active across all operational phases. Task scenarios, register constraints, and language rules activate conditionally upon matching operational context.

1. `1_model_behavior/`: Global behavioral invariants (§ 101 through § 112). These clauses govern identity disambiguation, MECE analytical standards, default read-only boundaries, priority queues, immediate halt controls, and minimalist verification reporting. Every agent execution MUST adhere to these rules by default.
2. `2_context/`: Contextual task scenarios and engineering domain principles (§ 201 through § 205, `scenarios/`, and `domain/`). These clauses define operational predicates, Test-Driven Development lifecycles, Merge Request authoring, Conventional Commit generation, and technology domain guidelines.
3. `3_register/`: Professional register and syntax specifications (§ 301 through § 307). These clauses define impersonal tone, vocabulary prohibitions, general coding standards, code comment limits, and RFC 7322 / ISO/IEC Directives Part 2 prose structures.
4. `4_L2-trigger/`: Programming language-specific constraints (`golang.md`, `typescript.md`, `hcl.md`, `yaml.md`, `markdown.md`, and `ipynb.md`). A file in this directory activates only when a targeted file extension matches the dispatch patterns defined in `2_context/scenarios/languages.md`.

## Section 2. Criteria Evaluation Pipeline

### Item A. Evaluation Pipeline Topology

When an operational request or tool call enters the runtime, the evaluation pipeline enforces rules through four sequential tiers:

```mermaid
graph LR
    Req([User Prompt or Tool Call Trigger]) --> Tier1

    subgraph Tier1 ["Tier 1: Global Invariants (1_model_behavior)"]
        direction TB
        G101["§ 101 Identity Mandate"] --> G102["§ 102 MECE Analytical Standard"]
        G102 --> G106["§ 106 Default Read-Only and Authorization"]
        G106 --> G108["§ 108 Mandatory Halt and Review"]
        G108 --> G111["§ 111 Minimalist Verification Reporting"]
    end

    Tier1 --> EvalAct{§ 201 Act Predicate Evaluation}

    subgraph Tier2 ["Tier 2: Contextual Specialization (2_context)"]
        direction TB
        EvalAct -- Planning Phase --> PlanBranch["reply.md<br/>§ 104 Evidence and § 109 Convergence"]
        EvalAct -- Local File Mutation --> MutateBranch["local-mutate.md / tdd.md<br/>§ 202 Test-Driven Development"]
        EvalAct -- External Write --> ExtBranch["external-write.md / mr.md / commit.md<br/>§ 204 MR Specs and § 205 Commit Specs"]
        PlanBranch & MutateBranch & ExtBranch --> DomainCheck["2_context/domain/<br/>Architecture Principles: 40-Secrets to 99-Contract"]
    end

    Tier2 --> EvalMedium{Output Medium Evaluation}

    subgraph Tier3 ["Tier 3: Register and Style Binding (3_register)"]
        direction TB
        EvalMedium -- Dialogue --> RegDialogue["§ 301 Objective Tone<br/>§ 302 Vocabulary Prohibitions"]
        EvalMedium -- Technical Prose --> RegProse["§ 305 RFC 7322 and ISO Structure<br/>Single Event Per Sentence"]
        EvalMedium -- Source Code --> RegCode["§ 303 Coding Standards<br/>§ 304 Comment Lifecycle<br/>§ 306 Identifier Naming"]
    end

    RegProse & RegCode --> EvalPath{File Extension Matched?}

    subgraph Tier4 ["Tier 4: Language-Specific Constraints (4_L2-trigger)"]
        direction TB
        EvalPath -- "languages.md Match" --> L2Spec["golang.md / typescript.md / hcl.md<br/>yaml.md / markdown.md / ipynb.md"]
        L2Spec --> Reg307["§ 307 L2 Integration Verification"]
    end

    RegDialogue --> Out([Completed Response or Tool Execution])
    Reg307 --> Out
```

### Item B. Tier Breakdown

1. **Global Invariants (Tier 1)**: Initial evaluation subjects every prompt and action to the behavioral mandates in `1_model_behavior/`. § 101 controls identity boundaries. § 102 enforces structured problem decomposition. § 106 enforces read-only operation until explicit authorization occurs. § 108 intercepts halt directives. § 111 limits execution responses to verification evidence.
2. **Contextual Specialization (Tier 2)**: § 201 evaluates the operational act:
    - A planning or inquiry interaction routes to `reply.md`, binding § 104 due diligence and § 109 single recommendation convergence.
    - A working-tree byte modification routes to `local-mutate.md`, binding § 202 Test-Driven Development whenever test paths match.
    - A command modifying remote state (`git push`, `glab`, `gh`, or MCP write) routes to `external-write.md`, binding § 204 for Merge Requests or § 205 for Conventional Commits.
    - Technology-specific system changes incorporate matching domain principles from `2_context/domain/`.
3. **Register Binding (Tier 3)**: Output generation attaches structural constraints based on medium:
    - Dialogue must satisfy § 301 impersonal tone and § 302 vocabulary limits.
    - Documentation and commit text must satisfy § 305 sentence independence rules.
    - Source code must satisfy § 303 standards, § 304 comment line limits, and § 306 function naming conventions.
4. **Language Constraints (Tier 4)**: File paths matching patterns in `2_context/scenarios/languages.md` attach corresponding rules from `4_L2-trigger/`. § 307 completes the validation loop.

### Item C. Runtime Hook Execution Lifecycle

Claude Code and Cursor environments enforce criteria compliance via PreToolUse, PostToolUse, and Stop hooks.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant Agent as Agent Runtime
    participant PreHook as PreToolUse Hook (gate-check.py)
    participant State as Session Marker Tree (/tmp)
    participant Disk as Local Workspace and Tools
    participant PostHook as PostToolUse Hook (post-write-review.py)

    User->>Agent: Prompt or Instruction
    Agent->>PreHook: Invokes Tool Call (Edit, Write, Bash)

    alt Hard Deny Triggered (git push -f, rm -rf)
        PreHook-->>Agent: DENY (Permanent Rejection)
    else External Write Operation
        alt Execution Phrase Absent in Current Turn
            PreHook-->>Agent: DENY / ASK (Demands Explicit Execution Authorization)
        end
    end

    PreHook->>State: Check Scenario Marker (is_scenario_surfaced)
    alt First Time Encountered in Session
        PreHook->>State: Record Marker (record_surfaced_scenario)
        PreHook-->>Agent: DENY (Injects Scenario Bundle Text and Requests Retry)
    else Previously Surfaced in Session
        PreHook-->>Agent: ALLOW (Permits Tool Execution)
    end

    Agent->>Disk: Executes Disk Mutation or Shell Command
    Disk-->>PostHook: Emits Tool Result
    PostHook->>PostHook: Executes Mechanical Register Scan (§ 304, § 305)
    alt Register Violation Detected
        PostHook-->>Agent: EMIT VIOLATION (Requires Immediate In-File Remediation)
    else Clean Register Check
        PostHook-->>Agent: Silent Continuation
    end
```

### Item D. Hook Operation Contracts

1. **PreToolUse (`hooks/adapters/claude/gate-check.py`)**: Intercepts `Edit`, `Write`, `StrReplace`, `TabWrite`, and `Bash` operations. Blocks destructive commands immediately. Demands an authorization phrase for external write operations. When an operational scenario triggers for the first time in a session, the hook records a state marker, rejects the call, and surfaces the scenario bundle text for immediate retry. Subsequent calls with that scenario ID pass through without interruption.
2. **PostToolUse (`hooks/adapters/claude/post-write-review.py`)**: Reviews file modifications landing on disk. Scans modified lines for register violations, including bare pronoun references, uncoordinated causal conjunctions, and excessive comment lengths. Detected violations require immediate correction before subsequent tool execution.
3. **Shared Parser Module (`hooks/adapters/claude/scenario_parser.py`)**: Centralizes YAML frontmatter extraction, scenario directory traversal, and path glob specificity calculations.

## Section 3. Harness Adapter Installation and Reconciliation

### Item A. Installation-Evaluation State Machine

The adapter installer (`hooks/adapter_install/install.py`) materializes repository sources into runtime target paths under product homes (`~/.agents`, `~/.claude`, `~/.cursor`, `~/.grok`, `~/.gemini`). The installer relies exclusively on Python standard library modules without invoking external shell commands or subprocesses.

```mermaid
graph LR
    Start([Inspect Adapter Destination]) --> CheckDest{Destination Exists?}
    CheckDest -- No --> RetMissing[State: missing]
    CheckDest -- Yes --> IsSymlink{Is Symlink?}

    IsSymlink -- Yes --> CheckModeSymlink{Spec Mode is Symlink?}
    CheckModeSymlink -- No --> RetSymForCopy[State: symlink-for-copy]
    CheckModeSymlink -- Yes --> CheckTarget{Target Equals Source?}
    CheckTarget -- Yes --> RetOK[State: ok]
    CheckTarget -- No --> RetWrong[State: wrong-symlink or broken-symlink]

    IsSymlink -- No --> CheckRegular{Spec Mode is Copy or MDC?}
    CheckRegular -- Yes --> CompareBytes{Content Equals Rendered Payload?}
    CompareBytes -- Yes --> RetOK
    CompareBytes -- No --> RetCopyDiffers[State: copy-differs]

    CheckRegular -- No --> CompareTree{Directory Content Matches Source?}
    CompareTree -- Yes --> RetRegSame[State: regular-same]
    CompareTree -- No --> RetRegDiff[State: regular-differs -> Abort Execution]
```

### Item B. Allow-Listed Adapter Destinations

| Source Path                                       | Destination Path                       | Mode       |
| ------------------------------------------------- | -------------------------------------- | ---------- |
| `rules/AGENT_CRITERIA.md`                         | `~/.agents/AGENTS.md`                  | symlink    |
| `rules/AGENT_CRITERIA.md`                         | `~/.gemini/GEMINI.md`                  | symlink    |
| `hooks/adapters/claude/CLAUDE.md`                 | `~/.claude/CLAUDE.md`                  | copy       |
| `hooks/adapters/claude/gate-check.py`             | `~/.claude/hooks/gate-check.py`        | copy       |
| `hooks/adapters/claude/post-write-review.py`      | `~/.claude/hooks/post-write-review.py` | copy       |
| `hooks/adapters/claude/scenario_parser.py`        | `~/.claude/hooks/scenario_parser.py`   | copy       |
| `hooks/adapters/claude/gate-check.py`             | `~/.cursor/hooks/gate-check.py`        | copy       |
| `hooks/adapters/claude/post-write-review.py`      | `~/.cursor/hooks/post-write-review.py` | copy       |
| `hooks/adapters/claude/scenario_parser.py`        | `~/.cursor/hooks/scenario_parser.py`   | copy       |
| `hooks/adapters/cursor/stop-output-scan.py`       | `~/.cursor/hooks/stop-output-scan.py`  | copy       |
| `hooks/adapters/cursor/skill-module-gate.py`      | `~/.cursor/hooks/skill-module-gate.py` | copy       |
| `hooks/adapters/cursor/hooks.json`                | `~/.cursor/hooks.json`                 | copy       |
| `hooks/adapters/skills`                           | `~/.agents/skills`                     | symlink    |
| `hooks/criteria`                                  | `~/.agents/criteria`                   | symlink    |
| `rules/ENGINEERING_PRINCIPLES.md`                 | `~/.agents/ENGINEERING_PRINCIPLES.md`  | symlink    |
| `hooks/criteria/4_L2-trigger/markdown.md`         | `~/.claude/lang_md.md`                 | symlink    |
| `hooks/criteria/4_L2-trigger/hcl.md`              | `~/.claude/lang_hcl.md`                | symlink    |
| `hooks/criteria/4_L2-trigger/typescript.md`       | `~/.claude/lang_ts.md`                 | symlink    |
| `hooks/criteria/4_L2-trigger/ipynb.md`            | `~/.claude/lang_ipynb.md`              | symlink    |
| `hooks/criteria/4_L2-trigger/yaml.md`             | `~/.claude/lang_yaml.md`               | symlink    |
| `hooks/criteria/4_L2-trigger/golang.md`           | `~/.claude/lang_go.md`                 | symlink    |
| `hooks/criteria/4_L2-trigger/markdown.md`         | `~/.gemini/lang_md.md`                 | symlink    |
| `hooks/criteria/4_L2-trigger/hcl.md`              | `~/.gemini/lang_hcl.md`                | symlink    |
| `hooks/criteria/4_L2-trigger/typescript.md`       | `~/.gemini/lang_ts.md`                 | symlink    |
| `hooks/criteria/4_L2-trigger/ipynb.md`            | `~/.gemini/lang_ipynb.md`              | symlink    |
| `hooks/criteria/4_L2-trigger/yaml.md`             | `~/.gemini/lang_yaml.md`               | symlink    |
| `hooks/criteria/4_L2-trigger/golang.md`           | `~/.gemini/lang_go.md`                 | symlink    |
| `rules`                                           | `~/.grok/rules`                        | symlink    |
| `skills`                                          | `~/.grok/skills`                       | symlink    |
| `config/contexts.toml`                            | `~/.grok/contexts.toml`                | symlink    |
| `config/contexts.toml`                            | `~/.claude/contexts.toml`              | symlink    |
| `config/contexts.toml`                            | `~/.gemini/contexts.toml`              | symlink    |
| `hooks/criteria/2_context/scenarios/languages.md` | `~/.cursor/rules/lang-<id>.mdc`        | cursor-mdc |

Cursor `.mdc` files render dynamically from each record declared in `languages.md`. File copies utilize atomic replacement via temporary files to eliminate incomplete read windows.
