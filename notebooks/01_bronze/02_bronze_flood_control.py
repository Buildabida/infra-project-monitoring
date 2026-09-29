# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: flood control projects
# MAGIC
# MAGIC Loads the DPWH flood control map layer (the data behind sumbongsapangulo.ph) into `01-bronze`.`flood_control_projects`. One row is one row of the layer. The key is `contract_id`, but a few contracts have more than one row.
# MAGIC
# MAGIC 1. Saves each call as it came in the landing volume, under today's date.
# MAGIC 2. Reads the rows with Spark and gives the columns our names.
# MAGIC 3. Adds a row to `01-bronze`.`load_log` with the total the layer reports.
# MAGIC
# MAGIC It takes about 1 minute. It is safe to run twice.

# COMMAND ----------

import os
import sys

repo_root = os.path.abspath("../..")  # the repo root, so the import below works everywhere
sys.path.insert(0, repo_root)

from src import api, bronze

# COMMAND ----------

# 1. Save every call as it came. About 10 calls of 1,000 rows.
folder = bronze.landing_folder("flood_control", bronze.today())
for page, rows, reported in api.flood_pages():
    bronze.write_json_lines(f"{folder}/page_{page:03d}.json", rows)
print(f"Saved {page} calls to {folder}. The layer reports {reported:,} rows.")

# COMMAND ----------

# 2. Read the rows and name the columns. The layer keeps dates as milliseconds, so we turn them into dates.
raw = spark.read.json(folder).select("*", "_metadata.file_path")
raw.createOrReplaceTempView("flood_raw")

flood = spark.sql("""
    SELECT
        ContractID                                             AS contract_id,
        ProjectID                                              AS project_id,
        ProjectDescription                                     AS description,
        ProjectComponentID                                     AS component_id,
        ProjectComponentDescription                            AS component_description,
        TypeofWork                                             AS type_of_work,
        infra_type,
        Program                                                AS program,
        TRY_CAST(InfraYear AS INT)                             AS infra_year,
        FundingYear                                            AS funding_year,
        Region                                                 AS region,
        Province                                               AS province,
        Municipality                                           AS municipality,
        LegislativeDistrict                                    AS legislative_district,
        DistrictEngineeringOffice                              AS deo,
        ImplementingOffice                                     AS implementing_office,
        TRY_CAST(ABC AS DECIMAL(18, 2))                        AS abc,
        TRY_CAST(ContractCost AS DECIMAL(18, 2))               AS contract_cost,
        ABC_String                                             AS abc_text,
        ContractCost_String                                    AS contract_cost_text,
        Contractor                                             AS contractor,
        StartDate                                              AS start_date_text,
        CAST(TIMESTAMP_MILLIS(TRY_CAST(CompletionDateOriginal AS BIGINT)) AS DATE) AS completion_date_original,
        CompletionDateActual                                   AS completion_date_actual_text,
        TRY_CAST(CompletionYear AS INT)                        AS completion_year,
        TRY_CAST(Latitude AS DOUBLE)                           AS latitude,
        TRY_CAST(Longitude AS DOUBLE)                          AS longitude,
        ObjectId                                               AS object_id,
        file_path                                              AS raw_file
    FROM flood_raw
""")

# COMMAND ----------

# 3. Save the table and log the load.
loaded = bronze.save_table(spark, flood, "flood_control_projects")
bronze.log_load(spark, "Flood control map layer", "flood_control_projects", reported, loaded, folder)
print(f"Loaded {loaded:,} of the {reported:,} rows the layer reports.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick look

# COMMAND ----------

display(spark.sql("""
    SELECT infra_year, COUNT(*) AS projects, ROUND(SUM(contract_cost) / 1e9, 1) AS contract_cost_billion_pesos
    FROM `buildabida-capstone`.`01-bronze`.flood_control_projects
    GROUP BY infra_year
    ORDER BY infra_year
"""))
