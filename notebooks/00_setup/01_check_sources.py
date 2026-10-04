# Databricks notebook source
# MAGIC %md
# MAGIC # Check the six R2 source files
# MAGIC
# MAGIC Reads only file metadata and each CSV header. It does not scan the file bodies.

# COMMAND ----------

import os
import sys

repo_root = os.path.abspath("../..")
sys.path.insert(0, repo_root)

from src import bronze, config

rows = []
for source_name in config.SOURCE_ORDER:
    source = config.source_config(source_name)
    try:
        metadata = bronze.inspect_source(source["path"])
        rows.append(
            (
                source_name,
                source["path"],
                "OK",
                metadata["size_bytes"],
                metadata["modified_at"],
                len(metadata["header"]),
                None,
            )
        )
    except Exception as error:  # noqa: BLE001 - show every unavailable source in one run
        rows.append((source_name, source["path"], "FAILED", None, None, None, str(error)[:500]))

checks = spark.createDataFrame(
    rows,
    "source_name string, source_path string, status string, size_bytes long, "
    "modified_at timestamp, header_columns int, error_message string",
)
display(checks)
failed = [row for row in rows if row[2] == "FAILED"]
if failed:
    raise RuntimeError(f"{len(failed)} of {len(rows)} required R2 sources failed metadata/header checks")
