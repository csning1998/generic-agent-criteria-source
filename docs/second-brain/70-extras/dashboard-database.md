# Dashboard Database

Dashboard Database is the Catalog. Each row is a Hub surface, not a data source. An Agent reads Catalog to locate a surface. An Agent MUST NOT create a Catalog row unless the owner asked.

## Locate

| Item              | Value                                                       |
| ----------------- | ----------------------------------------------------------- |
| Data source title | Dashboard Database                                          |
| Data source ID    | see `../03-identifiers.md`                                  |
| Database page     | `https://app.notion.com/p/eed2818ac17b4269b1344cece4f3921e` |
| Title property    | `Name`                                                      |

```sql
SELECT Name, Methodology, "Meta Description", "Page URL", Sort, url
FROM "collection://d2f4ebac-225b-49a4-a21f-21cc9cc9e4cd"
ORDER BY Sort
```

## Writable properties an Agent may set

| Property           | Type         | Fill rule                                                                                                                                                                                                     |
| ------------------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Name`             | title        | Surface name already used on Hub.                                                                                                                                                                             |
| `Sort`             | number       | Catalog sort key. Two rows share Sort `130`. Distinguish those rows by `Name`.                                                                                                                                |
| `Page URL`         | url          | Target Notion page or external URL.                                                                                                                                                                           |
| `Methodology`      | multi_select | Zero or more of `The 7 Habits`, `Eisenhower Matrix`, `Getting Things Done`, `P.A.R.A`, `Retrospective Review`, `Atomic Habits`, `Zettelkasten`, `6 Jars System`, `Zero-based Budgeting`, `Cashflow Tracking`. |
| `Meta Description` | text         | Short annotation.                                                                                                                                                                                             |

## Do not write

Formula property `Metadata`.

## Rows

| Sort | `Name`                            | Methodology                                            | Agent use                          |
| ---- | --------------------------------- | ------------------------------------------------------ | ---------------------------------- |
| 10   | `Year Summaries`                  | Retrospective Review                                   | Read                               |
| 20   | `Goal Setting & Yearly Planner`   | The 7 Habits                                           | Goal locate                        |
| 30   | `My Calendars`                    | Eisenhower Matrix, Getting Things Done                 | Read                               |
| 40   | `Workout Tracker`                 | Atomic Habits                                          | Read unless asked                  |
| 50   | `Meal Planner`                    | Atomic Habits                                          | Read unless asked                  |
| 80   | `Perspectives`                    | Retrospective Review                                   | Read                               |
| 90   | `Habit Tracker`                   | Atomic Habits, Retrospective Review                    | Read unless asked                  |
| 100  | `Financial Dashboards`            | Cashflow Tracking, 6 Jars System, Retrospective Review | Finance hub                        |
| 110  | `Financial Inbox`                 | Getting Things Done, Cashflow Tracking                 | Daily 記帳 intake                  |
| 120  | `Fixed Expenditures`              | 6 Jars System, Cashflow Tracking                       | Fixed Expenditure                  |
| 130  | `Monthly Flexible Budgets`        | Zero-based Budgeting, 6 Jars System                    | Monthly Budget                     |
| 130  | `The 6-Jar System and Categories` | Zero-based Budgeting, 6 Jars System                    | Jar and Financial Category         |
| 140  | `Financial Year Overview`         | Cashflow Tracking, Retrospective Review                | Read                               |
| 150  | `Financial Years`                 | Retrospective Review                                   | Fiscal Years                       |
| 160  | `Historical Archives`             | Cashflow Tracking                                      | Owner-manual                       |
| 170  | `Inbox`                           | Getting Things Done                                    | Tasks Inbox Status intake          |
| 180  | `Tasks & Action View`             | Getting Things Done, Eisenhower Matrix, The 7 Habits   | Daily Task                         |
| 190  | `Life Areas`                      | P.A.R.A                                                | Area locate                        |
| 200  | `Projects`                        | Getting Things Done, P.A.R.A                           | Project locate                     |
| 210  | `Weekly Review`                   | Getting Things Done, Retrospective Review              | Read                               |
| 220  | `Knowledge Base`                  | P.A.R.A, Zettelkasten, Getting Things Done             | Note locate                        |
| 240  | `Topics`                          | P.A.R.A, Zettelkasten                                  | Knowledge Base Topics              |
| 250  | `Journal`                         | Zettelkasten, Retrospective Review                     | Read                               |
| 260  | `Contacts`                        | Getting Things Done                                    | Optional relation                  |
| 270  | `P.A.R.A Dashboard`               | P.A.R.A, Getting Things Done                           | Menu only                          |
| 280  | `Archives`                        | P.A.R.A, Retrospective Review                          | Owner-manual                       |
| 290  | `Expenditure Plans`               | 6 Jars System                                          | Intent. Not a ledger event         |
| 300  | `Co-Pilot`                        | none                                                   | Ignore unless asked                |
| 310  | `Tasks Bin`                       | Getting Things Done                                    | Completed or deferred Task history |
| none | `Ingredients`                     | Atomic Habits                                          | Meal support                       |
| none | `Recipe Manager`                  | Atomic Habits                                          | Meal support                       |

Two Catalog rows share Sort `130` and the same `Page URL` `https://www.notion.so/316919d41936810183f3cacff79cdb76`. Distinguish those rows by `Name` `Monthly Flexible Budgets` and `Name` `The 6-Jar System and Categories`.
