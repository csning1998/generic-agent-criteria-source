---
name: skill-meta-python-engine
description: Foundational meta-skill governing in-sandbox Python deterministic compute. Executes native memory data structure mutations, O(N) set diffing, C-level RFC 8259 serialization via json.dumps, and non-blocking quarantine. Mandatory compute engine for all non-trivial data transformations.
---
# Meta-Skill: Sandbox Python Deterministic Compute Engine

Foundational execution engine running in the local sandbox VM. Governs deterministic data processing, algorithmic set diffing, and C-level JSON serialization across all skills.

## Core Invariants

### 1. Native In-Memory Data Model (Zero Comma/Syntax Hazards)
- **Strictly Prohibit Text-Based JSON Templating**: Never use Jinja2 string templating, regex replacements, or string concatenation to generate JSON.
- **Pure Dict/List Mutations**:
  - Build payloads entirely as native Python `dict` and `list` objects.
  - Manage dynamic/optional fields via direct conditional assignment:
    ```python
    props = {"Name": f"{title} !{iid}", "Status": "Done"}
    if goal_url:
        props["Related Goal"] = [goal_url]
    if project_url:
        props["Related Project"] = [project_url]
    ```
  - Independent field boundaries: Mathematically eliminates leading commas, trailing commas, or missing bracket syntax errors.

### 2. C-Level Serialization via `json.dumps`
- Final serialization into tool call payloads MUST be executed by CPython `json.dumps()`:
  ```python
  payload_json = json.dumps(
      payload_dict, ensure_ascii=False, separators=(",", ":")
  )
  ```
- **100% Escaping Immunity**: Handled entirely at the C extension level (`_json.c`). All nested quotes (`"`), newlines (`\n`), and backslashes (`\`) are guaranteed strictly escaped without string boundary collisions.
- **Token Optimization**: Compact separators `(',', ':')` prune whitespace overhead by 40% to 50%.

### 3. Algorithmic $O(N + M)$ Set Diffing Engine
- Replace LLM visual inspection with deterministic hash-set diffing:
  ```python
  notion_iids = {
      m
      for task in notion_tasks
      for m in re.findall(r"[#!](\d+)\b", task.get("Name", ""))
  }
  missing_mrs = [
      mr for mr in gitlab_mrs if str(mr.get("iid", "")) not in notion_iids
  ]
  ```
- Eliminates context-window attention drift, false positives, and dropped items.

### 4. Local Pre-flight Assertions & Quarantine
- Validate structural invariants in Python before emitting tool calls:
  - Assert no forbidden colons (`:`) in property keys.
  - Assert `parent` is positioned at the top level.
- Item-level quarantine: Wrap batch items in exception handlers to record malformed records to `quarantined_failures` without breaking the global execution pipeline.
