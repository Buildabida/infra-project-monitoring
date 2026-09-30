# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: DPWH projects
# MAGIC
# MAGIC Loads every DPWH project from the BetterGov.ph API into `01-bronze`.`dpwh_projects`. One row is one project, with every field as the API sent it. The key is `contractId`.
# MAGIC
# MAGIC 1. Saves each API reply exactly as it came, in a new landing folder for this run.
# MAGIC 2. Reads only this run's replies with Spark. It keeps every field and its name, and adds where each row came from: `_raw_file`, `_source_url` and `_ingest_run_id`.
# MAGIC 3. Adds a row to `01-bronze`.`load_log` with the total the API reports, the raw files, their sizes and their SHA-256 fingerprints.
# MAGIC
# MAGIC Bronze doesn't rename, cast or fix any field. For example, `location.province` holds a DPWH district office name, not a PSGC province. Silver renames the fields, turns the text into dates and numbers, and maps the office to a place. The checks use `TRY_CAST` when they need a number or a date.
# MAGIC
# MAGIC The load stops if a page is short or the API total changes during the load, so the table is never replaced with part of the data. It takes about 5 minutes. It is safe to run twice.

# COMMAND ----------

import os
import sys

from pyspark.sql import functions as F

repo_root = os.path.abspath("../..")  # the repo root, so the import below works everywhere
sys.path.insert(0, repo_root)

from src import api, bronze, config

# COMMAND ----------

# 1. Save every reply as it came, in a new folder for this run. About 54 pages of 5,000 projects.
load_run_id = bronze.new_run_id()
folder = bronze.landing_folder("dpwh_projects", load_run_id)
raw_files = []
for page, reply, _, total in api.dpwh_pages():
    raw_files.append(bronze.save_raw(f"{folder}/page_{page:03d}.json", reply))
print(f"Saved {len(raw_files)} pages to {folder}. The API reports {total:,} projects.")

# COMMAND ----------

# 2. Read only the pages this run saved. One row per project, with every field as the API sent it.
page_files = [path for path, _, _ in raw_files]
projects = (
    spark.read.option("multiLine", "true")
    .json(page_files)
    .select(F.explode("data.data").alias("project"), F.col("_metadata.file_path").alias("_raw_file"))
    .select("project.*", "_raw_file")
    .withColumn("_source_url", F.lit(config.DPWH_API))
)

# COMMAND ----------

# 3. Save the table and log the load.
loaded = bronze.save_table(spark, projects, "dpwh_projects", load_run_id)
bronze.log_load(spark, load_run_id, "DPWH projects API", "dpwh_projects", total, loaded, raw_files, config.DPWH_API)
print(f"Loaded {loaded:,} of the {total:,} projects the API reports.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick look
# MAGIC
# MAGIC The full checks run in `04_validation`. This is only a first look at the table.

# COMMAND ----------

display(spark.sql("""
    SELECT status, COUNT(*) AS projects, ROUND(SUM(TRY_CAST(budget AS DECIMAL(18, 2))) / 1e9, 1) AS budget_billion_pesos
    FROM `buildabida-capstone`.`01-bronze`.dpwh_projects
    GROUP BY status
    ORDER BY projects DESC
"""))
