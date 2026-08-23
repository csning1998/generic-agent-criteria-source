# Fiscal Years

Fiscal Years is the finance year container. Monthly Budgets and Income hang from Fiscal Years. Fiscal Years relates to Years.

## Locate

| Item              | Value                                                       |
| ----------------- | ----------------------------------------------------------- |
| Data source title | Fiscal Years                                                |
| Data source ID    | see `../03-identifiers.md`                                  |
| Database page     | `https://app.notion.com/p/316919d4193681b9bd44f002569d0b63` |
| Surface           | Catalog `Name` `Financial Years`                            |
| Title property    | `Fiscal Year`                                               |

## Writable properties an Agent may set

| Property         | Type     | Fill rule                                   |
| ---------------- | -------- | ------------------------------------------- |
| `Fiscal Year`    | title    | Year label already used nearby.             |
| `Related Year`   | relation | Matching Years page.                        |
| `Related Budget` | relation | Prefer writing the link on Monthly Budgets. |
| `Related Income` | relation | Prefer writing the link on Income.          |

## Do not write

Rollup and formula properties including `Report`, `Profit/Loss`, `Income YTD`.
