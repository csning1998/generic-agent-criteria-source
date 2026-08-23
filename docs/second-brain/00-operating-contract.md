# Operating contract

The contract overrides template marketing copy and unused schema. When a live property exists but the contract forbids a write, leave the property empty.

## Agent MUST

1. Locate a surface through `02-master-catalog.md`, `01-locate.md`, and `03-identifiers.md` before calling Notion search.
2. Set Task `Related Goal` when filing a Task.
3. Convert `merged_at` to Asia/Taipei with an explicit `+08:00` offset when writing Task `Completed At`.
4. Scan every string written to Notion, including properties and page `content`, for `{{`, `}}`, or `%{` before create or update.
5. Stop after a candidate list when the owner only asked to check or compare.

## Agent MUST NOT

1. Treat PACST as a filing taxonomy.
2. Require Task `Related Project`. Project is optional.
3. Create, edit, or file Resource pages unless the owner asked in the current turn.
4. Write Archives. Archives are owner-manual.
5. Create or fill Allocation. Allocation is unused and treated as redundant.
6. Assign or define Area `TOP OF MIND`. TOP OF MIND is owner-manual.
7. Treat Jar `Debt` as a seventh jar of the 6 Jars method. Jar `Debt` holds leftover bad debt under dedicated handling.
8. Treat Notes Inbox Status as Tasks Inbox Status. Notes `Status` is document progress.
9. Guess a custom emoji name for Task `icon`. Use the string recorded in `20-tasks-projects-areas/tasks.md`.
10. Query Knowledge Base Topics when the owner asked for CS Topics, or the reverse. Both live titles are `Topics`.
11. Write a relation or rollup whose target data source is absent from `03-identifiers.md` or returns `object_not_found`.
12. Treat an Expenditure Plan as a ledger event. Realization writes an Expenditure Log and sets Plan Status `Realized`.
13. Set both Related Fixed Expenditure and Related Flexible Expenditure on one Expenditure Log.

## Write gate

Creating or updating a Notion page is an external write. The owner must have asked to register, sync, create, or update. A request that only says inspect, list, or compare stays read-only.
