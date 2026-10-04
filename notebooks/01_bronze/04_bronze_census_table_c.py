# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # Bronze: 2024 Census Table C from R2
# MAGIC
# MAGIC ## Purpose
# MAGIC
# MAGIC Preserve `population_2024_table_c_test.csv` in
# MAGIC `01-bronze.census_2024_table_c`. This is the authoritative project population
# MAGIC source. One Bronze row remains one exported Table C row, including the known copied
# MAGIC BARMM rows.
# MAGIC
# MAGIC ## Source-of-truth boundary
# MAGIC
# MAGIC Bronze does not create a generic `population_2024` table and does not reintroduce
# MAGIC Table B. It also does not remove the known BARMM copies. Their identification and
# MAGIC analytical handling belong in validation and Silver.
# MAGIC
# MAGIC The current combined CSV was derived from 18 PSA workbooks. Original file, sheet,
# MAGIC row, and duplicate-sheet provenance is retained only when those fields are present;
# MAGIC missing provenance is documented and never fabricated.
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
# MAGIC ## Step 2 — Resolve the Table C source contract
# MAGIC
# MAGIC Central configuration supplies the exact R2 file, authoritative target table,
# MAGIC expected source grain, historical reference counts, and required place, population,
# MAGIC file, sheet, and row lineage aliases. This keeps the population decision consistent
# MAGIC across code and validation.

# COMMAND ----------

source = config.source_config("census_2024_table_c")
source["path"] = dbutils.widgets.get("source_path").strip() or source["path"]
source["source_version"] = dbutils.widgets.get("source_version").strip() or None

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Preserve the selected snapshot
# MAGIC
# MAGIC The shared loader checks the artifact and required header contract before replacing
# MAGIC Bronze. It preserves all values as strings, adds lineage metadata, uses an atomic
# MAGIC Delta overwrite for the selected snapshot, reconciles row counts, and records the
# MAGIC snapshot outcome in `load_log`.

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
# MAGIC The resulting table is the raw Table C interface for downstream population work.
# MAGIC Bronze performs no place-name cleanup, PSGC matching, population aggregation,
# MAGIC duplicate removal, numeric assumption, or fabricated source lineage.

# COMMAND ----------

print(json.dumps(result, sort_keys=True))
dbutils.notebook.exit(json.dumps(result, sort_keys=True))