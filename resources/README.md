# Resources

[`buildabida_full_pipeline.job.yml`](buildabida_full_pipeline.job.yml) is the Databricks job `buildabida-full-pipeline`, exported from the team workspace. It runs 49 tasks from setup to the dashboard refresh: Bronze, Silver, and Gold with every validation gate, the six Analytics views, `10_validation_analytics`, the acceptance evidence publisher, and the dashboard refresh. A task runs only after the tasks it depends on succeed, so a failed STOP gate stops everything after it.

The job reads the notebooks from `/Workspace/Shared/infra-project-monitoring/`. Sync that folder with the branch you want to run before you start the job.

The root `databricks.yml` sets up the VS Code Databricks project. It does not include this file, so `databricks bundle deploy` does not create a second copy of the job. To manage the job through the bundle instead, add `include: [resources/*.yml]` to `databricks.yml`, and change the notebook paths to paths relative to the bundle.

## Failure and recovery

When a task fails, Databricks skips every task that depends on it, so a failed STOP gate never lets a later layer run on bad data. The validators save their evidence before their STOP gate, so the failed checks stay readable in `04-validation`.

To recover, fix the cause, sync the workspace folder, and use **Repair run** on the failed job run. It reruns the failed task and every task after it, and keeps the tasks that already succeeded. The notebooks are safe to rerun: they replace or merge their outputs by deterministic keys.

This happened on October 16, 2026. The first attempts stopped on four Databricks SQL errors in the province notebooks. After the fixes, Repair 2 of the same job run finished with all 49 tasks succeeded.

## Runtime evidence

The job ran in full on October 16, 2026, in job run `1077732256280159`. See the [six Analytics views evidence](../docs/evidence/six-analytics-views/README.md).
