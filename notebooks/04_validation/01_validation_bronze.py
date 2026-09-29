# Databricks notebook source
# MAGIC %md
# MAGIC # Validation: bronze checks
# MAGIC
# MAGIC Runs our checks on every bronze table and adds the results to `04-validation`.`dq_results`, with the same columns as Week 9: `column`, `data_quality_check`, `failed_rows`, `total_rows`, `percentage` and `status`.
# MAGIC
# MAGIC - **stop**: the data is broken. Fix the load before anyone uses the table. A failed stop check makes this notebook fail.
# MAGIC - **flag**: the data is usable, but silver has to handle these rows. The percentage tells us how big the problem is.
# MAGIC
# MAGIC Each check is one SQL line in the list below. To add a check, add a line. Tables that are not loaded yet are skipped.
# MAGIC
# MAGIC Most checks count rows. The checks that add up counts are different: `failed_rows` is how far off the total is (places or people), and `total_rows` is the total we expect. So the percentage still means how far off we are.

# COMMAND ----------

import datetime
import os
import sys

from pyspark.sql import functions as F

repo_root = os.path.abspath("../..")  # the repo root, so the import below works everywhere
sys.path.insert(0, repo_root)

from src import bronze, config

run_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
LAT, LON = config.PH_LAT, config.PH_LON
IN_PH = f"latitude BETWEEN {LAT[0]} AND {LAT[1]} AND longitude BETWEEN {LON[0]} AND {LON[1]}"
LEVELS = {"Reg": 18, "Prov": 82, "City": 149, "Mun": 1493, "SubMun": 14, "Bgy": 42010}  # PSGC 2Q 2026 summary
PEOPLE_IN_REGIONS = 112_727_776  # 2024 census: 112,729,484 minus 1,708 Filipinos in embassies abroad


def off_by(difference, expected, table):
    """For checks that add things up: how far off the total is, out of the total we expect."""
    return f"SELECT {difference} AS failed_rows, {expected} AS total_rows FROM {bronze.table_name(table)}"


def log_count(table):
    """Failed rows = the gap between what the source reported and what we loaded, from the latest load."""
    return f"""
        SELECT ABS(rows_expected - rows_loaded) AS failed_rows, rows_expected AS total_rows
        FROM {bronze.table_name('load_log')}
        WHERE table_name = '{table}'
        ORDER BY load_ts DESC
        LIMIT 1
    """


# table, column, check, failed rows (SQL, or a full query), action
CHECKS = [
    ("dpwh_projects", "row count", "matches the API total", log_count("dpwh_projects"), "stop"),
    ("dpwh_projects", "contract_id", "not null", "COUNT_IF(contract_id IS NULL)", "stop"),
    ("dpwh_projects", "contract_id", "unique", "COUNT(*) - COUNT(DISTINCT contract_id)", "stop"),
    ("dpwh_projects", "status", "one of the five known values", "COUNT_IF(status IS NULL OR status NOT IN ('Completed', 'On-Going', 'Not Yet Started', 'For Procurement', 'Terminated'))", "flag"),
    ("dpwh_projects", "progress", "between 0 and 100", "COUNT_IF(progress IS NULL OR progress NOT BETWEEN 0 AND 100)", "flag"),
    ("dpwh_projects", "status, progress", "Completed means 100 percent", "COUNT_IF((status = 'Completed') <> (progress = 100))", "flag"),
    ("dpwh_projects", "budget", "more than 0", "COUNT_IF(budget IS NULL OR budget <= 0)", "flag"),
    ("dpwh_projects", "amount_paid", "filled in (more than 0)", "COUNT_IF(amount_paid IS NULL OR amount_paid <= 0)", "flag"),
    ("dpwh_projects", "amount_paid", "not more than budget", "COUNT_IF(amount_paid > budget)", "flag"),
    ("dpwh_projects", "latitude, longitude", "has a map point", "COUNT_IF(latitude IS NULL OR longitude IS NULL)", "flag"),
    ("dpwh_projects", "latitude, longitude", "inside the Philippines", f"COUNT_IF(latitude IS NOT NULL AND NOT ({IN_PH}))", "flag"),
    ("dpwh_projects", "start_date", "has a start date", "COUNT_IF(start_date IS NULL)", "flag"),
    ("dpwh_projects", "completion_date", "not before start_date", "COUNT_IF(completion_date < start_date)", "flag"),
    ("dpwh_projects", "deo", "names a district office, not a region office", "COUNT_IF(deo IS NULL OR deo NOT LIKE '%DEO%')", "flag"),
    ("flood_control_projects", "row count", "matches the layer total", log_count("flood_control_projects"), "stop"),
    ("flood_control_projects", "contract_id", "not null", "COUNT_IF(contract_id IS NULL)", "stop"),
    ("flood_control_projects", "contract_id", "unique", "COUNT(*) - COUNT(DISTINCT contract_id)", "flag"),
    ("flood_control_projects", "contract_cost", "more than 0", "COUNT_IF(contract_cost IS NULL OR contract_cost <= 0)", "flag"),
    ("flood_control_projects", "latitude, longitude", "inside the Philippines", f"COUNT_IF(latitude IS NULL OR NOT ({IN_PH}))", "flag"),
    ("flood_control_projects", "contract_id", "found in dpwh_projects", f"COUNT_IF(contract_id NOT IN (SELECT contract_id FROM {bronze.table_name('dpwh_projects')}))", "flag"),
    ("flood_control_projects", "type_of_work", "more exact than the general label", "COUNT_IF(type_of_work = 'Construction of Flood Mitigation Structure')", "flag"),
    ("psgc", "row count", "matches the file", log_count("psgc"), "stop"),
    ("psgc", "psgc_code", "not null", "COUNT_IF(psgc_code IS NULL)", "stop"),
    ("psgc", "psgc_code", "unique", "COUNT(*) - COUNT(DISTINCT psgc_code)", "stop"),
    ("psgc", "psgc_code", "10 digits", "COUNT_IF(NOT psgc_code RLIKE '^[0-9]{10}$')", "flag"),
    ("psgc", "geographic_level", "counts match the PSA summary", off_by(" + ".join(f"ABS(COUNT_IF(geographic_level = '{k}') - {v})" for k, v in LEVELS.items()), sum(LEVELS.values()), "psgc"), "flag"),
    ("population_2024", "population_2024", "regions add up to the census total", off_by(f"ABS(SUM(IF(geographic_level = 'Reg', population_2024, 0)) - {PEOPLE_IN_REGIONS})", PEOPLE_IN_REGIONS, "population_2024"), "flag"),
    ("population_2024", "population_2024", "barangays add up to the census total", off_by(f"ABS(SUM(IF(geographic_level = 'Bgy', population_2024, 0)) - {PEOPLE_IN_REGIONS})", PEOPLE_IN_REGIONS, "population_2024"), "flag"),
    ("census_2024_table_b", "row count", "matches the file", log_count("census_2024_table_b"), "stop"),
    ("census_2024_table_b", "pop_2024", "regions add up to the census total", off_by(f"ABS(SUM(IF(is_region, pop_2024, 0)) - {PEOPLE_IN_REGIONS})", PEOPLE_IN_REGIONS, "census_2024_table_b"), "flag"),
    ("boundaries", "row count", "matches the files", log_count("boundaries"), "stop"),
    ("boundaries", "geometry_json", "not null", "COUNT_IF(geometry_json IS NULL)", "stop"),
    ("boundaries", "psgc_code", "not null", "COUNT_IF(psgc_code IS NULL)", "flag"),
    # Shapes with no code are counted by the not null check above, so this check skips them.
    ("boundaries", "psgc_code", "found in the current PSGC", f"COUNT_IF(psgc_code IS NOT NULL AND psgc_code NOT IN (SELECT psgc_code FROM {bronze.table_name('psgc')}))", "flag"),
]

# COMMAND ----------

results, skipped = [], set()
for table, column, check, failed, action in CHECKS:
    if not spark.catalog.tableExists(bronze.table_name(table)):
        skipped.add(table)
        continue
    query = failed if failed.lstrip().upper().startswith("SELECT") else f"SELECT {failed} AS failed_rows, COUNT(*) AS total_rows FROM {bronze.table_name(table)}"
    try:
        row = spark.sql(query).first()
    except Exception as error:  # noqa: BLE001 a check that cannot run is a failed check, not a crash
        print(f"Could not run {table} {column} {check}: {error}")
        row = None
    failed_rows = None if row is None else int(row["failed_rows"] or 0)
    total_rows = None if row is None else int(row["total_rows"] or 0)
    if failed_rows is None:
        status = "ERROR"
    elif failed_rows == 0:
        status = "PASS"
    else:
        status = "FAIL" if action == "stop" else "FLAG"
    percentage = round(100 * failed_rows / total_rows, 2) if total_rows else None
    results.append((run_id, table, column, check, failed_rows, total_rows, percentage, status, action))

columns = (
    "run_id string, table_name string, column string, data_quality_check string, failed_rows long, "
    "total_rows long, percentage double, status string, action string"
)
frame = spark.createDataFrame(results, columns).withColumn("run_ts", F.current_timestamp())
frame.write.mode("append").saveAsTable(bronze.table_name("dq_results", config.VALIDATION))
print(f"Run {run_id}: {len(results)} checks saved. Skipped tables that are not loaded yet: {sorted(skipped) or 'none'}")

# COMMAND ----------

display(frame.select("table_name", "column", "data_quality_check", "failed_rows", "total_rows", "percentage", "status", "action"))

# COMMAND ----------

stops = [r for r in results if r[8] == "stop" and r[7] in ("FAIL", "ERROR")]
if stops:
    raise RuntimeError(f"{len(stops)} stop checks failed: " + "; ".join(f"{r[1]} {r[2]} {r[3]}" for r in stops))
print("No stop check failed.")
