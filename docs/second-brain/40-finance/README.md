# Finance

Daily bookkeeping is the second active loop. The Financial Database Manual splits finance into four collections that do not overlap.

1. Dimension holds Jar and Financial Category.
2. Period holds Fiscal Years and Monthly Budget. Monthly Budget carries `Previous Period`.
3. Ledger holds Income Event, Fixed Expenditure, Flexible Expenditure, and Expenditure Log.
4. Intent holds Expenditure Plan. Allocation is unused.

Jar MUST NOT hold a transaction. Flexible Expenditure MUST set exactly one Financial Category. Every Expenditure Log MUST belong to exactly one Monthly Budget. Every Expenditure Log MUST bind to exactly one carrier. The carrier is Fixed Expenditure or Flexible Expenditure. Expenditure Plan and Expenditure Log are disjoint until realization.
Fixed Expenditure `Tag` is `Subscription` or `Installment`.

Currency display on number properties is New Taiwan Dollar.

Open surfaces from Catalog `Name` `Financial Dashboards`, `Financial Inbox`, `The 6-Jar System and Categories`, `Monthly Flexible Budgets`, `Fixed Expenditures`, `Expenditure Plans`, and `Financial Year Overview`.

One locate and fill file exists for each finance H3. Allocation has no file.
