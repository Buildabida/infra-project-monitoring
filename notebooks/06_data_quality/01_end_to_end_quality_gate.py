# Databricks notebook source
# MAGIC %md
# MAGIC # End-to-end quality gate
# MAGIC
# MAGIC ## Purpose
# MAGIC
# MAGIC Decide once, at the end of the pipeline, whether the current Gold and Analytics
# MAGIC data is safe to publish to the dashboard.
# MAGIC
# MAGIC The layer validators in `04_validation` check each layer. This notebook does not
# MAGIC repeat their checks. It reads the evidence they already saved and asks four questions:
# MAGIC
# MAGIC 1. Did every required validator save evidence, for every table it owns?
# MAGIC 2. Is that evidence newer than the latest Bronze load, so it describes this pipeline run?
# MAGIC 3. Did any STOP check fail? FLAG findings stay visible, but they do not block.
# MAGIC 4. Do the layers still agree with each other at publish time: one DPWH snapshot,
# MAGIC    the same project count and reported budget, and evidence for the current Gold runs?
# MAGIC
# MAGIC Missing evidence never counts as a pass.
# MAGIC
# MAGIC ## Outputs
# MAGIC
# MAGIC - `04-validation.quality_gate_results`: one row per gate check, saved with `MERGE`
# MAGIC   **before** the gate raises, so a failed gate stays readable.
# MAGIC - `04-validation.quality_gate_summary`: a view with one row per layer and one overall
# MAGIC   row per gate run.
# MAGIC
# MAGIC ## Cost
# MAGIC
# MAGIC The evidence tables hold a few thousand rows. The cross-layer checks read one Silver
# MAGIC table, the current Gold project rows, and one Analytics view once each, using only a
# MAGIC few columns. No spatial work, cache, or repartition.
# MAGIC
# MAGIC ## Step 1: Read the job run ID

# COMMAND ----------

import re

dbutils.widgets.text("job_run_id", "", "Databricks job run ID (set by the job)")
job_run_id = dbutils.widgets.get("job_run_id").strip()
# the job passes {{job.run_id}}; refuse anything else before it reaches SQL
if not re.fullmatch(r"\d*", job_run_id):
    raise ValueError(f"job_run_id must be digits or empty, got {job_run_id!r}")
job_run_literal = f"'{job_run_id}'" if job_run_id else "CAST(NULL AS STRING)"

gate_rule_version = "end-to-end-quality-gate-v1"

spark.sql("USE CATALOG `buildabida-capstone`")
spark.sql("CREATE SCHEMA IF NOT EXISTS `04-validation`")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: List the validators the gate requires
# MAGIC
# MAGIC **What:** one row per validator task in the pipeline job, with its results table, the
# MAGIC table that identifies its latest run (the anchor), and every table its run must cover.
# MAGIC
# MAGIC **Why:** the list is the contract. If a validator is removed, renamed, or stops
# MAGIC writing a table, the gate stops instead of passing on less evidence. The anchor is a
# MAGIC table that only that validator writes, so two validators never share a run.
# MAGIC
# MAGIC **When to change it:** in the same pull request that adds, removes, or renames a
# MAGIC validator or a validated table. `tests/test_quality_gate.py` checks that every
# MAGIC validator task in the job appears here.

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TEMPORARY VIEW gate_required_validations AS
SELECT * FROM VALUES
    ('bronze', 'bronze_validation', '04_validation/01_validation_bronze', 'dq_results', 'dpwh_projects',
        ARRAY('boundaries', 'census_2024_table_c', 'dpwh_projects', 'flood_control_projects',
              'flood_susceptibility', 'psgc')),
    ('silver', 'silver_validation_config_mappings', '04_validation/02_validation_silver_config',
        'silver_config_dq_results', 'config_place_name_alias', ARRAY('config_place_name_alias')),
    ('silver', 'silver_validation_geography_population',
        '04_validation/03_validation_silver_geography_population', 'silver_dq_results',
        'silver_region_population',
        ARRAY('silver_psgc_place', 'silver_population_place_reconciliation', 'silver_region_population')),
    ('silver', 'silver_validation_province_reporting', '04_validation/03b_validation_silver_province_reporting',
        'silver_dq_results', 'silver_project_province_map',
        ARRAY('silver_project_province_map', 'silver_province_reporting_area',
              'silver_province_reporting_area_population')),
    ('silver', 'silver_validation_projects', '04_validation/04_validation_silver_projects',
        'silver_dq_results', 'silver_dpwh_project_component',
        ARRAY('silver_dpwh_project_component', 'silver_project')),
    ('silver', 'silver_validation_source_reconciliation',
        '04_validation/05_validation_silver_source_reconciliation', 'silver_dq_results',
        'silver_project_source_match', ARRAY('silver_flood_control_component', 'silver_project_source_match')),
    ('silver', 'silver_validation_project_region_map', '04_validation/06_validation_silver_project_region_map',
        'silver_dq_results', 'silver_project_region_map', ARRAY('silver_project_region_map')),
    ('silver', 'silver_validation_mgb_flood_area', '04_validation/06a_validation_silver_mgb_flood_area',
        'silver_dq_results', 'silver_mgb_flood_area', ARRAY('silver_mgb_flood_area')),
    ('silver', 'silver_validation_region_flood_exposure',
        '04_validation/07_validation_silver_region_flood_exposure', 'silver_dq_results',
        'silver_region_flood_exposure', ARRAY('silver_region_flood_exposure')),
    ('silver', 'silver_validation_project_flood_map', '04_validation/08_validation_silver_project_flood_map',
        'silver_dq_results', 'silver_project_flood_map', ARRAY('silver_project_flood_map')),
    ('gold', 'gold_validation', '04_validation/09_validation_gold', 'gold_dq_results',
        'fact_region_flood_exposure',
        ARRAY('dim_date', 'dim_flood_susceptibility', 'dim_project', 'dim_project_status', 'dim_region',
              'dim_region_boundary', 'fact_project_snapshot', 'fact_region_flood_exposure',
              'fact_region_population')),
    ('gold', 'gold_validation_province_reporting', '04_validation/09a_validation_gold_province_reporting',
        'gold_dq_results', 'dim_province_reporting_area',
        ARRAY('dim_province_reporting_area', 'fact_project_snapshot', 'fact_province_reporting_area_population')),
    ('analytics', 'analytics_validation', '04_validation/10_validation_analytics', 'analytics_dq_results',
        'analytics_implementation_monitoring',
        ARRAY('analytics_investment_distribution', 'analytics_population_equity', 'analytics_flood_alignment',
              'analytics_implementation_monitoring', 'analytics_infrastructure_network',
              'analytics_integration_coverage', 'analytics_layer'))
AS required(layer, task_key, notebook, results_table, anchor_table, expected_tables)
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Read every validator's latest evidence
# MAGIC
# MAGIC **What:** put the five existing results tables into one shape, then find each
# MAGIC validator's latest run through its anchor table.
# MAGIC
# MAGIC **Why:** every validator saves all of its rows in one write stamped with one
# MAGIC `CURRENT_TIMESTAMP()` (Bronze appends, the others `MERGE`). So the anchor's newest
# MAGIC `run_ts` marks that validator's latest execution, and the rows with exactly that
# MAGIC `run_ts` are everything it saved then. Grouping by `run_ts`, not by run ID, matters:
# MAGIC a validator may give each of its tables its own `validation_run_id`, and the two
# MAGIC Gold validators both write `fact_project_snapshot` rows to the same table, at
# MAGIC different times. Only the columns the gate needs are read.

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TEMPORARY VIEW gate_evidence AS
SELECT
    'dq_results' AS results_table, run_id AS validation_run_id, CAST(NULL AS STRING) AS pipeline_run_id,
    table_name, snapshot_id AS source_snapshot_id, status, action, run_ts
FROM `04-validation`.dq_results
UNION ALL
SELECT
    'silver_config_dq_results', run_id, CAST(NULL AS STRING), table_name, CAST(NULL AS STRING),
    status, action, run_ts
FROM `04-validation`.silver_config_dq_results
UNION ALL
SELECT
    'silver_dq_results', validation_run_id, pipeline_run_id, table_name, source_snapshot_id,
    status, action, run_ts
FROM `04-validation`.silver_dq_results
UNION ALL
SELECT
    'gold_dq_results', validation_run_id, pipeline_run_id, table_name, source_snapshot_id,
    status, action, run_ts
FROM `04-validation`.gold_dq_results
UNION ALL
SELECT
    'analytics_dq_results', validation_run_id, pipeline_run_id, table_name, source_snapshot_id,
    status, action, run_ts
FROM `04-validation`.analytics_dq_results
""")

spark.sql("""
CREATE OR REPLACE TEMPORARY VIEW gate_latest_validation AS
WITH anchors AS (
    SELECT
        results_table,
        table_name,
        validation_run_id,
        run_ts,
        ROW_NUMBER() OVER (
            PARTITION BY results_table, table_name
            ORDER BY run_ts DESC, validation_run_id DESC
        ) AS evidence_rank
    FROM gate_evidence
)
SELECT
    required.*,
    anchors.validation_run_id,
    anchors.run_ts AS evidence_run_ts
FROM gate_required_validations AS required
LEFT JOIN anchors
    ON anchors.results_table = required.results_table
    AND anchors.table_name = required.anchor_table
    AND anchors.evidence_rank = 1
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Read the data that will be published
# MAGIC
# MAGIC **What:** one row with the latest Bronze load event, the latest DPWH load, the
# MAGIC Silver project totals, the current Gold project totals and fact runs, and the totals
# MAGIC of `analytics_implementation_monitoring` (one row per current project).
# MAGIC
# MAGIC **Why:** the cross-layer checks compare these. The gate run ID comes from the
# MAGIC validator run IDs and the data identities, so evaluating the same evidence twice
# MAGIC updates the same rows instead of adding copies (the D-52 rule).
# MAGIC
# MAGIC **Freshness rule:** evidence must be at least as new as the latest Bronze load event,
# MAGIC whatever its status. Every job run writes a Bronze load event, so this means "validated
# MAGIC in this pipeline run". After a Bronze-only reload, the gate stops until the later
# MAGIC layers are rebuilt and validated again.

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TEMPORARY VIEW gate_context AS
WITH bronze_events AS (
    SELECT MAX(COALESCE(completed_at, started_at)) AS latest_bronze_event_ts
    FROM `01-bronze`.load_log
    WHERE table_name IN (
        'boundaries', 'census_2024_table_c', 'dpwh_projects', 'flood_control_projects',
        'flood_susceptibility', 'psgc'
    )
),
dpwh_load AS (
    SELECT
        status AS bronze_dpwh_status,
        snapshot_id AS bronze_dpwh_snapshot_id
    FROM (
        SELECT
            status,
            snapshot_id,
            ROW_NUMBER() OVER (
                ORDER BY COALESCE(completed_at, started_at) DESC, started_at DESC
            ) AS event_rank
        FROM `01-bronze`.load_log
        WHERE table_name = 'dpwh_projects'
    )
    WHERE event_rank = 1
),
silver AS (
    SELECT
        COUNT(*) AS silver_projects,
        SUM(reported_budget_pesos) AS silver_budget_pesos,
        COUNT(reported_budget_pesos) AS silver_budget_projects,
        COUNT(DISTINCT source_snapshot_id) AS silver_snapshot_count,
        MAX(source_snapshot_id) AS silver_snapshot_id
    FROM `02-silver`.silver_project
),
gold AS (
    SELECT
        COUNT(*) AS gold_current_rows,
        COUNT(DISTINCT project_key) AS gold_current_projects,
        SUM(reported_budget_pesos) AS gold_budget_pesos,
        COUNT(reported_budget_pesos) AS gold_budget_projects,
        COUNT(DISTINCT source_snapshot_id) AS gold_snapshot_count,
        COUNT_IF(source_snapshot_id IS NULL) AS gold_snapshot_null_rows,
        MAX(source_snapshot_id) AS gold_snapshot_id,
        MAX(run_id) AS gold_project_run_id
    FROM `03-gold`.fact_project_snapshot
    WHERE is_current_snapshot
),
gold_runs AS (
    SELECT
        (SELECT MAX(run_id) FROM `03-gold`.fact_region_population) AS gold_population_run_id,
        (SELECT MAX(run_id) FROM `03-gold`.fact_region_flood_exposure) AS gold_exposure_run_id
),
analytics AS (
    SELECT
        COUNT(*) AS analytics_rows,
        COUNT(DISTINCT project_key) AS analytics_projects,
        SUM(reported_budget_pesos) AS analytics_budget_pesos,
        COUNT(reported_budget_pesos) AS analytics_budget_projects,
        COUNT(DISTINCT source_snapshot_id) AS analytics_snapshot_count,
        MAX(source_snapshot_id) AS analytics_snapshot_id
    FROM `05-analytics`.analytics_implementation_monitoring
),
validator_runs AS (
    SELECT SORT_ARRAY(COLLECT_LIST(CONCAT(task_key, ':', COALESCE(validation_run_id, 'NONE')))) AS runs
    FROM gate_latest_validation
)
SELECT
    bronze_events.*,
    dpwh_load.*,
    silver.*,
    gold.*,
    gold_runs.*,
    analytics.*,
    SHA2(CONCAT_WS(
        '|',
        validator_runs.runs,
        gold.gold_snapshot_id,
        gold.gold_project_run_id,
        gold_runs.gold_population_run_id,
        gold_runs.gold_exposure_run_id,
        '{gate_rule_version}'
    ), 256) AS gate_run_id
FROM bronze_events
CROSS JOIN silver
CROSS JOIN gold
CROSS JOIN gold_runs
CROSS JOIN analytics
CROSS JOIN validator_runs
LEFT JOIN dpwh_load ON TRUE
""")

display(spark.table("gate_context"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Check each validator's evidence
# MAGIC
# MAGIC **What:** one row per required validator. It fails when the evidence is missing,
# MAGIC misses a table, is older than the latest Bronze load event, or holds a blocking finding.
# MAGIC
# MAGIC **Blocking findings:** a `stop` check that is not `PASS`, any `ERROR`, or an
# MAGIC unknown action. A `flag` check with findings is non-blocking, including the two
# MAGIC October 16 `09a` rows saved as `FAIL` with action `flag`, which every existing
# MAGIC STOP gate also treats as non-blocking.
# MAGIC
# MAGIC **Result:** `FAIL` blocks publishing. `FLAG` means the evidence passed but carries known
# MAGIC data limits that must stay visible. `PASS` means no findings.

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TEMPORARY VIEW gate_validation_checks AS
WITH counted AS (
    SELECT
        latest.layer,
        latest.task_key,
        latest.notebook,
        latest.results_table,
        latest.expected_tables,
        latest.validation_run_id,
        latest.evidence_run_ts,
        COUNT(evidence.status) AS checks,
        COUNT_IF(evidence.status = 'PASS') AS passed_checks,
        COUNT_IF(evidence.action = 'flag' AND evidence.status IN ('FLAG', 'FAIL')) AS flagged_checks,
        COUNT_IF(
            evidence.status = 'ERROR'
            OR (evidence.action = 'stop' AND NOT evidence.status <=> 'PASS')
            OR (evidence.status IS NOT NULL AND NOT COALESCE(evidence.action IN ('stop', 'flag'), FALSE))
        ) AS failed_stop_checks,
        ARRAY_DISTINCT(COLLECT_LIST(evidence.table_name)) AS covered_tables
    FROM gate_latest_validation AS latest
    LEFT JOIN gate_evidence AS evidence
        ON evidence.results_table = latest.results_table
        AND evidence.run_ts = latest.evidence_run_ts
    GROUP BY ALL
),
judged AS (
    SELECT
        counted.*,
        context.latest_bronze_event_ts,
        context.gate_run_id,
        context.gold_snapshot_id,
        ARRAY_EXCEPT(counted.expected_tables, counted.covered_tables) AS missing_tables,
        COALESCE(counted.evidence_run_ts >= context.latest_bronze_event_ts, FALSE) AS is_current
    FROM counted
    CROSS JOIN gate_context AS context
)
SELECT
    gate_run_id,
    layer,
    task_key AS check_scope,
    'Latest validation evidence is present, current, and has no failed STOP check' AS data_quality_check,
    results_table,
    validation_run_id AS evidence_validation_run_id,
    evidence_run_ts,
    gold_snapshot_id AS source_snapshot_id,
    CAST(checks AS BIGINT) AS required_checks,
    CAST(passed_checks AS BIGINT) AS passed_checks,
    CAST(flagged_checks AS BIGINT) AS flagged_checks,
    CAST(failed_stop_checks AS BIGINT) AS failed_stop_checks,
    CAST(CASE WHEN is_current THEN SIZE(missing_tables) ELSE SIZE(expected_tables) END AS BIGINT)
        AS missing_checks,
    CASE
        WHEN validation_run_id IS NULL OR checks = 0 OR NOT is_current
            OR SIZE(missing_tables) > 0 OR failed_stop_checks > 0 THEN 'FAIL'
        WHEN flagged_checks > 0 THEN 'FLAG'
        ELSE 'PASS'
    END AS status,
    'stop' AS action,
    CONCAT_WS(
        '; ',
        CONCAT('Notebook ', notebook),
        CASE WHEN validation_run_id IS NULL THEN 'no saved evidence' END,
        CASE WHEN latest_bronze_event_ts IS NULL THEN 'no Bronze load event to compare with' END,
        CASE WHEN evidence_run_ts < latest_bronze_event_ts THEN CONCAT(
            'stale: evidence from ', CAST(evidence_run_ts AS STRING),
            ' is older than the latest Bronze load event at ', CAST(latest_bronze_event_ts AS STRING)
        ) END,
        CASE WHEN validation_run_id IS NOT NULL AND SIZE(missing_tables) > 0
            THEN CONCAT('missing tables: ', ARRAY_JOIN(missing_tables, ', ')) END,
        CASE WHEN failed_stop_checks > 0 THEN CONCAT(failed_stop_checks, ' blocking checks failed') END,
        CONCAT('checks=', checks, ', pass=', passed_checks, ', flag=', flagged_checks)
    ) AS details
FROM judged
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Check that the layers agree at publish time
# MAGIC
# MAGIC **What:** four STOP checks across layers.
# MAGIC
# MAGIC | Check | Why |
# MAGIC | --- | --- |
# MAGIC | One DPWH snapshot from Bronze to Analytics | The latest DPWH load, Silver, current Gold, and the Analytics view must name the same single snapshot (D-29). |
# MAGIC | Project count reconciles Silver, Gold, and Analytics | Every Silver project has one current Gold row and one Analytics row. This repeats the Gold fact grain at publish time. |
# MAGIC | Reported budget reconciles Silver, Gold, and Analytics | The headline budget total and the number of projects with a budget are the same in all three layers. The count catches a missing budget that turned into `0`, which a total alone cannot see. |
# MAGIC | Gold and Analytics evidence describe the current Gold runs | The latest `09_validation_gold` rows name the current run of each fact, and the latest `10_validation_analytics` rows name the current project run and snapshot. A table rebuilt after its validation stops the gate. |
# MAGIC
# MAGIC The run-ID bindings are the ones `09_validation_gold` and `10_validation_analytics`
# MAGIC already record, so no run-ID recipe is copied here.

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TEMPORARY VIEW gate_cross_layer_checks AS
WITH gold_evidence AS (
    SELECT
        COUNT_IF(
            (evidence.table_name = 'fact_project_snapshot' AND evidence.pipeline_run_id = context.gold_project_run_id)
            OR (evidence.table_name = 'fact_region_population'
                AND evidence.pipeline_run_id = context.gold_population_run_id)
            OR (evidence.table_name = 'fact_region_flood_exposure'
                AND evidence.pipeline_run_id = context.gold_exposure_run_id)
        ) AS matching_rows,
        COUNT(DISTINCT CASE
            WHEN (evidence.table_name = 'fact_project_snapshot'
                    AND evidence.pipeline_run_id = context.gold_project_run_id)
                OR (evidence.table_name = 'fact_region_population'
                    AND evidence.pipeline_run_id = context.gold_population_run_id)
                OR (evidence.table_name = 'fact_region_flood_exposure'
                    AND evidence.pipeline_run_id = context.gold_exposure_run_id)
            THEN evidence.table_name
        END) AS matching_facts
    FROM gate_latest_validation AS latest
    INNER JOIN gate_evidence AS evidence
        ON evidence.results_table = latest.results_table
        AND evidence.run_ts = latest.evidence_run_ts
    CROSS JOIN gate_context AS context
    WHERE latest.task_key = 'gold_validation'
),
analytics_evidence AS (
    SELECT
        COUNT(*) AS rows_checked,
        COUNT_IF(
            evidence.pipeline_run_id <=> context.gold_project_run_id
            AND evidence.source_snapshot_id <=> context.gold_snapshot_id
        ) AS matching_rows
    FROM gate_latest_validation AS latest
    INNER JOIN gate_evidence AS evidence
        ON evidence.results_table = latest.results_table
        AND evidence.run_ts = latest.evidence_run_ts
    CROSS JOIN gate_context AS context
    WHERE latest.task_key = 'analytics_validation'
        AND evidence.table_name = 'analytics_implementation_monitoring'
),
checks AS (
    SELECT INLINE(ARRAY(
        NAMED_STRUCT(
            'check_scope', 'dpwh_snapshot_lineage',
            'check_name', 'One DPWH snapshot from Bronze to Analytics',
            'failed', CAST(CASE
                WHEN context.bronze_dpwh_status IN ('SUCCESS', 'SKIPPED_IDEMPOTENT')
                    AND context.silver_snapshot_count = 1
                    AND context.gold_snapshot_count = 1
                    AND context.gold_snapshot_null_rows = 0
                    AND context.analytics_snapshot_count = 1
                    AND context.bronze_dpwh_snapshot_id = context.silver_snapshot_id
                    AND context.silver_snapshot_id = context.gold_snapshot_id
                    AND context.gold_snapshot_id = context.analytics_snapshot_id
                THEN 0 ELSE 1
            END AS BIGINT),
            'details', CONCAT(
                'Bronze ', COALESCE(context.bronze_dpwh_status, 'NO LOAD'), ' ',
                COALESCE(context.bronze_dpwh_snapshot_id, 'NULL'),
                ', Silver ', COALESCE(context.silver_snapshot_id, 'NULL'),
                ' (', context.silver_snapshot_count, ' snapshots)',
                ', Gold ', COALESCE(context.gold_snapshot_id, 'NULL'),
                ' (', context.gold_snapshot_count, ' snapshots, ', context.gold_snapshot_null_rows, ' empty)',
                ', Analytics ', COALESCE(context.analytics_snapshot_id, 'NULL'),
                ' (', context.analytics_snapshot_count, ' snapshots)'
            )
        ),
        NAMED_STRUCT(
            'check_scope', 'project_count_reconciliation',
            'check_name', 'Project count reconciles Silver, Gold, and Analytics',
            'failed', CAST(
                ABS(context.gold_current_rows - context.silver_projects)
                + ABS(context.analytics_rows - context.gold_current_rows)
                + (context.gold_current_rows - context.gold_current_projects)
                + (context.analytics_rows - context.analytics_projects)
            AS BIGINT),
            'details', CONCAT(
                'Silver projects=', context.silver_projects,
                ', Gold current rows=', context.gold_current_rows,
                ' (', context.gold_current_projects, ' projects)',
                ', Analytics rows=', context.analytics_rows,
                ' (', context.analytics_projects, ' projects)'
            )
        ),
        NAMED_STRUCT(
            'check_scope', 'reported_budget_reconciliation',
            'check_name', 'Reported budget reconciles Silver, Gold, and Analytics',
            'failed', CAST(
                CASE WHEN context.silver_budget_pesos <=> context.gold_budget_pesos
                    AND context.silver_budget_projects = context.gold_budget_projects THEN 0 ELSE 1 END
                + CASE WHEN context.gold_budget_pesos <=> context.analytics_budget_pesos
                    AND context.gold_budget_projects = context.analytics_budget_projects THEN 0 ELSE 1 END
            AS BIGINT),
            'details', CONCAT(
                'Reported budget, not payment (D-28). Silver=',
                COALESCE(CAST(context.silver_budget_pesos AS STRING), 'NULL'),
                ', Gold=', COALESCE(CAST(context.gold_budget_pesos AS STRING), 'NULL'),
                ', Analytics=', COALESCE(CAST(context.analytics_budget_pesos AS STRING), 'NULL'),
                '. Projects with a budget: Silver=', context.silver_budget_projects,
                ', Gold=', context.gold_budget_projects, ', Analytics=', context.analytics_budget_projects
            )
        ),
        NAMED_STRUCT(
            'check_scope', 'evidence_matches_current_gold',
            'check_name', 'Gold and Analytics evidence describe the current Gold runs',
            'failed', CAST(
                (3 - COALESCE(gold_evidence.matching_facts, 0))
                + CASE
                    WHEN analytics_evidence.rows_checked > 0
                        AND analytics_evidence.matching_rows = analytics_evidence.rows_checked
                    THEN 0 ELSE 1
                END
            AS BIGINT),
            'details', CONCAT(
                'Gold facts with evidence for the current run=', COALESCE(gold_evidence.matching_facts, 0),
                ' of 3; Analytics rows naming the current project run and snapshot=',
                COALESCE(analytics_evidence.matching_rows, 0), ' of ', COALESCE(analytics_evidence.rows_checked, 0)
            )
        )
    )) AS (check_scope, check_name, failed, details)
    FROM gate_context AS context
    CROSS JOIN gold_evidence
    CROSS JOIN analytics_evidence
)
SELECT
    context.gate_run_id,
    'end_to_end' AS layer,
    checks.check_scope,
    checks.check_name AS data_quality_check,
    CAST(NULL AS STRING) AS results_table,
    CAST(NULL AS STRING) AS evidence_validation_run_id,
    CAST(NULL AS TIMESTAMP) AS evidence_run_ts,
    context.gold_snapshot_id AS source_snapshot_id,
    CAST(1 AS BIGINT) AS required_checks,
    CAST(CASE WHEN checks.failed = 0 THEN 1 ELSE 0 END AS BIGINT) AS passed_checks,
    CAST(0 AS BIGINT) AS flagged_checks,
    CAST(CASE WHEN checks.failed = 0 THEN 0 ELSE 1 END AS BIGINT) AS failed_stop_checks,
    CAST(0 AS BIGINT) AS missing_checks,
    CASE WHEN checks.failed = 0 THEN 'PASS' ELSE 'FAIL' END AS status,
    'stop' AS action,
    checks.details
FROM checks
CROSS JOIN gate_context AS context
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Save the gate result before deciding
# MAGIC
# MAGIC **What:** `MERGE` every gate row into `04-validation.quality_gate_results`, keyed by
# MAGIC the gate run ID, scope, and check. Then refresh the summary view.
# MAGIC
# MAGIC **Why:** the result stays readable after the gate stops the job. Evaluating the same
# MAGIC evidence again updates the same rows, so reruns never add copies.

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS `04-validation`.quality_gate_results (
    gate_run_id STRING NOT NULL,
    job_run_id STRING,
    layer STRING NOT NULL,
    check_scope STRING NOT NULL,
    data_quality_check STRING NOT NULL,
    results_table STRING,
    evidence_validation_run_id STRING,
    evidence_run_ts TIMESTAMP,
    source_snapshot_id STRING,
    required_checks BIGINT,
    passed_checks BIGINT,
    flagged_checks BIGINT,
    failed_stop_checks BIGINT,
    missing_checks BIGINT,
    status STRING NOT NULL,
    action STRING NOT NULL,
    details STRING,
    rule_version STRING NOT NULL,
    run_ts TIMESTAMP NOT NULL
)
USING DELTA
COMMENT 'End-to-end quality gate. One row per gate check per gate run. Written before the gate decides.'
""")

spark.sql(f"""
MERGE INTO `04-validation`.quality_gate_results AS target
USING (
    SELECT
        gate_run_id, {job_run_literal} AS job_run_id, layer, check_scope, data_quality_check,
        results_table, evidence_validation_run_id, evidence_run_ts, source_snapshot_id,
        required_checks, passed_checks, flagged_checks, failed_stop_checks, missing_checks,
        status, action, details, '{gate_rule_version}' AS rule_version, CURRENT_TIMESTAMP() AS run_ts
    FROM (
        SELECT * FROM gate_validation_checks
        UNION ALL
        SELECT * FROM gate_cross_layer_checks
    )
) AS source
ON target.gate_run_id = source.gate_run_id
    AND target.check_scope = source.check_scope
    AND target.data_quality_check = source.data_quality_check
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
""")

spark.sql("""
CREATE OR REPLACE VIEW `04-validation`.quality_gate_summary
COMMENT 'One row per layer and one ALL row per end-to-end gate run. gate_status is PASS, FLAG, or STOP.'
AS
SELECT
    gate_run_id,
    MAX(job_run_id) AS job_run_id,
    MAX(run_ts) AS evaluated_at,
    MAX(source_snapshot_id) AS source_snapshot_id,
    COALESCE(layer, 'ALL') AS layer,
    SUM(required_checks) AS required_checks,
    SUM(passed_checks) AS passed_checks,
    SUM(flagged_checks) AS flagged_checks,
    SUM(failed_stop_checks) AS failed_stop_checks,
    SUM(missing_checks) AS missing_checks,
    CASE
        WHEN COUNT_IF(status <> 'PASS' AND status <> 'FLAG') > 0 THEN 'STOP'
        WHEN COUNT_IF(status = 'FLAG') > 0 THEN 'FLAG'
        ELSE 'PASS'
    END AS gate_status,
    NULLIF(CONCAT_WS('; ', COLLECT_LIST(CASE
        WHEN status <> 'PASS' AND status <> 'FLAG' THEN CONCAT(check_scope, ': ', details)
    END)), '') AS failure_reason
FROM `04-validation`.quality_gate_results
GROUP BY GROUPING SETS ((gate_run_id, layer), (gate_run_id))
""")

gate_run_id = spark.table("gate_context").first()["gate_run_id"]
summary = spark.sql(
    "SELECT * FROM `04-validation`.quality_gate_summary WHERE gate_run_id = :gate_run_id",
    args={"gate_run_id": gate_run_id},
)
display(summary)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8: The gate
# MAGIC
# MAGIC The task fails here when any gate check is `FAIL`, or when nothing was saved. The
# MAGIC dashboard refresh depends on this task, so it never runs on data that failed.
# MAGIC `FLAG` rows do not block, and they stay in the summary.

# COMMAND ----------

results = spark.sql(
    """
    SELECT layer, check_scope, status, details
    FROM `04-validation`.quality_gate_results
    WHERE gate_run_id = :gate_run_id
    ORDER BY layer, check_scope
    """,
    args={"gate_run_id": gate_run_id},
).collect()
blocked = [row for row in results if row["status"] not in {"PASS", "FLAG"}]
if not results or blocked:
    raise RuntimeError(
        f"STOP: end-to-end quality gate {gate_run_id} blocked publishing. "
        + (
            "; ".join(f"{row['check_scope']}: {row['details']}" for row in blocked)
            or "no gate result was saved"
        )
    )
flagged = sum(row["status"] == "FLAG" for row in results)
print(
    f"Quality gate {gate_run_id}: PASS with {flagged} validators carrying visible FLAG findings."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC The gate adds no new layer check. It proves that every required validator ran for
# MAGIC this pipeline run and passed, that the layers agree on snapshot, count, and budget at
# MAGIC publish time, and it saves one readable result before it lets the dashboard refresh.
# MAGIC See `notebooks/06_data_quality/README.md` for how to read and rerun it.
