# Second Brain documentation

Owner workspace is Failure Managements. The documentation tree tells an Agent how to locate a page and how to fill a writable property without rediscovering the schema.

Read `00-operating-contract.md` first. Then open `02-master-catalog.md` and the entity file that matches the object being created or queried.

## Section 1. Object names

The following names are reserved. A later sentence MUST reuse the reserved name, not a pronoun, when the paragraph already names two or more objects.

- Workspace means Failure Managements (`63b37ef9-7036-4629-8f11-77adb0602ab3`).
- Hub means the page Second Brain Dashboard.
- Catalog means the data source Dashboard Database.
- Metadatabase means the page System Metadatabase.
- Goal means one page in the Goals data source.
- Task means one page in the Tasks data source.
- Project means one page in the Projects data source.
- Area means one page in the Areas data source. The title property of Area is `Life Area`.
- Note means one page in the Notes data source.
- Resource means one page in the Resources data source.
- Jar means one page in the Jars data source.
- Financial Category means one page in the Financial Categories data source.
- Monthly Budget means one page in the Monthly Budgets data source.
- Income Event means one page in the Income data source.
- Flexible Expenditure means one page in the Flexible Expenditure data source.
- Fixed Expenditure means one page in the Fixed Expenditure data source.
- Expenditure Log means one page in the Expenditure Logs data source.
- Expenditure Plan means one page in the Expenditure Plans data source.
- Tasks Inbox Status means the Tasks property `Status` value `Inbox`.
- Notes Inbox Status means the Notes property `Status` value `Inbox`.
- Inbox Dashboard means the Catalog page whose `Name` is `Inbox`.

`this` is allowed only when the surrounding sentence names exactly one reserved object.

## Section 2. How to read the tree

### Task A. Top down order

1. `00-operating-contract.md` states what an Agent MUST and MUST NOT do.
2. `01-locate.md` states how to reach a surface without a fresh workspace search.
3. `02-master-catalog.md` lists every data source and the entity file for that data source.
4. `03-identifiers.md` holds every `collection://` ID and Hub URL.
5. Folder numbers `10` through `60` follow System Metadatabase H2 order. Folder `70-extras/` holds data sources that sit outside Metadatabase.

### Task B. One home per fact

A writable property is defined in exactly one entity file. IDs live only in `03-identifiers.md`. Operating bans live only in `00-operating-contract.md`.

### Task C. Folder map

| Folder                      | Metadatabase H2                                                                          |
| --------------------------- | ---------------------------------------------------------------------------------------- |
| `10-years-days-goals-kpis/` | System Databases: Years & Days, Goals & KPIs                                             |
| `20-tasks-projects-areas/`  | System Databases: Tasks, Projects & Areas                                                |
| `30-habits-journal/`        | System Databases: Habits & Journal                                                       |
| `40-finance/`               | System Databases: Fiscal Year & Monthly Budget, Income & Expenditures, Expenditure Plans |
| `50-workout-meals/`         | System Databases: Workout Tracker & Meal Planner                                         |
| `60-knowledge/`             | System Databases: Knowledge Base: Notes, Topics, Resources, Contacts                     |
| `70-extras/`                | Outside Metadatabase                                                                     |

Each H3 under those H2 headings has one locate and fill file. Allocation is unused and has no file.

## Section 3. Daily loops

Two loops consume almost all owner time.

1. Task management at Getting Things Done granularity, with Goal defined from Covey The 7 Habits of Highly Effective People.
2. Daily bookkeeping through Income Event, Flexible Expenditure, Fixed Expenditure, and Expenditure Log. Intent sits on Expenditure Plan.

PACST (Plan, Action, Capture, Track, System) is a menu invented by the template author. PACST is not the owner's taxonomy.

## Section 4. Execution chain

Goal sits at the top. Task MUST point at Goal through `Related Goal`. Project is a work breakdown or a bundle of similar Task pages under Goal. Project is optional. A Task page remains valid when `Related Project` is empty.
