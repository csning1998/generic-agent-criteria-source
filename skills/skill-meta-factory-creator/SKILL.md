---
name: skill-meta-factory-creator
description: Foundational meta-skill governing the authoring and registration of new skills within the factory system. Enforces tier architecture (skill-meta-*, skill-module-*, skill-layer-*) and provides explicit disambiguation between deterministic MCP/data pipelines and semantic intelligence/synthesis pipelines.
---

# Meta-Skill: Skills Factory Creator

Governs the creation, verification, and registration of all new skills to guarantee 100% compliance with the factory system architecture.

## Unified Namespace & Tier Taxonomy (三層正交命名架構)

All skills within the factory system strictly follow the unified prefix convention:
`skill-{tier}-{name}`

1. **`skill-meta-*` (Tier 1: Operational Mechanism & Foundation Tier)**:
    - Foundational mechanics of agent operation, universal protocols, and governance specifications.
    - Examples: `skill-meta-python-engine`, `skill-meta-mcp-json`, `skill-meta-factory-creator`.
    - Invariants: Universal across domains. Zero domain-specific entities are baked in.

2. **`skill-layer-*` (Tier 2: Business Orchestration Tier)**:
    - Domain business workflows sequencing one or more modules.
    - For Paradigm A: Owns destination field semantics, write-gate enforcement, artifact generation (`ArtifactName`), and triaged summaries.
    - For Paradigm B: Owns intelligence report structure (Sections 0 to 5), domain whitelist configuration, timepoint parsing, and delivery formats.
    - Examples: `skill-layer-trend-geopolitics`, `skill-layer-sync-gitlab-mrs-to-notion`.

3. **`skill-module-*` (Tier 3: Stateless Adapter & Component Tier)**:
    - Stateless tool executors, API adapters, or contract linters.
    - For Paradigm A: Stateless tool adapter interfacing directly with one tool/MCP API (pure JSON in, pure JSON out).
    - For Paradigm B: Reusable search recipe planner, delta classification contract, or style/lexicon normalizer.
    - Invariants: Pure input/output contracts. Zero hard-coded collection IDs, workspace state, or cross-tool orchestration.

---

## Pipeline Classification & Engine Disambiguation (管線範式分流)

Before applying tier rules, newly authored skills MUST be explicitly classified into one of two pipeline paradigms:

### Paradigm A: Deterministic MCP / Data Pipelines (確定性資料與 API 整合管線)

- **Scope**: Structured entity synchronization, discrete unique IDs, databases, ticketing, calendar operations, and batch API mutations (e.g., GitLab ↔ Notion, Google Calendar, Gmail multi-tagging).
- **Core Invariants**:
    - **Mandatory Python Compute Delegation**: All data mutations, $O(N + M)$ set diffing, and payload assembly MUST be executed in native Python memory via `skill-meta-python-engine`.
    - **C-Level Serialization**: Payloads must be serialized via CPython `json.dumps()` to eliminate text-template escaping bugs.
    - **MCP Protocol Guardrails**: Must adhere to `skill-meta-mcp-json` (no colons in custom property keys outside the Notion system-prefix whitelist, top-level parent boundaries, non-blocking error quarantine).

### Paradigm B: Semantic Intelligence & Synthesis Pipelines (非結構化情報與語意分析管線)

- **Scope**: Open-web information gathering including non-structural contents and qualitative multi-source synthesis (e.g. `skill-layer-trend-*`).
- **Core Invariants**:
    - **LLM Reasoning as Primary Engine**: Fact extraction, policy shift detection, directional movement evaluation, and qualitative delta classification are executed via LLM contextual comprehension.
    - **Module Nature**: `skill-module-*` in this paradigm serve as **Prompt Contracts, Whitelist Search Recipes, and Style/Epistemic Linters**, rather than brittle web scrapers or code adapters.
    - **Sandbox Python Boundary**: In-sandbox Python is strictly reserved for optional lightweight post-processing checks (e.g., title length assertions, deterministic concept substitution) and MUST NOT be used for web scraping (sandbox has no outbound network) or natural language semantic comprehension.
    - **Bounded Context Isolation**: Cross-domain catalysts (markets vs. geopolitics vs. domestic governance) are strictly restricted to single-sentence references.

---

## Mandatory Creation Checklist

Before registering any new skill, verify:

- [ ] **Tier Naming**: Starts strictly with `skill-meta-`, `skill-module-`, or `skill-layer-`.
- [ ] **Pipeline Paradigm Declared**: Explicitly categorized under Paradigm A (Deterministic Data) or Paradigm B (Semantic Intelligence).
- [ ] **Engine Appropriateness**:
    - If Paradigm A: Prohibits text-based JSON templating. Delegates diffing and C-serialization to Python engine.
    - If Paradigm B: Relies on LLM semantic reasoning for qualitative synthesis. Restricts Python engine to offline linting/assertions, and does not attempt network crawling in sandbox.
- [ ] **Delimiter & Key Safety**: Custom property keys never contain colons (`:`) outside the Notion system-prefix whitelist (`date:`, `place:`, `userDefined:`) defined in `skill-meta-mcp-json`.
- [ ] **Non-Blocking Error Handling**: Batch operations implement the Quarantine Pattern (`quarantined_failures`).
- [ ] **Structure & Contract**: Defines When to Use, Input Requirements, Process, Output (Named Artifact), Validation Checklist, and Backtrack Triggers.
