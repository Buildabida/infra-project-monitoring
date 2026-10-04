# Databricks notebook source
# MAGIC %md
# MAGIC # Run Source → Bronze → Bronze validation
# MAGIC
# MAGIC Runs setup validation, all six independent Bronze loads, then validation. An exact
# MAGIC completed snapshot may return `SKIPPED_IDEMPOTENT`; that is safe and does not block
# MAGIC validation. A failed source always blocks validation even if an older table exists.

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


def run_step(step, parameters=None):
    """Run a child notebook and retain a concise result for the final table."""
    try:
        return dbutils.notebook.run(f"./{step}", 0, parameters or {}) or "SUCCESS"
    except Exception as error:  # noqa: BLE001 - report every source failure together
        return "FAILED: " + str(error).strip().splitlines()[0][:500]


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

display(spark.createDataFrame(results, "step string, result string"))
failed = [step for step, result in results if result.startswith(("FAILED", "BLOCKED"))]
if failed:
    raise RuntimeError("Pipeline did not finish: " + ", ".join(failed))
