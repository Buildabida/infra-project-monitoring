# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # Check the six R2 source files
# MAGIC
# MAGIC ## Purpose
# MAGIC
# MAGIC Confirm that all six approved CSV artifacts are present, non-empty, readable, and
# MAGIC structurally recognizable before any Bronze table can be replaced.
# MAGIC
# MAGIC ## Low-cost precheck
# MAGIC
# MAGIC The check uses filesystem metadata, the CSV header, and a small buffered proof that
# MAGIC data exists. It does not parse each source row, infer a Spark schema, calculate a
# MAGIC full-file checksum, or read the 2 GB MGB extract into a DataFrame.
# MAGIC
# MAGIC ## Failure contract
# MAGIC
# MAGIC Every source is inspected so the result table shows the complete set of problems.
# MAGIC Missing files, empty files, duplicate or unusable headers, reserved metadata-name
# MAGIC collisions, and missing identifying aliases are reported clearly. Any failed source
# MAGIC blocks Bronze replacement.
# MAGIC
# MAGIC ## Step 1 — Load shared source definitions

# COMMAND ----------

import os
import sys

repo_root = os.path.abspath("../..")
sys.path.insert(0, repo_root)

from src import bronze, config
import importlib
importlib.reload(config)
importlib.reload(bronze)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Inspect each configured artifact
# MAGIC
# MAGIC `SOURCE_ORDER` is the single authoritative six-source list. The same source
# MAGIC configuration supplies file paths and header contracts to precheck, ingestion, and
# MAGIC validation, preventing notebook-specific hardcoding.

# COMMAND ----------

rows = []
for source_name in config.SOURCE_ORDER:
    source = config.source_config(source_name)
    try:
        metadata = bronze.inspect_source(source["path"])
        clean_header, _ = bronze._column_mapping(metadata["header"])
        bronze.validate_source_header(source, clean_header)
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

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Present one compact source inventory
# MAGIC
# MAGIC The output contains one row per required source with its resolved path, artifact
# MAGIC size, modification time, header width, and concise failure reason. It contains no
# MAGIC business rows and therefore remains small enough for the driver.

# COMMAND ----------

checks = spark.createDataFrame(
    rows,
    "source_name string, source_path string, status string, size_bytes long, "
    "modified_at timestamp, header_columns int, error_message string",
)
display(checks)
failed = [row for row in rows if row[2] == "FAILED"]
if failed:
    raise RuntimeError(f"{len(failed)} of {len(rows)} required R2 sources failed metadata/header checks")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC This precheck protects the last complete Bronze tables by rejecting missing or
# MAGIC structurally unexpected artifacts before the shared loader performs a full read.