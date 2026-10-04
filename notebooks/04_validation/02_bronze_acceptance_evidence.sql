-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Bronze acceptance evidence
-- MAGIC
-- MAGIC ## Purpose
-- MAGIC
-- MAGIC Produce a compact, low-cost evidence set for the six-source Bronze pull request.
-- MAGIC The queries read only `load_log` and `dq_results`; they do not rescan the source
-- MAGIC files or the large Bronze tables.

-- COMMAND ----------

USE CATALOG `buildabida-capstone`;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Latest terminal load for every required source
-- MAGIC
-- MAGIC Capture this result with the Databricks run date and notebook URL. Every source
-- MAGIC should show `SUCCESS` or `SKIPPED_IDEMPOTENT`, a non-null snapshot ID, and a positive
-- MAGIC row count.

-- COMMAND ----------

WITH ranked_loads AS (
    SELECT
        source_name,
        table_name,
        snapshot_id,
        rows_loaded,
        status,
        source_path,
        source_version,
        started_at,
        completed_at,
        ROW_NUMBER() OVER (
            PARTITION BY table_name
            ORDER BY COALESCE(completed_at, started_at) DESC, run_id DESC
        ) AS row_number
    FROM `01-bronze`.load_log
    WHERE status IN ('SUCCESS', 'SKIPPED_IDEMPOTENT')
)
SELECT
    source_name,
    table_name,
    snapshot_id,
    rows_loaded,
    status,
    source_path,
    source_version,
    completed_at
FROM ranked_loads
WHERE row_number = 1
ORDER BY table_name;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Latest grouped validation summary
-- MAGIC
-- MAGIC A merge-safe result has no `ERROR` and no `FAIL` whose action is `stop`. `FLAG`
-- MAGIC rows remain visible because they describe source limitations for review or Silver.

-- COMMAND ----------

WITH latest_validation AS (
    SELECT run_id
    FROM `04-validation`.dq_results
    GROUP BY run_id
    ORDER BY MAX(run_ts) DESC
    LIMIT 1
)
SELECT
    table_name,
    status,
    action,
    COUNT(*) AS checks,
    SUM(COALESCE(failed_rows, 0)) AS reported_findings,
    MAX(run_ts) AS validation_time
FROM `04-validation`.dq_results
WHERE run_id = (SELECT run_id FROM latest_validation)
GROUP BY table_name, status, action
ORDER BY table_name, action, status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Acceptance checks and source-preservation findings
-- MAGIC
-- MAGIC This view includes the current row-count/snapshot reconciliation, repeated
-- MAGIC flood-control Contract IDs, Table C copy/provenance findings, and MGB category and
-- MAGIC geometry checks from the same validation run.

-- COMMAND ----------

WITH latest_validation AS (
    SELECT run_id
    FROM `04-validation`.dq_results
    GROUP BY run_id
    ORDER BY MAX(run_ts) DESC
    LIMIT 1
)
SELECT
    table_name,
    column,
    data_quality_check,
    failed_rows,
    total_rows,
    percentage,
    status,
    action,
    details,
    snapshot_id,
    run_ts
FROM `04-validation`.dq_results
WHERE run_id = (SELECT run_id FROM latest_validation)
  AND (
      data_quality_check IN (
          'Bronze row count matches latest load_log',
          'current Bronze snapshot matches load_log',
          'repeated Contract IDs are preserved for Silver review',
          'known BARMM duplicate rows are preserved',
          'original Table C row provenance is available',
          'flood-area geometry is not null or empty'
      )
      OR data_quality_check LIKE '%row count matches documented reference%'
      OR data_quality_check = 'missing-rating row count matches documented reference'
  )
ORDER BY table_name, data_quality_check;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Blocking-result gate
-- MAGIC
-- MAGIC This final query should return zero rows. Any returned row must be resolved or
-- MAGIC explicitly reviewed before Silver uses the selected Bronze snapshots.

-- COMMAND ----------

WITH latest_validation AS (
    SELECT run_id
    FROM `04-validation`.dq_results
    GROUP BY run_id
    ORDER BY MAX(run_ts) DESC
    LIMIT 1
)
SELECT *
FROM `04-validation`.dq_results
WHERE run_id = (SELECT run_id FROM latest_validation)
  AND (status = 'ERROR' OR (status = 'FAIL' AND action = 'stop'))
ORDER BY table_name, data_quality_check;
