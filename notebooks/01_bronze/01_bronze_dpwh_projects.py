# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # Bronze: DPWH projects from R2
# MAGIC
# MAGIC ## Purpose
# MAGIC
# MAGIC Preserve one selected `dpwh_projects.csv` snapshot in
# MAGIC `01-bronze.dpwh_projects`. One Bronze row remains one exported DPWH project row.
# MAGIC Contract, budget, status, progress, office/location, date, and coordinate values
# MAGIC stay as source strings; interpretation and correction belong in Silver.
# MAGIC
# MAGIC ## Why this design
# MAGIC
# MAGIC - **Batch-based:** one bounded CSV snapshot is handled at a time.
# MAGIC - **Idempotent:** the same current artifact is verified and skipped without adding rows.
# MAGIC - **Parameterized:** shared widgets supply snapshot, version, reload, and path choices.
# MAGIC - **Snapshot-aware:** every row and audit event carries artifact and attempt metadata.
# MAGIC - **Low cost:** metadata and headers are checked before Spark reads the full CSV.
# MAGIC
# MAGIC The shared loader also protects the last complete Delta version, checks a documented
# MAGIC project-key alias before replacement, preserves every source row, and records the
# MAGIC source-to-Bronze row count.
# MAGIC
# MAGIC ## Step 1 — Define the batch parameters
# MAGIC
# MAGIC The notebook exposes only source-specific choices. Catalog, schema, table, default
# MAGIC path, metadata rules, conflict handling, and Delta mechanics stay centralized.

# COMMAND ----------

import importlib
import json
import os
import sys

repo_root = os.path.abspath("../..")
sys.path.insert(0, repo_root)

from src import bronze, config

dbutils.widgets.text("snapshot_id", "", "Snapshot ID (blank = source metadata)")
dbutils.widgets.text("source_version", "", "Optional publisher/source version")
dbutils.widgets.dropdown("force_reload", "false", ["false", "true"], "Force identical snapshot reload")
dbutils.widgets.text("source_path", "", "Optional source path override")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Resolve the DPWH source contract
# MAGIC
# MAGIC `source_config` supplies the approved file name, target table, source system,
# MAGIC grain, provenance statement, and accepted project-key aliases. A controlled path
# MAGIC override changes only the selected artifact; it does not duplicate path logic.

# COMMAND ----------

source = config.source_config("dpwh_projects")
source["path"] = dbutils.widgets.get("source_path").strip() or source["path"]
source["source_version"] = dbutils.widgets.get("source_version").strip() or None

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Preserve the selected snapshot
# MAGIC
# MAGIC The shared loader verifies file/header contracts, derives or accepts a snapshot ID,
# MAGIC checks the current Delta table before an idempotent skip, reads all business columns
# MAGIC as strings with `FAILFAST`, adds technical lineage, atomically replaces the selected
# MAGIC snapshot, reconciles row counts, and appends a concise status to `load_log`.

# COMMAND ----------

import importlib
importlib.reload(bronze)

result = bronze.load_csv_snapshot(
    spark,
    source,
    snapshot_id=dbutils.widgets.get("snapshot_id"),
    force_reload=dbutils.widgets.get("force_reload"),
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC The resulting table is a traceable raw DPWH snapshot. No project categories,
# MAGIC geographic corrections, status normalization, numeric casts, filtering,
# MAGIC aggregation, or business deduplication are applied in Bronze.

# COMMAND ----------

print(json.dumps(result, sort_keys=True))
dbutils.notebook.exit(json.dumps(result, sort_keys=True))
