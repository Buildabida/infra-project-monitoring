# Data quality checks

> [!NOTE]
> This is our proposed design for the checks. No checks notebook or `04-validation.dq_results` table is built yet.

Each run should check the data before it moves to the next layer:

1. Silver runs only after bronze passes its checks.
2. Gold runs only after silver passes.
3. The dashboard and Genie use only gold tables that passed.

| Check | Example | If it fails |
| --- | --- | --- |
| Not null | `contract_id` is never empty | Stop the run |
| Unique | One row per `contract_id` in `02-silver.projects` | Stop the run |
| Row counts | Bronze, silver and gold totals match, after known drops | Stop the run |
| Valid range | `progress` is from 0 to 100 | Flag the row |
| Map point | The point is inside the Philippines | Flag the row |
| Place match | Every project has a PSGC code | Flag and report the match rate |
| Money | `amount_paid` is not more than `budget` | Flag the row |

Never skip a failed check, mark it as passed by hand or edit a table by hand to make a run look fine. Keep the results of failed runs, so we can see what went wrong.

## Where the results go

Each run saves its results in `04-validation.dq_results`. We use the same columns as in Week 9:

| column | data_quality_check | failed_rows | total_rows | percentage | status |
| --- | --- | --- | --- | --- | --- |
| contract_id | not null | 0 | 1000 | 0.00 | PASS |

We finalize these fields when we build the first checks.
