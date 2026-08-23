# Expenditure Logs

Expenditure Log is the single actual spend fact. This is the daily 記帳 write target. Each row binds to exactly one carrier. The carrier is Fixed Expenditure or Flexible Expenditure.

## Locate

| Item              | Value                                                       |
| ----------------- | ----------------------------------------------------------- |
| Data source title | Expenditure Logs                                            |
| Data source ID    | see `../03-identifiers.md`                                  |
| Database page     | `https://app.notion.com/p/319919d4193680d0a35ceb048b789a59` |
| Title property    | `Log Entry`                                                 |
| Template          | Live name is `@Now` plus one trailing space                 |

## Writable properties an Agent may set

| Property                       | Type     | Fill rule                                                         |
| ------------------------------ | -------- | ----------------------------------------------------------------- |
| `Log Entry`                    | title    | What was spent.                                                   |
| `Amount`                       | number   | Single transaction delta in New Taiwan Dollar.                    |
| `Log Time`                     | date     | Expanded keys with time.                                          |
| `Payment Status`               | select   | One of `Pending`, `Paid`.                                         |
| `Posting Period`               | relation | Required. Limit 1. Monthly Budget for the posting month.          |
| `Related Fixed Expenditure`    | relation | Limit 1. Set when the carrier is a Fixed Expenditure.             |
| `Related Flexible Expenditure` | relation | Limit 1. Set when the carrier is a Flexible Expenditure envelope. |
| `Related Category`             | relation | Limit 1. Posting Financial Category.                              |
| `Related Day`                  | relation | Days page. Set only when Related Flexible Expenditure is set.     |
| `Related Project`              | relation | Optional.                                                         |
| `Notes`                        | text     | Owner language only.                                              |

Exactly one of Related Fixed Expenditure or Related Flexible Expenditure MUST be set.

## Do not write

Formula properties including `Expense Class`. Rollup properties `Budget Month` and `Rollup Category`.
