# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: flood control projects from R2
# MAGIC
# MAGIC ## Purpose
# MAGIC
# MAGIC Preserve one selected `flood_control_projects.csv` snapshot in
# MAGIC `01-bronze.flood_control_projects`. One Bronze row remains one exported source
# MAGIC feature. Repeated Contract IDs can represent real components or funding-year rows,
# MAGIC so Bronze deliberately keeps them.
# MAGIC
# MAGIC ## Why this design
# MAGIC
# MAGIC - **Batch-based:** the CSV snapshot is finite and independently traceable.
# MAGIC - **Idempotent:** artifact-level checks prevent duplicate batch insertion.
# MAGIC - **Parameterized:** source choices come from widgets and shared configuration.
# MAGIC - **Snapshot-aware:** source identity is recorded on rows and in `load_log`.
# MAGIC - **Raw preserving:** ContractID repetition is reported for downstream review,
# MAGIC   never removed as a Bronze “duplicate.”
# MAGIC
# MAGIC The documented source object ID is the technical grain check. Contract cost,
# MAGIC geometry, status, and other business fields remain source strings.
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
dbutils.widgets.dropdown("force_reload", "false", ["false", "true"], "Force identical snapshot reload")
dbutils.widgets.text("source_path", "", "Optional source path override")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Resolve the flood-control source contract
# MAGIC
# MAGIC Central configuration supplies the approved file, target table, source grain,
# MAGIC provenance, and acceptable object-ID aliases. This keeps paths and contracts out
# MAGIC of the notebook logic.

# COMMAND ----------

source = config.source_config("flood_control_projects")
source["path"] = dbutils.widgets.get("source_path").strip() or source["path"]
source["source_version"] = dbutils.widgets.get("source_version").strip() or None

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Preserve the selected snapshot
# MAGIC
# MAGIC The shared loader performs inexpensive artifact/header checks, rejects snapshot-ID
# MAGIC conflicts, verifies the current table before skipping, reads strings with
# MAGIC `inferSchema=false` and `FAILFAST`, adds lineage, writes Delta atomically, and
# MAGIC reconciles source and Bronze row counts.

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
# MAGIC The resulting table keeps the source feature grain and every repeated ContractID.
# MAGIC No contract consolidation, cost cleanup, project matching, spatial assignment,
# MAGIC category mapping, aggregation, or row-level deduplication occurs in Bronze.

# COMMAND ----------

print(json.dumps(result, sort_keys=True))
dbutils.notebook.exit(json.dumps(result, sort_keys=True))
