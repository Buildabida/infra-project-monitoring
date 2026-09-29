# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: DPWH projects
# MAGIC
# MAGIC Loads every DPWH project from the BetterGov.ph API into `01-bronze`.`dpwh_projects`. One row is one project. The key is `contract_id`.
# MAGIC
# MAGIC 1. Saves each API page as it came in the landing volume, under today's date.
# MAGIC 2. Reads the pages with Spark and names the columns like our data dictionary.
# MAGIC 3. Adds a row to `01-bronze`.`load_log` with the total the API reports.
# MAGIC
# MAGIC It takes about 5 minutes. It is safe to run twice. A second run replaces the table.

# COMMAND ----------

import sys

sys.path.append("../..")  # the repo root, so the import below works everywhere

from src import api, bronze

# COMMAND ----------

# 1. Save every page as it came. About 54 pages of 5,000 projects.
folder = bronze.landing_folder("dpwh_projects", bronze.today())
for page, projects, reported in api.dpwh_pages():
    bronze.write_json_lines(f"{folder}/page_{page:03d}.json", projects)
print(f"Saved {page} pages to {folder}. The API reports {reported:,} projects.")

# COMMAND ----------

# 2. Read the pages and name the columns. Money is a decimal. Bad dates or years become null.
raw = spark.read.json(folder).select("*", "_metadata.file_path")
raw.createOrReplaceTempView("dpwh_raw")

projects = spark.sql("""
    SELECT
        contractId                                AS contract_id,
        description,
        category,
        componentCategories                       AS component_categories,
        status,
        TRY_CAST(budget AS DECIMAL(18, 2))        AS budget,
        TRY_CAST(amountPaid AS DECIMAL(18, 2))    AS amount_paid,
        TRY_CAST(progress AS DOUBLE)              AS progress,
        TRY_CAST(infraYear AS INT)                AS infra_year,
        programName                               AS program_name,
        sourceOfFunds                             AS source_of_funds,
        contractor,
        TRY_CAST(startDate AS DATE)               AS start_date,
        TRY_CAST(completionDate AS DATE)          AS completion_date,
        location.region                           AS region,
        location.province                         AS deo,
        TRY_CAST(latitude AS DOUBLE)              AS latitude,
        TRY_CAST(longitude AS DOUBLE)             AS longitude,
        TRY_CAST(reportCount AS INT)              AS report_count,
        hasSatelliteImage                         AS has_satellite_image,
        file_path                                 AS raw_file
    FROM dpwh_raw
""")

# COMMAND ----------

# 3. Save the table and log the load.
loaded = bronze.save_table(spark, projects, "dpwh_projects")
bronze.log_load(spark, "DPWH projects API", "dpwh_projects", reported, loaded, folder)
print(f"Loaded {loaded:,} of the {reported:,} projects the API reports.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick look
# MAGIC
# MAGIC The full checks run in `04_validation`. This is only a first look at the table.

# COMMAND ----------

display(spark.sql("""
    SELECT status, COUNT(*) AS projects, ROUND(SUM(budget) / 1e9, 1) AS budget_billion_pesos
    FROM `buildabida-capstone`.`01-bronze`.dpwh_projects
    GROUP BY status
    ORDER BY projects DESC
"""))
