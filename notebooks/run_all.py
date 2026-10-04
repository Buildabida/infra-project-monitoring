# Databricks notebook source
# MAGIC %md
# MAGIC # Run Source → Bronze → Bronze validation
# MAGIC
# MAGIC ## Purpose
# MAGIC
# MAGIC Coordinate the complete Source-to-Bronze batch in one explicit order:
# MAGIC
# MAGIC 1. establish the workspace and source-volume contract;
# MAGIC 2. preserve each of the six independent source snapshots;
# MAGIC 3. apply grouped Bronze validation only when every source result is safe.
# MAGIC
# MAGIC ## Why this orchestration stays simple
# MAGIC
# MAGIC Databricks notebook tasks are enough for six batch sources. The coordinator adds no
# MAGIC streaming service, scheduler framework, queue, or hidden state. Each source notebook
# MAGIC owns only its source contract; shared ingestion mechanics stay in `src/bronze.py`.
# MAGIC
# MAGIC ## Batch result contract
# MAGIC
# MAGIC `SUCCESS` means a selected snapshot was committed and audited.
# MAGIC `SKIPPED_IDEMPOTENT` means the current table and artifact identity were verified and
# MAGIC no replacement was needed. Any other result blocks validation, so an older table
# MAGIC cannot hide a failed current source attempt.
# MAGIC
# MAGIC ## Step 1 — Define shared parameters and ordered tasks

# COMMAND ----------

import json

dbutils.widgets.text("snapshot_id", "", "Snapshot ID for all sources (blank = per-file metadata)")
dbutils.widgets.text("source_version", "", "Optional shared publisher/source version")
dbutils.widgets.dropdown("force_reload", "false", ["false", "true"], "Force identical snapshot reload")

setup_step = "00_setup/00_setup_workspace"
source_steps = [
    "01_bronze/01_bronze_dpwh_projects",
    "01_bronze/02_bronze_flood_control",
    "01_bronze/03_bronze_psgc",
    "01_bronze/04_bronze_census_table_c",
    "01_bronze/05_bronze_boundaries",
    "01_bronze/06_bronze_flood_susceptibility",
]
validation_step = "04_validation/01_validation_bronze"
arguments = {
    "snapshot_id": dbutils.widgets.get("snapshot_id"),
    "source_version": dbutils.widgets.get("source_version"),
    "force_reload": dbutils.widgets.get("force_reload"),
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Capture each child result without hiding failures
# MAGIC
# MAGIC The wrapper converts a notebook exception into a short result for the final status
# MAGIC table. It does not treat the exception as success. This allows all independent
# MAGIC source problems to be visible together while preserving a blocking final outcome.

# COMMAND ----------


def run_step(step, parameters=None):
    """Run a child notebook and retain a concise result for the final table."""
    try:
        return dbutils.notebook.run(f"./{step}", 0, parameters or {}) or "SUCCESS"
    except Exception as error:  # noqa: BLE001 - report every source failure together
        return "FAILED: " + str(error).strip().splitlines()[0][:500]


# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Verify setup, load six sources, then gate validation
# MAGIC
# MAGIC Setup must succeed first. Source notebooks remain independent, so one failure does
# MAGIC not erase the status of the other sources. Validation is added only when all six
# MAGIC return a safe terminal status.

# COMMAND ----------

results = []
setup_result = run_step(setup_step)
results.append((setup_step, setup_result))
if setup_result.startswith("FAILED"):
    display(spark.createDataFrame(results, "step string, result string"))
    raise RuntimeError(f"Setup did not finish: {setup_result}")

source_ok = True
for step in source_steps:
    result = run_step(step, arguments)
    results.append((step, result))
    try:
        status = json.loads(result)["status"]
    except (json.JSONDecodeError, KeyError, TypeError):
        status = "FAILED"
    if status not in {"SUCCESS", "SKIPPED_IDEMPOTENT"}:
        source_ok = False

if source_ok:
    results.append((validation_step, run_step(validation_step)))
else:
    results.append((validation_step, "BLOCKED: this orchestration run has a failed source"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 — Publish the batch summary
# MAGIC
# MAGIC The compact status table names every setup, source, and validation step. A final
# MAGIC blocking exception preserves failure visibility for jobs and reviewers.

# COMMAND ----------

display(spark.createDataFrame(results, "step string, result string"))
failed = [step for step, result in results if result.startswith(("FAILED", "BLOCKED"))]
if failed:
    raise RuntimeError("Pipeline did not finish: " + ", ".join(failed))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC The coordinator is batch-based, parameterized, and fail-closed. It accepts an
# MAGIC idempotent skip as safe, requires all six sources, and keeps validation downstream
# MAGIC of the complete current batch.
