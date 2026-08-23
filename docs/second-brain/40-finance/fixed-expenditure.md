# Fixed Expenditure

Fixed Expenditure is a standing commitment. Tag is `Subscription` or `Installment`. Actual charges land on Expenditure Logs.

## Locate

| Item              | Value                                                       |
| ----------------- | ----------------------------------------------------------- |
| Data source title | Fixed Expenditure                                           |
| Data source ID    | see `../03-identifiers.md`                                  |
| Database page     | `https://app.notion.com/p/1c347ff8c6e146bbab2feab9a765ae6f` |
| Surface           | Catalog `Name` `Fixed Expenditures`                         |
| Title property    | `Expenditure Title`                                         |

```sql
SELECT "Expenditure Title", Status, Tag, url FROM "collection://a28876a5-e119-4755-a9f3-c986c49e60c6"
WHERE Status = 'Live'
```

Create a Fixed Expenditure row only when the owner asked to define a recurring or installment commitment.

## Writable properties an Agent may set

| Property                     | Type     | Fill rule                                                                             |
| ---------------------------- | -------- | ------------------------------------------------------------------------------------- |
| `Expenditure Title`          | title    | Commitment name.                                                                      |
| `Status`                     | status   | One of `Inbox`, `Not Started`, `Live`, `Closed`. Use `Live` for an active commitment. |
| `Tag`                        | select   | Required. One of `Subscription`, `Installment`.                                       |
| `Frequency`                  | select   | One of `Monthly`, `Bi-Monthly`, `Quarterly`, `Half Year`, `Yearly`.                   |
| `Expected Amount Per Period` | number   | New Taiwan Dollar per Frequency unit.                                                 |
| `Total Periods`              | number   | Required when Tag is `Installment`. Leave empty when Tag is `Subscription`.           |
| `Start Date`                 | date     | Expanded keys.                                                                        |
| `End Date`                   | date     | Expanded keys. Optional for a Subscription.                                           |
| `Related Category`           | relation | Limit 1. Required. Financial Category.                                                |
| `Related Budget Month`       | relation | Monthly Budgets that this commitment posts into.                                      |
| `Notes`                      | text     | Owner language only.                                                                  |

## Do not write

Formula and rollup properties including `Source`, `Report`, `Predicted Expense`, `Jar`, `Timeframe`.
