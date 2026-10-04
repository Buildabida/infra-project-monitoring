# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # Bronze: PSGC from R2
# MAGIC
# MAGIC ## Purpose
# MAGIC
# MAGIC Preserve one selected `psgc.csv` snapshot in `01-bronze.psgc`. One Bronze row
# MAGIC remains one exported PSGC place row. Codes, names, classifications, and any
# MAGIC population field stay exactly as represented by the CSV, apart from technical
# MAGIC column-name handling required by Delta.
# MAGIC
# MAGIC ## Source-of-truth boundary
# MAGIC
# MAGIC PSGC is the geographic code and place-name reference. Its population value may
# MAGIC support a downstream cross-check, but PSA 2024 Census Table C remains the project's
# MAGIC authoritative population source. Bronze does not merge the two sources.
# MAGIC
# MAGIC ## Why this design
# MAGIC
# MAGIC The notebook is batch-based, parameterized, snapshot-aware, and idempotent through
# MAGIC the shared loader. Documented code, place-name, and geographic-level aliases are
# MAGIC required before replacement,
# MAGIC while geographic standardization and hierarchy logic remain in Silver.
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
# MAGIC ## Step 2 — Resolve the PSGC source contract
# MAGIC
# MAGIC Shared configuration provides the approved file name, target table, provenance,
# MAGIC row grain, and accepted aliases for PSGC code, place name, and geographic level.
# MAGIC This avoids hardcoded paths and table names inside the notebook.

# COMMAND ----------

source = config.source_config("psgc")
source["path"] = dbutils.widgets.get("source_path").strip() or source["path"]
source["source_version"] = dbutils.widgets.get("source_version").strip() or None

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Preserve the selected snapshot
# MAGIC
# MAGIC The shared loader verifies metadata and headers, resolves snapshot identity, checks
# MAGIC current-table state, preserves all source rows as strings, adds technical lineage,
# MAGIC atomically replaces the selected Delta snapshot, and records row-count evidence.

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
# MAGIC The resulting PSGC table is a raw geographic reference snapshot. Bronze does not
# MAGIC clean place names, rebuild the hierarchy, cast population, match projects, or make
# MAGIC PSGC population authoritative.

# COMMAND ----------

print(json.dumps(result, sort_keys=True))
dbutils.notebook.exit(json.dumps(result, sort_keys=True))
