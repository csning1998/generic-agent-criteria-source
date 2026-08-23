# Flexible Expenditure

Flexible Expenditure is a monthly spend envelope. Actual spend lands on Expenditure Logs.

## Locate

| Item              | Value                                                       |
| ----------------- | ----------------------------------------------------------- |
| Data source title | Flexible Expenditure                                        |
| Data source ID    | see `../03-identifiers.md`                                  |
| Database page     | `https://app.notion.com/p/316919d419368179bcf9c0b4168ad0e5` |
| Title property    | `Expenditure Title`                                         |

## Writable properties an Agent may set

| Property                  | Type     | Fill rule                                    |
| ------------------------- | -------- | -------------------------------------------- |
| `Expenditure Title`       | title    | Envelope name.                               |
| `Budgeted Expense`        | number   | Planned New Taiwan Dollar amount.            |
| `Related Category`        | relation | Required. Limit 1. One Financial Category.   |
| `Related Budget Month`    | relation | Required. Exactly one Monthly Budget.        |
| `Related Expenditure Log` | relation | Prefer creating the log in Expenditure Logs. |
| `Related Contact`         | relation | Optional payee.                              |
