---
name: skill-module-notion-query
effort: low
description: >
    Execute Notion database or data source queries from a QueryRequest JSON.
    Use when a layer hands off that JSON or when the user runs
    /skill-module-notion-query. This is the generic Notion query adapter.
metadata:
    short-description: "Execute generic Notion queries from QueryRequest"
---

# Module Notion query

## When to Use

A layer already filled `data_source_url` (or `data_source_id`) and `query`.

## Input Requirements

Load `~/.grok/skills/modules/shared/notion-mcp.md`.

```json
{
    "data_source_id": "<data_source_id>",
    "data_source_url": "<data_source_url>",
    "query": "SELECT Name, url, Status FROM \"<from locate>\" LIMIT 100",
    "filter": null,
    "sorts": null,
    "page_size": 100
}
```

`data_source_url`, `data_source_id`, or `query` comes from the calling layer. This module does not own collection IDs or database schemas. If both `data_source_url` and `data_source_id` are missing, return `ok` false.

## Process

1. Call `notion__notion-query-data-sources` or Notion database query endpoint with the received target and query/filter.
2. Handle pagination via `LIMIT` / `OFFSET` or cursors when query results exceed single page capacity.
3. Return raw rows without parsing domain-specific tokens.
4. Do not evaluate whether rows match layer domain criteria; return rows directly to the layer.

## Output

Artifact `NotionQueryResult`.

```json
{
    "ok": true,
    "error": null,
    "rows": [
        {
            "Name": "example row title",
            "url": "https://app.notion.com/p/...",
            "Status": "Done"
        }
    ]
}
```

## Validation Checklist

- [ ] Query matches input JSON
- [ ] Module remains stateless and bakes zero domain entity names or token parsers
- [ ] Raw rows are returned intact to the calling layer

## Backtrack Triggers

- `object_not_found` on the query target: return `ok` false. The layer stops.
- Query syntax error: return `ok` false and the Notion error message.

## Example

Layer sends SQL query to this module. Module executes query, pages results if necessary, and returns `NotionQueryResult` with raw rows.
