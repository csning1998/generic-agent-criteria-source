---
name: skill-meta-mcp-json
description: Foundational meta-skill governing MCP tool call JSON serialization, fault-tolerant batch execution, delimiter collision prevention, and error quarantine. Mandates skill-meta-python-engine for serialization and compute.
---
# Meta-Skill: MCP JSON Protocol & Fault-Tolerant Engine

Mandatory foundational skill for all MCP tool calls. Governs protocol safety, delimiter isolation, non-blocking batch execution, and graceful degradation during failures.

## Core Invariants

### 1. Mandatory Compute Delegation (`skill-meta-python-engine`)
- **Prohibit Text-Based Templating**: Never use Jinja2 string templating or manual string concatenation to assemble JSON payloads.
- **Pure Memory Construction & C-Level Dumps**: All non-trivial payload structures and collections must be constructed as native Python `dict`/`list` objects and serialized via `json.dumps()` in CPython, delegating to `skill-meta-python-engine`.

### 2. Direct Batch Execution (No Per-Item Prompting)
- Once the write-gate is approved in the current turn, execute all candidate items directly without user interaction per item.
- Chunk requests into optimal window sizes to maximize throughput.

### 3. Item-Level Fault Tolerance & Non-Blocking Isolation
- **Quarantine Pattern**: A failure on a single item MUST NOT terminate the execution of the remaining queue.
- Record failed items into `quarantined_failures` array with `item_id`, `error_type`, and `reason`, and continue processing.
- Transient errors (HTTP 429, timeouts): Apply exponential backoff and retry up to 3 times.

### 4. Delimiter & Key Safety (With Notion SQLite Schema Whitelist)
- **System-Prefixed Colon Whitelist**: In Notion MCP (`notion-create-pages`, `notion-update-page`, `notion-query-data-sources`), expanded property keys mandated by the SQLite schema are explicitly whitelisted and REQUIRED:
  - Date properties: `"date:{Property}:start"`, `"date:{Property}:end"`, `"date:{Property}:is_datetime"` (0 or 1).
  - Place properties: `"place:{Property}:name"`, `"place:{Property}:address"`, `"place:{Property}:latitude"`, `"place:{Property}:longitude"`, `"place:{Property}:google_place_id"`.
  - Reserved property names: `"userDefined:URL"`, `"userDefined:id"`.
- **Custom Property Keys**: Outside the whitelisted system prefixes above, never construct arbitrary custom property keys containing unescaped delimiter colons (`:`).
- **Top-Level Root Boundaries**: Parent and target selectors (`parent`, `project_id`, `data_source_id`, `allow_async`) must remain at the root level of tool call arguments, never nested inside `pages` items.

### 5. Triaged Execution Reporting
Emit a structured triage report at completion: `total`, `succeeded_count`, `failed_count`, `succeeded`, `failed`.
