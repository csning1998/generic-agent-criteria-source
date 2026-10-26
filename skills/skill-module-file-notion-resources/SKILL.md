---
name: skill-module-file-notion-resources
effort: low
description: >
    Execute Notion lookup, create, or update from a payload_path a
    layer already filled. Use when a skill- hands off that JSON, or
    when the user runs /skill-module-file-notion-resources. This is
    the Notion write adapter. A Notion API change is confined to this
    file.
metadata:
    short-description: "Execute Notion write from payload_path"
---

# Module Notion write

## When to Use

A layer already filled `op` and, for create or update, `payload_path`.

## Input Requirements

Load `~/.grok/skills/modules/shared/notion-mcp.md`.

```json
{
    "op": "create",
    "data_source_id": "<from locate>",
    "data_source_url": "<from locate>",
    "payload_path": "<payload_path>",
    "page_id": null,
    "lookup": {
        "property": "userDefined:URL",
        "value": "<url from payload>"
    }
}
```

`op` is `lookup`, `create`, or `update`. For `create` and `update`, read the JSON at `payload_path`. Map `content` to page body. Map `icon` to the top-level page icon. Map every other key onto a Notion property except `media_path` and `transcript_path`. Do not accept property keys inline. For `update`, the layer also sends `page_id`.

## Process

1. Call `search_tool` then the Notion MCP tools named in `notion-mcp.md`.
2. For `lookup`, query `data_source_url` for `lookup.property` equals `lookup.value`. Return matching page urls.
3. For `create` or `update`, read `payload_path`. Walk every string value. If any string contains `{{`, `}}`, or `%{`, return `ok` false and the snippet. Do not write.
4. Create pages with parent `{"type":"data_source_id","data_source_id":"<data_source_id>"}`. When `icon` is specified in `payload_path`, include top-level `icon` in the page creation payload. Write properties and content from the payload file. Ensure `title` and `rich_text` property values do not contain raw Markdown syntax strings (such as `[**...**](...)` or unparsed inline code backticks); convert them into valid Notion Rich Text arrays. Write the full string of `content` from `payload_path` to the page body without truncation. Verify the retention of terminal sections in the markdown body.
5. For `update`, update top-level `icon` when present in payload, then call `notion__notion-update-page` `update_properties` then `replace_content` on `page_id`. Write properties and the full `content` from the payload file without prompt-level truncation. Verify the presence of terminal sections in the updated page body.
6. Return page urls.

## Output

Artifact `NotionWriteResult`.

```json
{
    "ok": true,
    "error": null,
    "op": "create",
    "urls": ["https://app.notion.com/p/..."],
    "blocked_snippet": null
}
```

## Validation Checklist

- [ ] Properties and content came from `payload_path`
- [ ] Top-level `icon` is passed to the page creation or update payload when specified in `payload_path`
- [ ] Template tokens abort the write
- [ ] yt-dlp and Buzz were not called
- [ ] No raw Markdown link or bold syntax in `title` property values
- [ ] No raw backticks in `rich_text` property values
- [ ] Page body markdown matches `payload_path` `content` in full without truncation

## Backtrack Triggers

- HTML block page from the connector: return `ok` false. The layer rewrites the payload file and resubmits `payload_path`.
- `object_not_found` for the data source: return `ok` false. The layer stops.

## Example

Layer sends `payload_path`. Module reads that file and returns `urls`.
