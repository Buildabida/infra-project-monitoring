# End-to-end data quality gate

[`01_end_to_end_quality_gate.py`](01_end_to_end_quality_gate.py) is the last check before the dashboard refreshes. It answers one question: **is the data we are about to publish safe to show?**

## Why we need it

Each layer already has its own validator in [`04_validation`](../04_validation/), and each one stops its own layer. But no single place says, "everything from Bronze to Analytics passed, for this run, and the layers still agree with each other." Without that, a validator that silently didn't run, or a table rebuilt after it was validated, could reach the dashboard.

## How it differs from `04_validation`

| | `04_validation` | `06_data_quality` |
| --- | --- | --- |
| Checks | The data in one layer: grain, keys, ranges, reconciliation to the layer before | The **evidence** the validators saved, plus a few checks across layers |
| Reads | Bronze, Silver, Gold, and Analytics tables | The five validation result tables, one Silver table, current Gold project rows, and one Analytics view |
| Stops | The next layer from building | The dashboard refresh |

The gate does not repeat any layer check. It reuses what the validators saved.

## What it checks

**Per validator.** All 13 validator tasks in the job are listed in the notebook. For each one, the gate stops if:

- no evidence was saved
- the latest run misses a table that validator is expected to cover
- the evidence is older than the latest Bronze load event, so it is **stale** and does not describe this pipeline run
- any STOP check failed, or any check returned `ERROR`

**Across layers.** Four STOP checks run at publish time:

1. The latest DPWH load, Silver, current Gold, and the Analytics view all name the same single DPWH snapshot.
2. The project count matches across Silver, current Gold, and `analytics_implementation_monitoring`, with one current Gold row per project.
3. The reported budget total, and the number of projects that have a budget, match across the same three layers. This is the reported budget, not actual payment (D-28).
4. The latest Gold and Analytics evidence names the current Gold fact runs and snapshot. So a fact rebuilt after its validation stops the gate.

## PASS, FLAG, and STOP

| Result | Meaning | What happens |
| --- | --- | --- |
| **PASS** | The requirement is met, with no findings | The dashboard may refresh |
| **FLAG** | The evidence passed, but it carries known data limits, like projects without a map point | The dashboard may refresh. The flags stay in the summary for people to read |
| **STOP** | Evidence is missing or stale, a blocking check failed, or the layers disagree | The gate task fails, and the dashboard refresh does not run |

Missing evidence is never a pass.

## When it runs

In the [pipeline job](../../resources/buildabida_full_pipeline.job.yml), the gate runs after `publish_acceptance_evidence`, as the `end_to_end_quality_gate` task. It runs even when an earlier task failed (`run_if: ALL_DONE`), so the result always records why a run stopped. The `business_dashboard` task waits for the gate **and** the analytics validator and acceptance publisher, so it refreshes only when all of them succeed.

You can also run the notebook on its own after a full pipeline run. Leave `job_run_id` empty.

## Where results are saved

- `04-validation.quality_gate_results` holds one row per gate check. Each row has the check, its status, the validator run it read, its counts (`required_checks`, `passed_checks`, `flagged_checks`, `failed_stop_checks`, `missing_checks`), and a plain-language `details`.
- `04-validation.quality_gate_summary` is a view with one row per layer and one `ALL` row per gate run. It shows `gate_status` (PASS, FLAG, or STOP) and `failure_reason`.

The gate saves its rows **before** it decides, so a stopped gate stays readable.

```sql
SELECT *
FROM `buildabida-capstone`.`04-validation`.quality_gate_summary
ORDER BY evaluated_at DESC, layer
LIMIT 6;
```

## What to do when it stops

1. Read `failure_reason` in the summary, then the matching rows in `quality_gate_results`.
2. If one validator failed, open its results table and find the failed check. The table is `results_table` on the gate row, and the run is `evidence_validation_run_id`.
3. Fix the cause in the layer where it started. Never edit a Gold table by hand to make the gate pass.
4. Use **Repair run** on the failed job run. It reruns the failed tasks and everything after them. See the [operations guide](../../docs/guides/operations.md).

## Rerun safely

The gate only reads data and writes its own results table. Its gate run ID comes from the validator run IDs and the current data identities. So running it twice on the same evidence updates the same rows instead of adding copies. Fixing a validator and rerunning it on the same data also updates the same rows, so the summary shows the recovered result.

## When to change the gate

Change the required-validator list in step 2 when a validator or validated table is added, removed, or renamed. Make that change in the same pull request. `tests/test_quality_gate.py` fails if a validator task in the job is missing from the list.

## Tests

`tests/test_quality_gate.py` runs this exact notebook on local Spark with Delta against small synthetic tables. It never touches Databricks. It covers passing validators, a failed STOP check, a FLAG, missing evidence, and a missing table. It also covers evidence from another snapshot or run, stale evidence, repeated evaluation, gate failure, recovery, and budget checks. These tests prove the logic. They do not replace a Databricks run. That run is still required before the gate is accepted.
