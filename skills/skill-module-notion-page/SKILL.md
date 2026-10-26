---
name: skill-module-notion-page
effort: low
description: >
    Execute Notion page create, update, or property lookup from a PageRequest
    JSON payload. Use when a layer hands off that JSON or when the user runs
    /skill-module-notion-page. This is the generic Notion page write adapter.
metadata:
    short-description: "Execute generic Notion page operations from PageRequest"
---

# Module Notion page

## When to Use

A layer already filled `op` and, for `create` or `update`, `payload_path`.

## Input Requirements

Load `~/.grok/skills/modules/shared/notion-mcp.md`.

```json
{
    "op": "create",
    "target": {
        "data_source_id": "<data_source_id>",
        "page_id": null
    },
    "lookup": {
        "property": "userDefined:URL",
        "value": "<url from payload>"
    },
    "payload_path": "<payload_path>"
}
```

`op` is `lookup`, `create`, or `update`. For `create` and `update`, read the JSON at `payload_path`.

The JSON at `payload_path` MUST conform to this schema:

```json
{
    "page": {
        "icon": null,
        "cover": null,
        "properties": {}
    },
    "markdown_content": "<markdown body string>"
}
```

Top-level `icon`, `cover`, and `properties` inside `page` map directly onto Notion API parameters. `markdown_content` maps onto the page body via the Notion markdown endpoint. Do not accept ad-hoc property keys inline. For `update`, `target.page_id` is required.

## Process

1. Call `search_tool` then the Notion MCP tools named in `notion-mcp.md`.
2. For `lookup`, query `target.data_source_id` where `lookup.property` equals `lookup.value`. Return matching page IDs and URLs.
3. For `create` or `update`, read `payload_path`. Walk every string value in the parsed JSON. If any string contains `{{`, `}}`, or `%{`, return `ok` false and `blocked_snippet`. Do not write.
4. For `create`, call `POST https://api.notion.com/v1/pages` with:
   - `parent`: `{"type": "data_source_id", "data_source_id": "<target.data_source_id>"}` (or `database_id` when target specifies database).
   - `icon`: `page.icon` when non-null.
   - `cover`: `page.cover` when non-null.
   - `properties`: `page.properties`.
   Obtain `page_id` and `url` from the response.
5. If `markdown_content` is present and non-empty, call `PATCH https://api.notion.com/v1/pages/{page_id}/markdown` with `replace_content` to populate the page body without string truncation.
6. For `update`, call `PATCH https://api.notion.com/v1/pages/{target.page_id}` with `icon`, `cover`, and `properties`. If `markdown_content` is present and non-empty, update the page body via the markdown endpoint.
7. Return standard result.

## Output

Artifact `NotionPageResult`.

```json
{
    "ok": true,
    "error": null,
    "op": "create",
    "page_id": "<UUID>",
    "url": "https://app.notion.com/p/...",
    "blocked_snippet": null
}
```

## Validation Checklist

- [ ] Module remains stateless and bakes zero workspace collection IDs or entity names
- [ ] Properties and content came from `payload_path`
- [ ] Template tokens `{{`, `}}`, or `%{` abort the write
- [ ] Top-level `icon` and `cover` are forwarded directly to Notion API
- [ ] Page body markdown matches `markdown_content` in full without truncation

## Backtrack Triggers

- Module `blocked_snippet`: the calling layer rewrites `payload_path` and resubmits.
- `object_not_found` for target: return `ok` false and the target ID. The layer stops.

## Example

Layer prepares `PageRequest` at `/tmp/.../page-request.json` and invokes this module. Module validates, calls Notion API, updates markdown, and returns `NotionPageResult`.
