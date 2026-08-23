# Master catalog

This file is the access index. Each row points at one data source file. Identifiers live in `03-identifiers.md`. Operating bans live in `00-operating-contract.md`.

Folder numbers follow System Metadatabase H2 order. Extra data sources sit in `70-extras/`.

| Section                  | Object                    | Doc                                                   | Agent default                         |
| ------------------------ | ------------------------- | ----------------------------------------------------- | ------------------------------------- |
| 10 Years Days Goals KPIs | Years                     | `10-years-days-goals-kpis/years.md`                   | Read. Create only for a missing year. |
| 10 Years Days Goals KPIs | Days                      | `10-years-days-goals-kpis/days.md`                    | Read unless logging a day.            |
| 10 Years Days Goals KPIs | Goal Settings             | `10-years-days-goals-kpis/goal-settings.md`           | Optional draft before Goals.          |
| 10 Years Days Goals KPIs | Goals                     | `10-years-days-goals-kpis/goals.md`                   | Execution parent.                     |
| 10 Years Days Goals KPIs | Key Performance Indices   | `10-years-days-goals-kpis/key-performance-indices.md` | Read unless creating a KPI.           |
| 10 Years Days Goals KPIs | KPI Logs                  | `10-years-days-goals-kpis/kpi-logs.md`                | Read unless logging a value.          |
| 20 Tasks Projects Areas  | Tasks                     | `20-tasks-projects-areas/tasks.md`                    | Daily GTD write.                      |
| 20 Tasks Projects Areas  | Projects                  | `20-tasks-projects-areas/projects.md`                 | Optional WBS.                         |
| 20 Tasks Projects Areas  | Areas                     | `20-tasks-projects-areas/areas.md`                    | Standing domain.                      |
| 30 Habits Journal        | Habits                    | `30-habits-journal/habits.md`                         | Read unless changing a Habit.         |
| 30 Habits Journal        | Journal                   | `30-habits-journal/journal.md`                        | Read unless writing a Journal row.    |
| 30 Habits Journal        | My Significant Events     | `30-habits-journal/significant-events.md`             | Owner-manual review.                  |
| 40 Finance               | Jars                      | `40-finance/jars.md`                                  | Dimension.                            |
| 40 Finance               | Financial Categories      | `40-finance/financial-categories.md`                  | Dimension.                            |
| 40 Finance               | Fiscal Years              | `40-finance/fiscal-years.md`                          | Period.                               |
| 40 Finance               | Monthly Budgets           | `40-finance/monthly-budgets.md`                       | Period.                               |
| 40 Finance               | Income                    | `40-finance/income.md`                                | Ledger inflow.                        |
| 40 Finance               | Fixed Expenditure         | `40-finance/fixed-expenditure.md`                     | Standing commitment. Tag Subscription or Installment. |
| 40 Finance               | Flexible Expenditure      | `40-finance/flexible-expenditure.md`                  | Monthly envelope.                     |
| 40 Finance               | Expenditure Logs          | `40-finance/expenditure-logs.md`                      | Daily 記帳 line. Single spend fact.   |
| 40 Finance               | Expenditure Plans         | `40-finance/expenditure-plans.md`                     | Intent. Not cashflow until realized.  |
| 50 Workout Meals         | Workout Sessions          | `50-workout-meals/workout-sessions.md`                | Read unless logging.                  |
| 50 Workout Meals         | Fitness Records           | `50-workout-meals/fitness-records.md`                 | Read.                                 |
| 50 Workout Meals         | Weights Log               | `50-workout-meals/weights-log.md`                     | Read unless logging.                  |
| 50 Workout Meals         | Cardio Log                | `50-workout-meals/cardio-log.md`                      | Read unless logging.                  |
| 50 Workout Meals         | Classes and Sports Log    | `50-workout-meals/classes-sports-log.md`              | Read unless logging.                  |
| 50 Workout Meals         | Recipes                   | `50-workout-meals/recipes.md`                         | Read unless asked.                    |
| 50 Workout Meals         | Ingredients               | `50-workout-meals/ingredients.md`                     | Read unless asked.                    |
| 50 Workout Meals         | Weekly Meal Plan          | `50-workout-meals/weekly-meal-plan.md`                | Read unless asked.                    |
| 60 Knowledge             | Notes                     | `60-knowledge/notes.md`                               | Create only when asked.               |
| 60 Knowledge             | Topics                    | `60-knowledge/topics.md`                              | Knowledge Base topic.                 |
| 60 Knowledge             | Resources                 | `60-knowledge/resources.md`                           | Do not write.                         |
| 60 Knowledge             | Contacts                  | `60-knowledge/contacts.md`                            | Optional relation.                    |
| 70 Extras                | Dashboard Database        | `70-extras/dashboard-database.md`                     | Catalog of surfaces.                  |
| 70 Extras                | Fear Setting Database     | `70-extras/fear-setting.md`                           | Owner-manual.                         |
| 70 Extras                | Articles                  | `70-extras/articles.md`                               | Computer Science articles. Not Notes. |
| 70 Extras                | CS Topics                 | `70-extras/cs-topics.md`                              | Distinct from Knowledge Base Topics.  |

Count is 37 data sources. Folder `70-extras/` holds four extras. Time Tracker appears in the Metadatabase ERD as a Task relation, not as a standalone data source. The Google Drive File relation on Tasks returned `object_not_found`.

Knowledge Base Topics and CS Topics share the live title `Topics`. Use the Object column in this table, then the `collection://` ID in `03-identifiers.md`.

Lookup order:

1. Open `02-master-catalog.md` and pick the Object row.
2. Open the Doc path in that row.
3. Copy IDs from `03-identifiers.md`.
