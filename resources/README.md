# Resources

[`buildabida_full_pipeline.job.yml`](buildabida_full_pipeline.job.yml) is the Databricks job `buildabida-full-pipeline`, exported from the team workspace. It runs 49 tasks from setup to the dashboard refresh: Bronze, Silver, and Gold with every validation gate, the six Analytics views, `10_validation_analytics`, the acceptance evidence publisher, and the dashboard refresh. A task runs only after the tasks it depends on succeed, so a failed STOP gate stops everything after it.

The job reads the notebooks from `/Workspace/Shared/infra-project-monitoring/`. Sync that folder with the branch you want to run before you start the job.

The root `databricks.yml` sets up the VS Code Databricks project. It does not include this file, so `databricks bundle deploy` does not create a second copy of the job. To manage the job through the bundle instead, add `include: [resources/*.yml]` to `databricks.yml`, and change the notebook paths to paths relative to the bundle.

The job ran in full on October 16, 2026, in job run `1077732256280159`. See the [six Analytics views evidence](../docs/evidence/six-analytics-views/README.md).
