# Resources

[`buildabida_full_pipeline.job.yml`](buildabida_full_pipeline.job.yml) is the Databricks job `buildabida-full-pipeline`. It runs 50 tasks from setup to the dashboard refresh:

1. Bronze, Silver, and Gold, each with its validation gates
2. the six Analytics views and `10_validation_analytics`
3. the acceptance evidence publisher
4. the [end-to-end quality gate](../notebooks/06_data_quality/README.md)
5. the dashboard refresh

A task runs only after the tasks it depends on succeed, so a failed STOP gate stops everything after it.

The root [`databricks.yml`](../databricks.yml) includes this file, so `databricks bundle deploy` creates and updates the job, and uploads the notebooks it runs. The job reads notebooks from the bundle's own folder, not from a hand-synced `/Workspace/Shared` folder.

## Job settings

| Setting | Value | Why |
| --- | --- | --- |
| `max_concurrent_runs` | 1 | Every layer replaces or merges the same tables, so two runs at once could mix data |
| `queue` | enabled | A second start waits instead of being dropped |
| `timeout_seconds` | 14400 (4 hours) | A hung run stops instead of using the daily serverless quota. The longest task on October 16 took 28m 32s |
| `email_notifications.on_failure` | `${var.alert_email}` | One email when a run fails. No email for successful or skipped runs |
| `end_to_end_quality_gate` | `run_if: ALL_DONE` | Records why a run stopped, even after an earlier failure. It fails unless everything passed |
| `business_dashboard` | waits for the gate, the analytics validator, and the evidence publisher | The dashboard can never refresh on data that failed |

## Targets and variables

| Target | Who deploys it | Where it goes | Job name |
| --- | --- | --- | --- |
| `dev` (default) | Any team member, from VS Code or the CLI | Their own home folder | `[dev <name>] buildabida-full-pipeline`, schedules paused |
| `prod` | The [deploy workflow](../.github/workflows/deploy-databricks.yml) on `main`, or Nadine | `/Workspace/Shared/infra-project-monitoring/.bundle/prod` | `buildabida-full-pipeline` |

Development mode gives every person a separate, prefixed copy, so a dev deploy can't overwrite the production job.

| Variable | Default | Set it when |
| --- | --- | --- |
| `warehouse_id` | The team SQL warehouse | You deploy to another workspace, like the clean-workspace test |
| `dashboard_id` | The team dashboard | Same as above |
| `alert_email` | The deploying user in `dev`. No default in `prod` | Always for `prod`. GitHub passes `DATABRICKS_ALERT_EMAIL` |

Override any variable with `--var name=value` or the environment variable `BUNDLE_VAR_<name>`.

## Deploy

```bash
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run -t dev buildabida_full_pipeline   # only when you mean to use compute
```

### First production deploy: adopt the existing job

The team job already exists in the workspace. It was created by hand before the bundle managed it. Bind it once, so the first `prod` deploy updates it instead of creating a second job:

```bash
databricks jobs list --name buildabida-full-pipeline           # note the job_id
databricks bundle deployment bind buildabida_full_pipeline <job_id> -t prod --var alert_email=<team address>
databricks bundle deploy -t prod --var alert_email=<team address>
```

> [!NOTE]
> Not tested yet: the bundle has not been validated or deployed against the workspace. The October 19, 2026 runs used the job created by hand, with notebooks under `/Workspace/Shared/infra-project-monitoring/`. Before the first `prod` deploy, run `databricks bundle validate -t dev`, then `databricks bundle deploy -t dev`, and run the dev copy once. Record the result here.

After the bind, the old `/Workspace/Shared/infra-project-monitoring/` notebook folder is no longer used by the job. Keep it until one production run passes, then remove it.

## Failure and recovery

When a task fails, Databricks skips every task that depends on it, so a failed STOP gate never lets a later layer run on bad data. The validators save their evidence before their STOP gate, so the failed checks stay readable in `04-validation`. The end-to-end gate still runs and writes `04-validation.quality_gate_summary`, so one query shows which validator stopped the run.

To recover, fix the cause, deploy the fix, and use **Repair run** on the failed job run. It reruns the failed task and every task after it, and keeps the tasks that already succeeded. The notebooks are safe to rerun: they replace or merge their outputs by deterministic keys. The full steps are in the [operations guide](../docs/guides/operations.md).

This happened on October 16, 2026. The first attempts stopped on four Databricks SQL errors in the province notebooks. After the fixes, Repair 2 of the same job run finished with all 49 tasks succeeded. That run was before the end-to-end gate existed.

## Runtime evidence

The 49-task job ran in full on October 16, 2026, in job run `1077732256280159`. See the [six Analytics views evidence](../docs/evidence/six-analytics-views/README.md).

The 50-task job with the end-to-end gate first ran on October 19, 2026, in job run `457335378856032`. Its first attempt stopped at the gate because of a gate bug, which was fixed. The repaired run passed. See the [end-to-end gate evidence](../docs/evidence/end-to-end-gate-2026-10-19/README.md). A second run on unchanged data, job run `880939659105900`, gave the same gate result and totals.
