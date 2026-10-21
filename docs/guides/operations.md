# Operations guide

How we run, watch, fix, and govern the pipeline in production. It follows the FTW path: **version, validate, deploy, orchestrate, monitor, recover, govern**.

| Step | What we use | Where |
| --- | --- | --- |
| Version | Git, one branch and one pull request per change | [How we work](../../CONTRIBUTING.md) |
| Validate | CI on every pull request, and the layer validators plus the end-to-end gate in every run | [Checks](../../.github/workflows/checks.yml), [validation](../validation/validation.md) |
| Deploy | Databricks Asset Bundle, `dev` and `prod` targets | [Resources](../../resources/README.md) |
| Orchestrate | One Databricks job, 50 tasks | [Job](../../resources/buildabida_full_pipeline.job.yml) |
| Monitor | Job run history, validation tables, the gate summary | [Monitor a run](#monitor-a-run) |
| Recover | Fix the cause, then **Repair run** | [Recover from a failure](#recover-from-a-failure) |
| Govern | CODEOWNERS, branch rules, GitHub environments | [GitHub governance](#github-governance) |

## Deploy and run

Deploying and running are separate on purpose. A deploy only updates the job definition and notebooks. A run uses compute, and the Free Edition workspace has one daily quota for the whole team.

| Situation | What happens |
| --- | --- |
| A pull request changes notebooks, `src`, or the bundle | [Databricks preview](../../.github/workflows/deploy-databricks-preview.yml) validates the `dev` bundle against the workspace. It deploys a preview copy only when `DATABRICKS_PREVIEW_DEPLOY` is `true`. It never runs the pipeline. |
| The change merges to `main` | [Databricks deploy](../../.github/workflows/deploy-databricks.yml) validates and deploys `prod`. It does not run the pipeline. |
| We want a production run | Start **Databricks deploy** by hand with **run_pipeline** checked, or select **Run now** on the job in Databricks. |
| You want to test your own change | `databricks bundle deploy -t dev`, then run your `[dev <name>]` copy of the job. |

The pipeline is not scheduled. A new run makes sense only when a source snapshot or the code changes. An automatic source refresh is out of scope (#129).

### GitHub configuration

First, add one **repository** variable under **Settings**, then **Secrets and variables**, then **Actions**, then **Variables**:

| Name | Value |
| --- | --- |
| `DATABRICKS_HOST` | `https://dbc-1a052b2e-8e60.cloud.databricks.com` |

It must be a repository variable, not an environment one. The preview job checks it before it enters an environment, and GitHub can't see environment values at that point. Until it exists, both **Databricks preview** and **Databricks deploy** are skipped, not failed, so a merge to `main` never deploys before the team is ready. The host is not a secret.

Set it last: create the environments, then bind the existing job (see [First production deploy](#first-production-deploy)), then add `DATABRICKS_HOST`. The first deploy after that updates the team job instead of creating a second one.

Then create two GitHub environments under **Settings**, then **Environments**: `development` and `production`. Each needs:

| Name | Kind | Value |
| --- | --- | --- |
| `DATABRICKS_ALERT_EMAIL` | Variable | The team address that gets failure emails |
| `DATABRICKS_TOKEN` | Secret | A token for the CI identity. Or use the next two instead |
| `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET` | Secrets | OAuth for a service principal, if the workspace allows one |
| `DATABRICKS_PREVIEW_DEPLOY` | Variable, `development` only | `true` to deploy previews. Leave it unset for validation only |

For `production`, limit **Deployment branches** to `main`, and add **Required reviewers** (Nadine and Kinah) if your GitHub plan offers it for this repository. Then no deploy reaches the team job without a person's approval.

Once `DATABRICKS_HOST` is set, a missing value makes the workflow fail on its first step and name what is missing. A pull request from a fork gets no secrets, so the preview skips it.

> [!NOTE]
> We have not yet confirmed that our Free Edition workspace allows a service principal or a personal access token for CI. Check **Settings**, then **Developer**, in the workspace before you add the secrets. Until then, leave `DATABRICKS_HOST` unset so both workflows skip, and deploy from VS Code or the CLI.

### First production deploy

The team job was created by hand before the bundle managed it. Bind it once so the first deploy updates it instead of creating a second job. The commands are in [resources](../../resources/README.md#first-production-deploy-adopt-the-existing-job).

## Failure alerts

The job emails `alert_email` when a run fails. It sends nothing for successful or skipped runs. In `prod` the address comes from `DATABRICKS_ALERT_EMAIL`. In `dev` it goes to the person who deployed.

A blocking check that fails goes like this:

1. The validator saves its evidence, then its `ASSERT_TRUE` gate fails the task.
2. Databricks skips every task that depends on it.
3. The end-to-end gate still runs (`run_if: ALL_DONE`), records the stale or failed evidence, and fails.
4. The dashboard refresh does not run.
5. The run fails, and Databricks sends one email.

To test the alert without breaking data, deploy to `dev`, then run only the gate task with **Run now with different settings**. Do it right after a Bronze-only reload, so the stale evidence makes it fail. Record the email in the evidence folder. The alert was first proven on October 19, 2026, when a real gate failure sent the email and skipped the dashboard. See the [end-to-end gate evidence](../evidence/end-to-end-gate-2026-10-19/README.md).

## Monitor a run

| Question | Where to look |
| --- | --- |
| Did the pipeline run, and did it succeed? | **Jobs and Pipelines**, then `buildabida-full-pipeline`, then **Runs** |
| Which task failed, and why? | The failed task's output in the run's task graph |
| Which validation stopped it? | `quality_gate_summary.failure_reason`, then the validator's results table |
| What snapshot was used? | `source_snapshot_id` in `quality_gate_summary` |
| Did Analytics pass? | The `analytics` row of `quality_gate_summary`, or `analytics_dq_results` |
| Did the end-to-end gate pass? | The `ALL` row of `quality_gate_summary` |
| Was the dashboard refreshed? | The `business_dashboard` task status in the run |
| Is the accepted data current? | See the freshness note below |

```sql
-- the last gate result, one row per layer plus ALL
SELECT layer, gate_status, required_checks, passed_checks, flagged_checks,
       failed_stop_checks, missing_checks, failure_reason, source_snapshot_id, job_run_id, evaluated_at
FROM `buildabida-capstone`.`04-validation`.quality_gate_summary
WHERE gate_run_id = (
    SELECT gate_run_id FROM `buildabida-capstone`.`04-validation`.quality_gate_results
    ORDER BY run_ts DESC LIMIT 1
)
ORDER BY layer;
```

**Freshness.** The gate proves the published data was validated in its own pipeline run. The team has **not** agreed when a DPWH snapshot becomes stale for users. There is no freshness SLA or alert. If the team sets one, add it as a FLAG in the gate first.

## Recover from a failure

Use this order every time: **detect, diagnose, impact, recover, verify**.

1. **Detect.** The failure email, or a red run in the job's run list.
2. **Diagnose.** Open the failed task. If it is a validator, read its saved rows, failures first:

   ```sql
   SELECT table_name, data_quality_check, status, action, failed_rows, total_rows, details
   FROM `buildabida-capstone`.`04-validation`.silver_dq_results  -- or gold_ or analytics_
   WHERE validation_run_id = '<evidence_validation_run_id from the gate>'
   ORDER BY CASE status WHEN 'FAIL' THEN 1 WHEN 'FLAG' THEN 2 ELSE 3 END;
   ```

3. **Impact.** Everything after the failed task was skipped, so the dashboard still shows the last data that passed. Nothing published is wrong. It is only not refreshed.
4. **Recover.** Fix the root cause in the layer where it started, in a pull request. After it merges, deploy, then use **Repair run** on the failed run. Repair reruns the failed task and every task after it, and keeps the ones that succeeded.
5. **Verify.** The repaired run is green, the gate's `ALL` row is `PASS` or `FLAG`, and the dashboard task succeeded.

Never edit a Gold or Analytics table by hand to make a check pass, and never mark a failed check as passed. If the source data is the problem, keep it visible as a FLAG with a decision in [decisions](../decisions.md). Don't hide it downstream.

The notebooks are safe to rerun. Bronze skips a snapshot it already holds, and the later layers `MERGE` or replace by deterministic keys. Validators update their rows under the same validation run ID.

### Incident record

Write every production failure up in the run's evidence folder with these four parts: **incident, problem, resolution, prevention**. Here is the real one from October 16, 2026:

| Part | What happened |
| --- | --- |
| Incident | Job run `1077732256280159` stopped on its first attempts in four province notebooks. Every later task was skipped, so no partial data was published. |
| Problem | Four Databricks SQL errors occurred. Two column names were ambiguous after a join. A `MERGE` dropped the geometry SRID. Spark SQL did not read a `''` escape as a quote. The notebooks had never run in a job before. |
| Resolution | Fixed in the workspace, ported to the repository with tests, then Repair 2 of the same run finished all 49 tasks. See the [evidence](../evidence/analytics-2026-10-16/README.md#runtime-fixes-found-by-this-run). |
| Prevention | The bundle now deploys exactly what is in `main`, so the workspace can't drift from the repository. CI checks the job and bundle on every pull request. |

## Rerun and idempotency evidence

| Claim | Evidence | Status |
| --- | --- | --- |
| Bronze skips an identical snapshot | `SKIPPED_IDEMPOTENT` in `load_log`, [Bronze evidence](../evidence/bronze-r2/README.md) | Proven |
| Gold reruns change nothing | Two runs on October 12 kept 75 checks under one ID, [validation](../validation/validation.md#gold-validation-runtime-evidence) | Proven |
| Analytics reruns change nothing | 111 saved checks unchanged on rerun, [Analytics evidence](../evidence/analytics-2026-10-16/README.md) | Proven |
| Province map reruns are exact | Same map run ID and checksum, [province evidence](../evidence/province-reporting/README.md) | Proven |
| Full job run twice with the gate gives the same result | Job runs `457335378856032` and `880939659105900` on October 19, 2026 gave the same gate result, totals, and validator run IDs, see the [end-to-end gate evidence](../evidence/end-to-end-gate-2026-10-19/README.md#rerun-on-unchanged-data) | Proven (#129) |

## GitHub governance

These are repository settings. A file can't turn them on, so an admin (Nadine) sets them in **Settings**, then **Rules**, then the `main` ruleset:

1. Keep **Require a pull request before merging** with one approval.
2. Turn on **Require review from Code Owners**. [CODEOWNERS](../../.github/CODEOWNERS) lists two owners for every path, so one absence doesn't block a merge. Every owner must have write access, or GitHub ignores the line.
3. Turn on **Require conversation resolution before merging**. Our [contributing rules](../../CONTRIBUTING.md) already ask for it.
4. Under **Require status checks to pass**, keep `Python (Ruff)`, `SQL (SQLFluff)`, `Markdown layout`, and `Links`. Add `Quality gate (Spark)` and `Databricks bundle (static)` after they pass once on `main`. A check can be required only after GitHub has seen it.
5. Turn on **Require branches to be up to date before merging**.
6. Keep **Block force pushes** and **Restrict deletions**. Don't add anyone to the bypass list.
7. In **Settings**, then **Advanced Security**, turn on **Secret scanning** and **Push protection** if the plan offers them.

## Governance at a glance

For each important dataset, we can answer five questions:

| Question | How |
| --- | --- |
| Can we **find** it? | Numbered schemas (`01-bronze` to `05-analytics`), numbered notebooks, and the [docs index](../README.md) |
| Can we **understand** it? | [Data model](../model/data-model.md), [Gold model](../model/gold_model.md), the layer docs, and a comment on every Analytics view and column |
| Can we **trust** it? | Layer validators, the [end-to-end gate](../../notebooks/06_data_quality/README.md), reconciliation checks, rerun evidence, and visible FLAG limits |
| Can we **control** it? | CODEOWNERS, branch rules, GitHub environments with reviewers, and bundle targets that keep `dev` away from `prod` |
| Can we **trace** it? | Snapshot IDs and run IDs on every Silver and Gold row (D-29), validation run IDs, `load_log`, and the gate's `job_run_id` |

Data access in Databricks (who can read which schema) is managed by Nadine in the team workspace (D-01). It is not set from this repository.

## Cost notes

- The job runs on serverless compute with `performance_target: PERFORMANCE_OPTIMIZED`, exported from the workspace. Standard mode may cost less. Test it on a `dev` copy before changing `prod`.
- The gate reads small evidence tables and a few columns of three project tables. It adds no spatial work.
- CI never runs Databricks compute. The Spark tests run on the GitHub runner with synthetic rows.
