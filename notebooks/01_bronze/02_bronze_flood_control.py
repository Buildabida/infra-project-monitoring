# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: flood control projects from R2
# MAGIC
# MAGIC Loads every row in `flood_control_projects.csv`. Repeated Contract IDs are valid
# MAGIC source rows and are deliberately not deduplicated in Bronze.

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

source = config.source_config("flood_control_projects")
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
