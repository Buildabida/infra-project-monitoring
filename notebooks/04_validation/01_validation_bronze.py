# Databricks notebook source
# MAGIC %md
# MAGIC # Validation: bronze checks
# MAGIC
# MAGIC Runs our checks on every bronze table and adds the results to `04-validation`.`dq_results`, with the same columns as Week 9: `column`, `data_quality_check`, `failed_rows`, `total_rows`, `percentage` and `status`.
# MAGIC
# MAGIC - **stop**: the data is broken. Fix the load before anyone uses the table.
# MAGIC - **flag**: the data is usable, but silver has to handle these rows. The percentage tells us how big the problem is.
# MAGIC
# MAGIC The run is blocked, and this notebook fails, if a stop check fails, if a check can't run (`ERROR`) or if a required table is missing. The required tables come from the DPWH projects API, the flood control layer, the PSGC file, census Table C and the boundary maps.
# MAGIC
# MAGIC Bronze keeps the source values as they came, so the checks use `TRY_CAST` when they need a number or a date. The stored values never change.
# MAGIC
# MAGIC Each check is one line in the lists below. To add a check, add a line. All the checks of one table run in one query, so each table is read once. The row counts come from one query on `load_log`, and the checks across two tables run on their own.
# MAGIC
# MAGIC Most checks count rows. The checks that add up counts are different: `failed_rows` is how far off the total is (places or people), and `total_rows` is the total we expect. So the percentage still means how far off we are.

# COMMAND ----------

import os
import sys

from pyspark.sql import functions as F

repo_root = os.path.abspath("../..")  # the repo root, so the import below works everywhere
sys.path.insert(0, repo_root)

from src import bronze, config

run_id = bronze.new_run_id()
LEVELS = {"Reg": 18, "Prov": 82, "City": 149, "Mun": 1493, "SubMun": 14, "Bgy": 42010}  # PSGC 2Q 2026 summary
PEOPLE_IN_REGIONS = 112_727_776  # 2024 census: 112,729,484 minus 1,708 Filipinos in embassies abroad

# Every bronze table, in the order the results show.
TABLES = [
    "dpwh_projects",
    "flood_control_projects",
    "psgc",
    "psgc_sheet_manifest",
    "psgc_parse_issues",
    "population_2024",
    "census_2024_table_c",
    "census_2024_table_c_sheet_manifest",
    "census_2024_table_c_parse_issues",
    "boundaries",
]

# Bronze keeps values as they came, so the checks turn them into numbers and dates here.
PROGRESS = "TRY_CAST(progress AS DOUBLE)"
BUDGET = "TRY_CAST(budget AS DECIMAL(18, 2))"
PAID = "TRY_CAST(amountPaid AS DECIMAL(18, 2))"
START, END = "TRY_CAST(startDate AS DATE)", "TRY_CAST(completionDate AS DATE)"
DPWH_LAT, DPWH_LON = "TRY_CAST(latitude AS DOUBLE)", "TRY_CAST(longitude AS DOUBLE)"
FLOOD_LAT, FLOOD_LON = "TRY_CAST(attributes.Latitude AS DOUBLE)", "TRY_CAST(attributes.Longitude AS DOUBLE)"
COST = "TRY_CAST(attributes.ContractCost AS DECIMAL(18, 2))"
SHAPE = "GET_JSON_OBJECT(source_feature_json, '$.geometry')"
SHAPE_CODE = "GET_JSON_OBJECT(source_feature_json, '$.properties.psgc_code')"
BARANGAYS = "NOT is_sheet_head AND NOT is_block_head AND NOT is_known_duplicate_sheet"


def in_ph(lat, lon):
    """SQL that is true when a map point is inside the rough box around the Philippines."""
    return f"{lat} BETWEEN {config.PH_LAT[0]} AND {config.PH_LAT[1]} AND {lon} BETWEEN {config.PH_LON[0]} AND {config.PH_LON[1]}"


def check(column, name, failed, action, total=None):
    """One check: the column, what we check, SQL that counts the failed rows, and stop or flag.

    For a check that adds things up, total is the total we expect. Otherwise it is the row count.
    """
    return {"column": column, "check": name, "failed": failed, "action": action, "total": total}


# The checks of each table. All the checks of one table run in one query.
TABLE_CHECKS = {
    "dpwh_projects": [
        check("contractId", "not null", "COUNT_IF(contractId IS NULL)", "stop"),
        check("contractId", "unique", "COUNT(*) - COUNT(DISTINCT contractId)", "stop"),
        check("status", "one of the five known values", "COUNT_IF(status IS NULL OR status NOT IN ('Completed', 'On-Going', 'Not Yet Started', 'For Procurement', 'Terminated'))", "flag"),
        check("progress", "between 0 and 100", f"COUNT_IF({PROGRESS} IS NULL OR {PROGRESS} NOT BETWEEN 0 AND 100)", "flag"),
        check("status, progress", "Completed means 100 percent", f"COUNT_IF(NOT ((status = 'Completed') <=> ({PROGRESS} = 100)))", "flag"),
        check("budget", "more than 0", f"COUNT_IF({BUDGET} IS NULL OR {BUDGET} <= 0)", "flag"),
        check("amountPaid", "filled in (more than 0)", f"COUNT_IF({PAID} IS NULL OR {PAID} <= 0)", "flag"),
        check("amountPaid", "not more than budget", f"COUNT_IF({PAID} > {BUDGET})", "flag"),
        check("latitude, longitude", "has a map point", f"COUNT_IF({DPWH_LAT} IS NULL OR {DPWH_LON} IS NULL)", "flag"),
        check("latitude, longitude", "inside the coarse Philippines screening box", f"COUNT_IF({DPWH_LAT} IS NOT NULL AND {DPWH_LON} IS NOT NULL AND NOT ({in_ph(DPWH_LAT, DPWH_LON)}))", "flag"),
        check("startDate", "has a start date", f"COUNT_IF({START} IS NULL)", "flag"),
        check("completionDate", "not before startDate", f"COUNT_IF({END} < {START})", "flag"),
        check("location.province", "names a district office, not a region office", "COUNT_IF(location.province IS NULL OR location.province NOT LIKE '%DEO%')", "flag"),
    ],
    "flood_control_projects": [
        check("attributes.ObjectId", "not null and unique", "COUNT(*) - COUNT(DISTINCT attributes.ObjectId)", "stop"),
        check("attributes.ContractID", "not null", "COUNT_IF(attributes.ContractID IS NULL)", "stop"),
        check("attributes.ContractID", "repeated at the source row grain", "COUNT(*) - COUNT(DISTINCT attributes.ContractID)", "flag"),
        check("attributes.ContractCost", "more than 0", f"COUNT_IF({COST} IS NULL OR {COST} <= 0)", "flag"),
        check("attributes.Latitude, attributes.Longitude", "has a map point inside the coarse Philippines screening box", f"COUNT_IF({FLOOD_LAT} IS NULL OR {FLOOD_LON} IS NULL OR NOT ({in_ph(FLOOD_LAT, FLOOD_LON)}))", "flag"),
        check("attributes.TypeofWork", "more exact than the general label", "COUNT_IF(attributes.TypeofWork = 'Construction of Flood Mitigation Structure')", "flag"),
    ],
    "psgc": [
        check("psgc_code_parsed", "not null", "COUNT_IF(psgc_code_parsed IS NULL)", "stop"),
        check("psgc_code_parsed", "unique", "COUNT(*) - COUNT(DISTINCT psgc_code_parsed)", "stop"),
        check("psgc_code_parsed", "10 digits", "COUNT_IF(NOT psgc_code_parsed RLIKE '^[0-9]{10}$')", "flag"),
        check("geographic_level", "counts match the PSA summary", " + ".join(f"ABS(COUNT_IF(TRIM(geographic_level) = '{k}') - {v})" for k, v in LEVELS.items()), "flag", total=sum(LEVELS.values())),
        check("geographic_level", "is one of the documented levels", "COUNT_IF(geographic_level IS NULL OR TRIM(geographic_level) NOT IN ('Reg', 'Prov', 'City', 'Mun', 'SubMun', 'Bgy'))", "flag"),
    ],
    "psgc_sheet_manifest": [
        check("physical_row_count", "rows add up", "COUNT_IF(physical_row_count <> expected_non_data_row_count + parsed_data_row_count + parse_issue_row_count)", "stop"),
    ],
    "psgc_parse_issues": [
        check("reason", "no rows we could not read", "COUNT(*)", "stop"),
    ],
    "population_2024": [
        check("population_2024_parsed", "is a whole number", "COUNT_IF(population_2024_parsed IS NULL)", "flag"),
        check("population_2024_parsed", "regions add up to the census total", f"ABS(COALESCE(SUM(IF(TRIM(geographic_level) = 'Reg', population_2024_parsed, 0)), 0) - {PEOPLE_IN_REGIONS})", "flag", total=PEOPLE_IN_REGIONS),
        check("population_2024_parsed", "barangays add up to the census total", f"ABS(COALESCE(SUM(IF(TRIM(geographic_level) = 'Bgy', population_2024_parsed, 0)), 0) - {PEOPLE_IN_REGIONS})", "flag", total=PEOPLE_IN_REGIONS),
    ],
    "census_2024_table_c": [
        check("source_file", "has all 18 region files", f"ABS(COUNT(DISTINCT source_file) - {config.TABLE_C_FILE_COUNT})", "stop", total=config.TABLE_C_FILE_COUNT),
        check("source_file, sheet_name, source_row_number", "unique", "COUNT(*) - COUNT(DISTINCT source_file, sheet_name, source_row_number)", "stop"),
        check("population_parsed", "barangays add up to the census total", f"ABS(COALESCE(SUM(IF({BARANGAYS}, population_parsed, 0)), 0) - {PEOPLE_IN_REGIONS})", "stop", total=PEOPLE_IN_REGIONS),
        check("sheet_name", "has all 4 known copied BARMM sheets", f"ABS(COUNT(DISTINCT IF(is_known_duplicate_sheet, sheet_name, NULL)) - {len(config.TABLE_C_DUPLICATE_SHEETS)})", "stop", total=len(config.TABLE_C_DUPLICATE_SHEETS)),
        check("is_known_duplicate_sheet", f"has {config.TABLE_C_DUPLICATE_ROWS:,} copied BARMM rows", f"ABS(COUNT_IF(is_known_duplicate_sheet) - {config.TABLE_C_DUPLICATE_ROWS})", "stop", total=config.TABLE_C_DUPLICATE_ROWS),
        check("sheet_name", "copied BARMM rows kept for silver to drop", "COUNT_IF(is_known_duplicate_sheet)", "flag"),
    ],
    "census_2024_table_c_sheet_manifest": [
        check("physical_row_count", "rows add up", "COUNT_IF(physical_row_count <> expected_non_data_row_count + parsed_data_row_count + parse_issue_row_count)", "stop"),
        check("is_data_sheet", f"has {config.TABLE_C_NON_DATA_SHEETS} sheets that are not Table C", f"ABS(COUNT_IF(NOT is_data_sheet) - {config.TABLE_C_NON_DATA_SHEETS})", "stop", total=config.TABLE_C_NON_DATA_SHEETS),
    ],
    "census_2024_table_c_parse_issues": [
        check("reason", "no rows we could not read", "COUNT(*)", "stop"),
    ],
    "boundaries": [
        check("source_file, source_feature_index", "unique", "COUNT(*) - COUNT(DISTINCT source_file, source_feature_index)", "stop"),
        check("source_feature_json", "has a shape", f"COUNT_IF({SHAPE} IS NULL)", "stop"),
        check("properties.psgc_code", "not null", f"COUNT_IF({SHAPE_CODE} IS NULL)", "flag"),
    ],
}

# Row counts: the latest load_log row of each table. The source total and the rows we loaded must match.
ROW_COUNT_CHECKS = {
    "dpwh_projects": "matches the API total",
    "flood_control_projects": "matches the layer total",
    "psgc": "matches the file",
    "population_2024": "matches the file",
    "census_2024_table_c": "matches the files",
    "boundaries": "matches the files",
}
LATEST_LOADS = f"""
    SELECT table_name, rows_expected, rows_loaded
    FROM (
        SELECT table_name, rows_expected, rows_loaded,
            ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY load_ts DESC) AS newest
        FROM {bronze.table_name('load_log')}
    )
    WHERE newest = 1
"""

# Checks across two tables. Each one is a whole query that returns failed_rows and total_rows.
# NOT EXISTS stays right when a code is null, and NOT IN does not.
FLOOD, DPWH, BOUNDARIES, PSGC = (bronze.table_name(t) for t in ("flood_control_projects", "dpwh_projects", "boundaries", "psgc"))
CROSS_CHECKS = {
    "flood_control_projects": [
        check("attributes.ContractID", "found in dpwh_projects", f"""
            SELECT COUNT(*) AS failed_rows, (SELECT COUNT(*) FROM {FLOOD}) AS total_rows
            FROM {FLOOD} AS flood
            WHERE flood.attributes.ContractID IS NULL
                OR NOT EXISTS (SELECT 1 FROM {DPWH} AS dpwh WHERE dpwh.contractId = flood.attributes.ContractID)
        """, "flag"),
    ],
    "boundaries": [
        # Shapes with no code are counted by the not null check, so this check skips them.
        check("properties.psgc_code", "found in the current PSGC", f"""
            WITH shape AS (SELECT {SHAPE_CODE} AS psgc_code FROM {BOUNDARIES})
            SELECT COUNT(*) AS failed_rows, (SELECT COUNT(*) FROM shape) AS total_rows
            FROM shape
            WHERE shape.psgc_code IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM {PSGC} AS place WHERE place.psgc_code_parsed = shape.psgc_code)
        """, "flag"),
    ],
}

# COMMAND ----------


def make_result(table, column, name, action, failed_rows, total_rows):
    """One row of dq_results. No failed_rows means the check could not run, so its status is ERROR."""
    if failed_rows is None:
        status = "ERROR"
    elif failed_rows == 0:
        status = "PASS"
    else:
        status = "FAIL" if action == "stop" else "FLAG"
    percentage = round(100 * failed_rows / total_rows, 2) if failed_rows is not None and total_rows else None
    return (run_id, table, column, name, failed_rows, total_rows, percentage, status, action)


def whole(value):
    return None if value is None else int(value)


def run_query(query):
    """Run a query that returns failed_rows and total_rows. Return (None, None) if it can't run."""
    try:
        row = spark.sql(query).first()
    except Exception as error:  # noqa: BLE001 save the error as an ERROR row, and it blocks the run
        print("Could not run a check:", str(error).strip().splitlines()[0])
        return None, None
    return whole(row["failed_rows"]), whole(row["total_rows"])


def run_table_checks(table, checks):
    """Run all the checks of one table in one query. If it can't run, run them one by one to find the broken one."""
    parts = []
    for index, one in enumerate(checks):
        parts.append(f"{one['failed']} AS failed_{index}")
        parts.append(f"{one['total'] if one['total'] is not None else 'COUNT(*)'} AS total_{index}")
    try:
        row = spark.sql(f"SELECT {', '.join(parts)} FROM {bronze.table_name(table)}").first()
        values = [(whole(row[f"failed_{i}"]), whole(row[f"total_{i}"])) for i in range(len(checks))]
    except Exception:  # noqa: BLE001 find which check can't run, then keep going
        values = [
            run_query(
                f"SELECT {one['failed']} AS failed_rows, "
                f"{one['total'] if one['total'] is not None else 'COUNT(*)'} AS total_rows "
                f"FROM {bronze.table_name(table)}"
            )
            for one in checks
        ]
    return [
        make_result(table, one["column"], one["check"], one["action"], failed_rows, total_rows)
        for one, (failed_rows, total_rows) in zip(checks, values)
    ]


results = []
has_log = spark.catalog.tableExists(bronze.table_name("load_log"))
latest = {row["table_name"]: row for row in spark.sql(LATEST_LOADS).collect()} if has_log else {}
for table in TABLES:
    if not spark.catalog.tableExists(bronze.table_name(table)):
        results.append(make_result(table, "table", "required table exists", "stop", None, None))
        continue
    if table in ROW_COUNT_CHECKS:
        log = latest.get(table)
        failed_rows = None if log is None else abs(log["rows_expected"] - log["rows_loaded"])
        total_rows = None if log is None else log["rows_expected"]
        results.append(make_result(table, "row count", ROW_COUNT_CHECKS[table], "stop", failed_rows, total_rows))
    results.extend(run_table_checks(table, TABLE_CHECKS[table]))
    for one in CROSS_CHECKS.get(table, []):
        results.append(make_result(table, one["column"], one["check"], one["action"], *run_query(one["failed"])))

columns = (
    "run_id string, table_name string, column string, data_quality_check string, failed_rows long, "
    "total_rows long, percentage double, status string, action string"
)
frame = spark.createDataFrame(results, columns).withColumn("run_ts", F.current_timestamp())
frame.write.mode("append").saveAsTable(bronze.table_name("dq_results", config.VALIDATION))
print(f"Run {run_id}: {len(results)} checks saved.")

# COMMAND ----------

display(frame.select("table_name", "column", "data_quality_check", "failed_rows", "total_rows", "percentage", "status", "action"))

# COMMAND ----------

blocked = [r for r in results if r[7] == "ERROR" or (r[8] == "stop" and r[7] == "FAIL")]
if blocked:
    raise RuntimeError(f"{len(blocked)} checks blocked the run: " + "; ".join(f"{r[1]} {r[2]} {r[3]} ({r[7]})" for r in blocked))
print("No blocking check failed.")
