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

## Bronze checks

Until silver, our checks are simple load checks. That is decision [D-20](decisions.md). They all live in one notebook, `notebooks/04_validation/01_validation_bronze.py`, and `run_all.py` runs it after the loads.

Each check is one line in a list, so to add a check, add a line. Each check has an action:

- **Stop:** the data is broken, like a row count that doesn't match the source or an empty key. If a stop check fails, the notebook fails. Fix the load before anyone uses the table.
- **Flag:** the data is usable, but silver has to handle these rows. The percentage shows how big the problem is.

The notebook skips tables that aren't loaded yet. Most checks count rows. The checks that add up counts, like people per region, are different. For those, `failed_rows` is how far off the total is, and `total_rows` is the total we expect.

## Where the results go

Each run saves its results in `04-validation.dq_results`. We use the same columns as in Week 9, plus `run_id`, `table_name`, `action` and `run_ts`. The `status` is `PASS`, `FLAG`, `FAIL` or `ERROR`. `ERROR` means the check itself could not run.

| column | data_quality_check | failed_rows | total_rows | percentage | status |
| --- | --- | --- | --- | --- | --- |
| contract_id | not null | 0 | 1000 | 0.00 | PASS |

We finalize these fields when we build the first checks.
