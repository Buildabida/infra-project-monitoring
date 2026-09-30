# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: flood control projects
# MAGIC
# MAGIC Loads the DPWH flood control map layer (the data behind sumbongsapangulo.ph) into `01-bronze`.`flood_control_projects`. One row is one feature of the layer, as the layer sent it: `attributes` has every field, and `geometry` has the map point. The key is `attributes.ObjectId`.
# MAGIC
# MAGIC 1. Saves each reply exactly as it came, in a new landing folder for this run.
# MAGIC 2. Reads only this run's replies with Spark. It keeps `attributes` and `geometry` as they came, and adds where each row came from: `_raw_file`, `_source_url` and `_ingest_run_id`.
# MAGIC 3. Adds a row to `01-bronze`.`load_log` with the total the layer reports, the raw files, their sizes and their SHA-256 fingerprints.
# MAGIC
# MAGIC The geometry uses Web Mercator (`spatialReference` 102100), not latitude and longitude. The reply says this once, not on each feature, so bronze copies it to each row as `spatialReference`. The attributes also have `Latitude` and `Longitude`.
# MAGIC
# MAGIC Some contracts have more than one row, because a contract can have parts or funding years (D-19). Bronze keeps every row. Silver flattens the fields, turns the dates from milliseconds into dates, and counts a repeated cost once.
# MAGIC
# MAGIC The load stops if a page is short, so the table is never replaced with part of the data. It takes about 1 minute. It is safe to run twice.

# COMMAND ----------

import os
import sys

from pyspark.sql import functions as F

repo_root = os.path.abspath("../..")  # the repo root, so the import below works everywhere
sys.path.insert(0, repo_root)

from src import api, bronze, config

# COMMAND ----------

# 1. Save every reply as it came, in a new folder for this run. About 10 pages of 1,000 rows.
load_run_id = bronze.new_run_id()
folder = bronze.landing_folder("flood_control", load_run_id)
raw_files = []
for page, reply, _, total in api.flood_pages():
    raw_files.append(bronze.save_raw(f"{folder}/page_{page:03d}.json", reply))
print(f"Saved {len(raw_files)} pages to {folder}. The layer reports {total:,} rows.")

# COMMAND ----------

# 2. Read only the pages this run saved. One row per feature, with its attributes and geometry as they came.
page_files = [path for path, _, _ in raw_files]
flood = (
    spark.read.option("multiLine", "true")
    .json(page_files)
    .select(
        F.explode("features").alias("feature"),
        "spatialReference",
        F.col("_metadata.file_path").alias("_raw_file"),
    )
    .select("feature.*", "spatialReference", "_raw_file")
    .withColumn("_source_url", F.lit(config.FLOOD_LAYER))
)

# COMMAND ----------

# 3. Save the table and log the load.
loaded = bronze.save_table(spark, flood, "flood_control_projects", load_run_id)
bronze.log_load(spark, load_run_id, "Flood control map layer", "flood_control_projects", total, loaded, raw_files, config.FLOOD_LAYER)
print(f"Loaded {loaded:,} of the {total:,} rows the layer reports.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick look

# COMMAND ----------

display(spark.sql("""
    SELECT
        attributes.InfraYear AS infra_year,
        COUNT(*) AS projects,
        ROUND(SUM(TRY_CAST(attributes.ContractCost AS DECIMAL(18, 2))) / 1e9, 1) AS contract_cost_billion_pesos
    FROM `buildabida-capstone`.`01-bronze`.flood_control_projects
    GROUP BY attributes.InfraYear
    ORDER BY infra_year
"""))
