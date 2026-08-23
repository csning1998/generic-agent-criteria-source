# Days

Days is one row per calendar day. Days holds Stamina, Mood, and One Thing. Days links Habits, Journal, Workout Sessions, and Expenditure Logs.

## Locate

| Item              | Value                                                       |
| ----------------- | ----------------------------------------------------------- |
| Data source title | Days                                                        |
| Data source ID    | see `../03-identifiers.md`                                  |
| Database page     | `https://app.notion.com/p/316919d4193681e3b9fad050493f1058` |
| Title property    | `Day`                                                       |

```sql
SELECT Day, url FROM "collection://316919d4-1936-8104-a7f9-000b520be34d"
WHERE Day LIKE '%2026%'
```

## Writable properties an Agent may set

| Property                        | Type         | Fill rule                                                                                                               |
| ------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `Day`                           | title        | Human date label already used on nearby Days rows.                                                                      |
| `Date`                          | date         | Expanded keys. The calendar date of the Days row.                                                                       |
| `Year`                          | relation     | Limit 1. Matching Years page.                                                                                           |
| `One Thing`                     | text         | Owner language for the single focus of the day.                                                                         |
| `Stamina`                       | select       | One of `●●●`, `●●○`, `●○○`, `○○○`.                                                                                      |
| `Mood`                          | multi_select | Zero or more of `Excited`, `Joyful / Happy`, `Content`, `Neutral / Calm`, `Anxious / Worried`, `Stressed / Frustrated`. |
| `Related Habit`                 | relation     | Habits logged on the Days row.                                                                                          |
| `Related Journal Entry`         | relation     | Journal rows for the Days row.                                                                                          |
| `Related Workout Session`       | relation     | Workout Sessions for the Days row.                                                                                      |
| `Related Flexible Expense Logs` | relation     | Expenditure Logs for the Days row. Flexible carrier only.                                                               |

## Do not write

Formula and rollup properties including `Day Report`, `One Thing Report`, `# Habits Logged`.
