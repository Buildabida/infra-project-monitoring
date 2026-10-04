# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # Bronze: MGB flood susceptibility from R2
# MAGIC
# MAGIC ## Purpose
# MAGIC
# MAGIC Preserve the approved trimmed `flood_susceptibility.csv` extract in
# MAGIC `01-bronze.flood_susceptibility`. One Bronze row remains one flood-area row from
# MAGIC the approved extract. The CSV is not described as the complete MGB service response.
# MAGIC
# MAGIC ## Source-of-truth boundary
# MAGIC
# MAGIC The extract contains no place names or PSGC codes. Bronze does not invent them and
# MAGIC does not perform spatial intersection. Susceptibility labels and geometry-related
# MAGIC source fields remain unchanged for downstream geographic work.
# MAGIC
# MAGIC ## Low-cost design for the large source
# MAGIC
# MAGIC The file is approximately 2 GB, so the loader avoids schema inference, pandas,
# MAGIC source collection, sorting, caching, repartitioning, single-file coalescing,
# MAGIC spatial joins, and full-file hashing. Snapshot identity uses inexpensive artifact
# MAGIC metadata, and all validation metrics are grouped into one aggregate.
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
# MAGIC ## Step 2 — Resolve the MGB source contract
# MAGIC
# MAGIC Shared configuration provides the exact file and table names, approved-extract
# MAGIC provenance, source grain, documented rating references, and separate required alias
# MAGIC groups for susceptibility and geometry.

# COMMAND ----------

source = config.source_config("flood_susceptibility")
source["path"] = dbutils.widgets.get("source_path").strip() or source["path"]
source["source_version"] = dbutils.widgets.get("source_version").strip() or None

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Preserve the selected snapshot
# MAGIC
# MAGIC The shared loader checks metadata, rating, and geometry headers before the full read,
# MAGIC verifies the current snapshot before skipping, strictly rejects unreadable or
# MAGIC wrong-width CRLF records, preserves source strings, attaches lineage, uses an atomic
# MAGIC Delta overwrite, and reconciles source and Bronze row counts.

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
# MAGIC The resulting table preserves the approved MGB extract with traceable snapshot
# MAGIC metadata. Category mapping, PSGC assignment, geometry processing, spatial matching,
# MAGIC filtering, and aggregation remain outside Bronze.

# COMMAND ----------

print(json.dumps(result, sort_keys=True))
dbutils.notebook.exit(json.dumps(result, sort_keys=True))