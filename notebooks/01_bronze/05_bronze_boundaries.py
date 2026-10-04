# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # Bronze: boundaries from R2
# MAGIC
# MAGIC ## Purpose
# MAGIC
# MAGIC Preserve one selected `boundary_bettergov.csv` snapshot in
# MAGIC `01-bronze.boundaries`. One Bronze row remains one exported geographic shape, and
# MAGIC geometry remains in the CSV's source representation.
# MAGIC
# MAGIC ## Source-of-truth boundary
# MAGIC
# MAGIC Boundaries are reference map data. Bronze does not spatially assign projects,
# MAGIC repair geometry, standardize place names, or infer missing PSGC codes. Original
# MAGIC seven-file and feature-index provenance is retained only when the combined CSV
# MAGIC supplies it.
# MAGIC
# MAGIC ## Why this design
# MAGIC
# MAGIC Documented geographic identity, feature lineage, and geometry are required before
# MAGIC replacement. Shared batch,
# MAGIC idempotency, parameter, and snapshot mechanics keep this loader consistent with
# MAGIC the other sources without embedding a geospatial framework in Bronze.
# MAGIC
# MAGIC ## Step 1 — Define the batch parameters

# COMMAND ----------

import json
import os
import sys

repo_root = os.path.abspath("../..")
sys.path.insert(0, repo_root)

from src import bronze, config

dbutils.widgets.text("snapshot_id", "", "Snapshot ID (blank = source metadata)")
dbutils.widgets.text("source_version", "", "Optional publisher/source version")
dbutils.widgets.dropdown(
    "force_reload", "false", ["false", "true"], "Force identical snapshot reload"
)
dbutils.widgets.text("source_path", "", "Optional source path override")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Resolve the boundary source contract
# MAGIC
# MAGIC Shared configuration provides the exact file and table names, provenance class,
# MAGIC source grain, historical row reference, and required geographic identifier,
# MAGIC administrative level, source feature lineage, and geometry aliases.

# COMMAND ----------

source = config.source_config("boundaries")
source["path"] = dbutils.widgets.get("source_path").strip() or source["path"]
source["source_version"] = dbutils.widgets.get("source_version").strip() or None

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Preserve the selected snapshot
# MAGIC
# MAGIC The shared loader performs inexpensive metadata/header checks, reads source fields
# MAGIC as strings with `FAILFAST`, adds technical lineage, verifies current-table state,
# MAGIC writes the complete selected snapshot atomically, and reconciles row counts.

# COMMAND ----------

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
# MAGIC The resulting table is a traceable raw boundary snapshot. Spatial intersection,
# MAGIC project-to-place assignment, geometry conversion, coordinate repair, and geographic
# MAGIC matching remain downstream responsibilities.

# COMMAND ----------

print(json.dumps(result, sort_keys=True))
dbutils.notebook.exit(json.dumps(result, sort_keys=True))
