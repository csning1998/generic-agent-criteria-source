# Locate surfaces

Prefer a stored URL or `collection://` ID from `03-identifiers.md`. Call `notion__notion-search` only when the target is absent from `03-identifiers.md` and from `70-extras/dashboard-database.md`.

## Tool sequence

1. Call `search_tool` once in a session with query `notion create-pages query-data-sources update-page`. The query MUST NOT contain the isolated token `search`.
2. Call `notion__notion-fetch` with a page URL, a raw UUID, or a `collection://` ID.
3. Call `notion__notion-query-data-sources` with `data.data_source_urls` and a SQL `query`.

Do not pass a page title as `notion__notion-fetch` `id`.

## Hub and catalog

| Surface                         | Kind                | How to open                                         |
| ------------------------------- | ------------------- | --------------------------------------------------- |
| Second Brain Dashboard          | Hub page            | URL in `03-identifiers.md`                          |
| Dashboard Database              | Catalog data source | `collection://d2f4ebac-225b-49a4-a21f-21cc9cc9e4cd` |
| System Metadatabase             | ERD and DDL page    | URL in `03-identifiers.md`                          |
| Inbox Dashboard                 | GTD capture surface | Catalog `Name` `Inbox`                              |
| `Tasks & Action View`           | Daily Task surface  | Catalog `Name` `Tasks & Action View`                |
| `Goal Setting & Yearly Planner` | Goal surface        | Catalog `Name` `Goal Setting & Yearly Planner`      |
| `Projects`                      | Project surface     | Catalog `Name` `Projects`                           |
| `Life Areas`                    | Area surface        | Catalog `Name` `Life Areas`                         |
| `Knowledge Base`                | Note surface        | Catalog `Name` `Knowledge Base`                     |
| `Financial Dashboards`          | Finance surface     | Catalog `Name` `Financial Dashboards`               |
| `Financial Inbox`               | Finance capture     | Catalog `Name` `Financial Inbox`                    |

Catalog `Name` values and `Sort` keys live in `70-extras/dashboard-database.md`.

## Query shape

Every SQL query uses the data source URL as the table name.

```json
{
    "data": {
        "data_source_urls": [
            "collection://316919d4-1936-81e5-b1af-000b95494b22"
        ],
        "query": "SELECT Name, url FROM \"collection://316919d4-1936-81e5-b1af-000b95494b22\" LIMIT 100"
    }
}
```

The query tool caps a result near 100 rows. When the row count hits that cap, add `ORDER BY` and page with `LIMIT` and `OFFSET`.

Do not SELECT a column listed under `notAvailableInQuerySql`. Date properties use expanded keys such as `date:Completed At:start`.

## Identity check

`notion__notion-fetch` with `id` set to `self` returns Workspace name Failure Managements and the owner user ID. Confirm Workspace before the first write in a session.
