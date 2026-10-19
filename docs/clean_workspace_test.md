# Clean-workspace test

Issue #23 asks that someone who did not build the pipeline follows our steps in a new workspace, from start to finish, and that every step works as written. Use this checklist for that run, and record the results at the bottom.

> [!IMPORTANT]
> **Not done yet.** On October 14, 2026, Kinah ran the Silver to Analytics order in her own workspace on `main` at `1b75364`. Bronze was already loaded there, so that run did not cover setup, the source files, or Bronze. A full run by a non-builder is still open.

## Before you start

- A Databricks Free Edition workspace of your own. Don't use the team workspace, or the test proves nothing.
- VS Code with the Databricks and Python extensions. See [set up VS Code](vscode-setup.md).
- The [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/install), version 0.278.0 or later.
- The six source CSVs listed in the [notebooks guide](../notebooks/README.md#before-running).

### Getting the source files

The team workspace reads the CSVs from Cloudflare R2 through the `cloudflare-r2` volume. A new workspace has no access to that bucket, and `00_setup_workspace` only checks the volume. It never creates it. So the tester needs a copy of the six files **from the team**. Ask Nadine. The repository does not store data files (see [keep it safe](../CONTRIBUTING.md#keep-it-safe)).

Then make a managed volume with the same name, so every path in `src/config.py` stays the same:

```sql
CREATE CATALOG IF NOT EXISTS `buildabida-capstone`;
CREATE SCHEMA IF NOT EXISTS `buildabida-capstone`.`00-source`;
CREATE VOLUME IF NOT EXISTS `buildabida-capstone`.`00-source`.`cloudflare-r2`;
```

Upload the six files into `/Volumes/buildabida-capstone/00-source/cloudflare-r2/buildabida/` with **Catalog**, then the volume, then **Upload to this volume**. Keep the file names exactly as listed.

## Checklist

Write the result of each step, and the exact error if one fails.

| # | Step | Expected result | Result |
| --- | --- | --- | --- |
| 1 | Clone the repository and open it in VS Code | The folder opens, and VS Code suggests the two extensions | |
| 2 | Change the `host` line under `targets.dev` in `databricks.yml` to your workspace. Don't commit it | Sign-in works | |
| 3 | Make the volume and upload the six CSVs, as above | `SHOW VOLUMES IN` `` `buildabida-capstone`.`00-source` `` lists `cloudflare-r2` | |
| 4 | Run `notebooks/00_setup/00_setup_workspace.sql` as a workflow | The last cells list the schemas and the volume | |
| 5 | Run `notebooks/00_setup/01_check_sources.py` | Six rows with status `OK` | |
| 6 | Make a SQL warehouse, then import `dashboard/buildabida_infrastructure_project_monitoring.lvdash.json` as a dashboard. Note both IDs | The dashboard opens with empty charts | |
| 7 | `databricks bundle validate -t dev --var="warehouse_id=<id>" --var="dashboard_id=<id>"` | `Validation OK!` | |
| 8 | `databricks bundle deploy -t dev` with the same `--var` values | A job named `[dev <you>] buildabida-full-pipeline` appears | |
| 9 | `databricks bundle run -t dev buildabida_full_pipeline` with the same values | All 50 tasks succeed. Write down the run ID and the time it took | |
| 10 | Query `` `04-validation`.quality_gate_summary `` | The `ALL` row is `PASS` or `FLAG`, with no failed STOP checks | |
| 11 | Compare counts with the [six-view evidence](evidence/six-analytics-views/README.md) | Same checks and counts, unless the source files differ | |
| 12 | Run the job a second time without changes | All tasks succeed, and the gate shows the same counts | |
| 13 | Open the dashboard | All seven tabs show data | |
| 14 | Click every link in the README and the docs index | Every link opens | |

Steps 6 to 9 follow the current bundle setup, which has not run in a new workspace yet. If a step fails, fix the doc or the code in a pull request, and say which step.

## Record

| Field | Value |
| --- | --- |
| Tester (not one of the builders) | |
| Date | |
| Commit | |
| Workspace | Free Edition, own account |
| Job run IDs (first and second run) | |
| Total time | |
| Steps that failed, and the fix pull request | |

Issue #23 is done when every step passes as written, the fixes are merged, and this record is filled in.
