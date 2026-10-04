# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: 2024 Census Table C from R2
# MAGIC
# MAGIC Loads `population_2024_table_c_test.csv` faithfully as the authoritative population
# MAGIC source. Known copied BARMM rows stay in Bronze. Missing workbook/sheet/row lineage is
# MAGIC reported as a provenance limitation and is never fabricated.

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

source = config.source_config("census_2024_table_c")
source["path"] = dbutils.widgets.get("source_path").strip() or source["path"]
source["source_version"] = dbutils.widgets.get("source_version").strip() or None
result = bronze.load_csv_snapshot(
    spark,
    source,
    snapshot_id=dbutils.widgets.get("snapshot_id"),
    force_reload=dbutils.widgets.get("force_reload"),
)
print(json.dumps(result, sort_keys=True))
dbutils.notebook.exit(json.dumps(result, sort_keys=True))
