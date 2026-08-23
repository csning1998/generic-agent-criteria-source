# Expenditure Plans

Expenditure Plan is the intent layer. An Expenditure Plan is not a ledger event. Realization writes one Expenditure Log and sets Plan Status `Realized`.

## Locate

| Item              | Value                                                       |
| ----------------- | ----------------------------------------------------------- |
| Data source title | Expenditure Plans                                           |
| Data source ID    | see `../03-identifiers.md`                                  |
| Database page     | `https://app.notion.com/p/316919d419368193926bfa9a977b0acb` |
| Surface           | Catalog `Name` `Expenditure Plans`                          |
| Title property    | `Item`                                                      |

## Writable properties an Agent may set

| Property                       | Type         | Fill rule                                                                                 |
| ------------------------------ | ------------ | ----------------------------------------------------------------------------------------- |
| `Item`                         | title        | Planned item.                                                                             |
| `Plan Status`                  | select       | One of `Draft`, `Approved`, `Realized`, `Cancelled`, `Lapsed`. Use `Draft` for a new row. |
| `Spend Tier`                   | select       | One of `Necessity`, `Need`, `Want`.                                                       |
| `Confidence`                   | select       | One of `Confirmed`, `Likely`, `Possible`.                                                 |
| `Realization Route`            | select       | One of `Fixed Commitment`, `Flexible Envelope`, `Direct Log`.                             |
| `Price`                        | number       | Estimated New Taiwan Dollar amount.                                                       |
| `List Selected`                | multi_select | Zero or more of `Electronics`, `Art and Designs`, `Equipments`.                           |
| `Shop / Source`                | select       | One of `PCHome`, `Other Online Store`, `Vacpack Official`.                                |
| `userDefined:URL`              | url          | Optional product URL.                                                                     |
| `Related Category`             | relation     | Limit 1. Financial Category.                                                              |
| `Target Period`                | relation     | Limit 1. Monthly Budget.                                                                  |
| `Related Expenditure Log`      | relation     | Limit 1. Required when Plan Status is `Realized`.                                         |
| `Related Fixed Expenditure`    | relation     | Set only when Realization Route is `Fixed Commitment`.                                    |
| `Related Flexible Expenditure` | relation     | Set only when Realization Route is `Flexible Envelope`.                                   |

Exactly one Realization Route relation MAY be populated. Direct Log leaves both commitment relations empty and still requires an Expenditure Log when Realized.

Do not treat an Expenditure Plan as Income, Fixed Expenditure, or Flexible Expenditure.
