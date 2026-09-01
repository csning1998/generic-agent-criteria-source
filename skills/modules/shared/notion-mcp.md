# Notion MCP

Before the first Notion call in a session, call `search_tool` so live schemas load. A sufficient query is `notion create-pages query-data-sources update-page`. The query MUST NOT contain the isolated token `search`.

Call tools through `use_tool` with Grok names `notion__notion-*`.

Do not rediscover a `collection://` ID that `~/.grok/docs/second-brain/03-identifiers.md` already records. The layer copies that ID into module JSON. A module MUST NOT hard-code a collection ID. When calling SQL, prefix that ID with `collection://`. When calling `notion__notion-create-pages`, pass the bare UUID as `data_source_id`.
