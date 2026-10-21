# Clean-workspace test

Issue #23 asks a non-builder to follow these steps in a new workspace. Every
step must work as written. Use this checklist and record the results below.

> [!IMPORTANT]
> **Cross-workspace reproduction completed.** The team confirms that the
> pipeline has run successfully in three separate Databricks Free Edition
> workspaces. This includes the team workspace and two independently configured
> workspaces. The October 14, 2026 run in Kinah's workspace started from the
> existing Bronze layer and completed Silver through Analytics on `main` at
> `1b75364`. On October 21, the 50-task Asset Bundle job then ran twice from
> setup through the dashboard in a separate Free Edition workspace. The two
> runs used the same source snapshot and produced identical gate counts, with
> zero failed STOP checks and zero missing checks.
>
> This evidence confirms cross-workspace and development-bundle
> reproducibility. Production binding and deployment remain post-merge
> operations. A successful `dev` run does not prove a `prod` deploy.

## Before you start

- A Databricks Free Edition workspace of your own. Don't use the team workspace, or the test proves nothing.
- One of these bundle deployment paths:
  - VS Code with the Databricks and Python extensions, plus the
    [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/install)
    0.278.0 or later
  - a Databricks Git folder with the **Deployments** pane enabled.
- The six source CSVs listed in the [notebooks guide](../../notebooks/README.md#before-running).

### Getting the source files

The team workspace reads the CSVs from Cloudflare R2 through the `cloudflare-r2` volume. A new workspace has no access to that bucket, and `00_setup_workspace` only checks the volume. It never creates it. So the tester needs a copy of the six files **from the team**. Ask Nadine. To grade without copying files, use read-only access to the team workspace instead. See [get the source data](data_access.md). The repository does not store data files (see [keep it safe](../../CONTRIBUTING.md#keep-it-safe)).

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
| 1 | Clone locally or create a Databricks Git folder from the repository | The repository opens at the intended branch | Passed through a separate-workspace Git folder |
| 2 | Select the `dev` target. With the CLI, authenticate to the new workspace. In Databricks, use the current workspace target | The deployment uses the new workspace | Passed. Job prefix: `[dev fnpc_work]` |
| 3 | Make the volume and upload the six CSVs, as above | `SHOW VOLUMES IN` `` `buildabida-capstone`.`00-source` `` lists `cloudflare-r2` | Passed. All source and Bronze tasks completed |
| 4 | Run `notebooks/00_setup/00_setup_workspace.sql` through the job | The schemas and volume exist | Passed in both runs |
| 5 | Run `notebooks/00_setup/01_check_sources.py` through the job | Six sources have status `OK` | Passed in both runs |
| 6 | Make a SQL warehouse, import the dashboard, and note both IDs | The dashboard opens and can be refreshed | Passed. The dashboard task succeeded |
| 7 | Validate `dev` with the selected warehouse and dashboard variables, using the CLI or Deployments pane | The bundle configuration validates | Passed as part of the successful UI deployment |
| 8 | Deploy `dev` with the CLI or **Deploy** in the Deployments pane | A job named `[dev <you>] buildabida-full-pipeline` appears | Passed. Job ID: `525182773840716` |
| 9 | Run the bundle job from the CLI or with **Run now** | All 50 tasks succeed | Passed. Run: `702857652434494` |
| 10 | Query `` `04-validation`.quality_gate_summary `` | `ALL` is `PASS` or `FLAG`, with no failed STOP checks | Passed with 0 failed STOP and 0 missing |
| 11 | Compare the gate with the [Analytics evidence](../evidence/analytics-2026-10-16/README.md) | The check contract agrees, unless approved source changes explain a difference | Passed with 566 passed checks and 109 flags |
| 12 | Run the job a second time without changes | All tasks succeed, and the gate shows the same counts | Passed. Run: `937376856057683` |
| 13 | Open the dashboard | Overview, three question pages, and Read Me show data | Passed. The dashboard task succeeded |
| 14 | Run the repository link check | Every repository link opens | Passed in PR #138 `Links` CI job |

Steps 6 to 13 were completed by the October 21 dev-bundle run. Step 14 is also
covered by the passing GitHub `Links` check on pull request #138. If a future
run fails, fix the documentation or code in a pull request and record the
affected step.

## Record

| Field | Value |
| --- | --- |
| Tester (not one of the builders) | Team member using an independently configured workspace |
| Date | October 21, 2026 |
| Commit | Branch `feat/productionize-governance`. `b6abb91` with the edits from `f79b9d6`, confirmed by the tester. See [deployed commit](../evidence/dev-bundle-2026-10-21/README.md#deployed-commit) |
| Workspace | Separate Databricks Free Edition workspace |
| Job | `[dev fnpc_work] buildabida-full-pipeline`, ID `525182773840716` |
| Job run IDs (first and second run) | `702857652434494` and `937376856057683` |
| Total time | 1h 11m 21s and 1h 19m 18s |
| Quality gate | Both `ALL` rows: FLAG, 566 pass, 109 flag, 0 failed STOP, 0 missing |
| Steps that failed, and the fix pull request | None in the two recorded complete runs |

The cross-workspace and development-bundle requirements for Issue #23 are
complete. See the [run IDs, gate export, and screenshots](../evidence/dev-bundle-2026-10-21/README.md).
The production target still requires the controlled bind and deploy described
in the [resources guide](../../resources/README.md#first-production-deploy-adopt-the-existing-job).
