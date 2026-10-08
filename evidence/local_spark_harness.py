"""Run the three project-foundation notebooks on local Spark with seeded rows.

Only Databricks-only syntax is swapped:
- USE CATALOG is skipped.
- USING DELTA becomes USING PARQUET.
- SELECT * EXCEPT (col) becomes SELECT * (the extra rank column is harmless).
- MERGE INTO silver_dq_results becomes INSERT INTO ... SELECT *.
"""

import json
import re
import shutil
import sys
from pathlib import Path

from pyspark.sql import SparkSession

REPO = Path(sys.argv[1])
WORK = Path(sys.argv[2])
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)

spark = (
    SparkSession.builder.master("local[2]")
    .config("spark.sql.warehouse.dir", str(WORK / "warehouse"))
    .config("spark.ui.enabled", "false")
    .config("spark.sql.shuffle.partitions", "2")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")

SCHEMA_NAMES = {"`01-bronze`": "bronze01", "`02-silver`": "silver02", "`04-validation`": "validation04"}
_raw_sql = spark.sql


def _local_sql(text, *args, **kwargs):
    for remote, local in SCHEMA_NAMES.items():
        text = text.replace(remote, local)
    return _raw_sql(text, *args, **kwargs)


spark.sql = _local_sql
_raw_table = spark.table
spark.table = lambda name: _raw_table(SCHEMA_NAMES.get(name.split(".")[0], name.split(".")[0]) + "." + name.split(".")[1])
print("ANSI mode:", spark.conf.get("spark.sql.ansi.enabled"))

for schema in ["01-bronze", "02-silver", "04-validation"]:
    spark.sql(f"CREATE DATABASE IF NOT EXISTS `{schema}`")

SNAP = "snap-2026-10-04"
DPWH_COLS = [
    "contract_id", "description", "category", "status", "reported_budget",
    "progress", "start_date", "completion_date", "latitude", "longitude",
    "contractor", "source_of_funds", "infra_year", "reported_region",
]
ROWS = [
    # identical twin rows: kept, numbered 1 and 2
    ("C1", "Road A", "Roads", "Completed", "1000.00", "100", "2020-01-01", "2021-01-01", "14.5", "121.0", "K1", "GAA", "2020", "NCR"),
    ("C1", "Road A", "Roads", "Completed", "1000.00", "100", "2020-01-01", "2021-01-01", "14.5", "121.0", "K1", "GAA", "2020", "NCR"),
    # conflicting budgets on one contract
    ("C2", "Dike B", "Flood Control", " On-Going ", "500.00", "0", "2023-05-01", None, "10.0", "123.0", "K2", "GAA", "2023", "Region VII"),
    ("C2", "Dike B", "Flood Control", "On-Going", "700.00", "0", "2023-05-01", None, "10.0", "123.0", "K2", "GAA", "2023", "Region VII"),
    # shifted values: progress 2026, negative budget, bad year, no coordinates
    ("C3", "Bridge C", "Bridges", "Completed", "-5", "2026", "bad-date", None, None, None, "K3 ", "GAA", "x", "  Region I "),
    # unparseable budget and progress, partial pair
    ("C4", "School D", "", "Terminated", "abc", "n/a", "2019-02-02", "2019-12-01", "15.0", None, "K4", "GAA", "2019", "Central Office"),
]


def seed(category_rules, status_rules):
    for table in ["dpwh_projects", "load_log"]:
        spark.sql(f"DROP TABLE IF EXISTS `01-bronze`.{table}")
    for table in ["config_project_category_mapping", "config_project_status_mapping",
                  "silver_dpwh_project_component", "silver_project"]:
        spark.sql(f"DROP TABLE IF EXISTS `02-silver`.{table}")
    for table in ["dq_results", "silver_dq_results"]:
        spark.sql(f"DROP TABLE IF EXISTS `04-validation`.{table}")

    data = [r + (SNAP, "ingest-1", "2026-10-04 00:00:00") for r in ROWS]
    cols = DPWH_COLS + ["_source_snapshot_id", "_ingest_run_id", "_source_modified_at"]
    df = spark.createDataFrame(data, cols)
    df = df.withColumn("_source_modified_at", df["_source_modified_at"].cast("timestamp"))
    df.write.saveAsTable("bronze01.dpwh_projects")

    spark.sql(f"""
        CREATE TABLE `01-bronze`.load_log USING PARQUET AS
        SELECT 'dpwh_projects' AS table_name, 'SUCCESS' AS status,
               TIMESTAMP'2026-10-04 01:00:00' AS started_at,
               TIMESTAMP'2026-10-04 01:05:00' AS completed_at,
               '{SNAP}' AS snapshot_id, {len(ROWS)} AS rows_loaded
    """)
    spark.sql(f"""
        CREATE TABLE `04-validation`.dq_results USING PARQUET AS
        SELECT 'dpwh_projects' AS table_name, '{SNAP}' AS snapshot_id,
               TIMESTAMP'2026-10-04 02:00:00' AS run_ts, 'v1' AS run_id,
               'stop' AS action, 'PASS' AS status
    """)
    spark.sql("""
        CREATE TABLE `02-silver`.config_project_category_mapping (
            source_system STRING, raw_category STRING, source_infra_type STRING,
            standardized_sector STRING, standardized_category STRING, mapping_rule STRING,
            taxonomy_version STRING, approval_status STRING, approved_by STRING,
            approved_at TIMESTAMP, is_active BOOLEAN, source_reference STRING, notes STRING
        ) USING PARQUET
    """)
    spark.sql("""
        CREATE TABLE `02-silver`.config_project_status_mapping (
            source_system STRING, source_status STRING, standardized_status STRING,
            status_group STRING, mapping_rule STRING, status_mapping_version STRING,
            approval_status STRING, approved_by STRING, approved_at TIMESTAMP,
            is_active BOOLEAN, source_reference STRING, notes STRING
        ) USING PARQUET
    """)
    for rule in category_rules:
        spark.sql(
            "INSERT INTO `02-silver`.config_project_category_mapping VALUES "
            f"({rule}, NULL, 'tax-v1', 'APPROVED', 'r', NULL, TRUE, NULL, NULL)"
        )
    for rule in status_rules:
        spark.sql(
            "INSERT INTO `02-silver`.config_project_status_mapping VALUES "
            f"({rule}, NULL, 'status-v1', 'APPROVED', 'r', NULL, TRUE, NULL, NULL)"
        )


def statements(path):
    cells = json.loads((REPO / path).read_text())["cells"]
    for cell in cells:
        if cell["cell_type"] != "code":
            continue
        sql = "".join(cell["source"]).replace("%sql\n", "", 1)
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if not stmt or stmt.startswith("USE CATALOG") or stmt.startswith("CREATE SCHEMA"):
                continue
            stmt = stmt.replace("USING DELTA", "USING PARQUET")
            stmt = re.sub(r"SELECT \* EXCEPT \(\w+\)", "SELECT *", stmt)
            if stmt.startswith("MERGE INTO `04-validation`.silver_dq_results"):
                stmt = "INSERT INTO `04-validation`.silver_dq_results SELECT * FROM silver_project_checks"
            replace = re.match(r"CREATE OR REPLACE TABLE (\S+)", stmt)
            if replace:
                yield f"DROP TABLE IF EXISTS {replace.group(1)}"
                stmt = stmt.replace("CREATE OR REPLACE TABLE", "CREATE TABLE", 1)
            yield stmt


def run(path):
    last = None
    for stmt in statements(path):
        last = spark.sql(stmt)
        last.collect()
    return last


NOTEBOOKS = [
    "notebooks/02_silver/04_silver_dpwh_project_component.ipynb",
    "notebooks/02_silver/05_silver_project.ipynb",
    "notebooks/04_validation/04_validation_silver_projects.ipynb",
]

failures = []


def check(label, ok):
    print(("PASS " if ok else "FAIL ") + label)
    if not ok:
        failures.append(label)


# Scenario 1: empty mapping tables
seed([], [])
for nb in NOTEBOOKS:
    run(nb)
comp = spark.table("`02-silver`.silver_dpwh_project_component")
proj = spark.table("`02-silver`.silver_project")
check("1 component rows equal Bronze rows", comp.count() == len(ROWS))
check("1 component keys unique", comp.select("component_key").distinct().count() == len(ROWS))
twins = comp.where("contract_id = 'C1'").select("source_row_ordinal").collect()
check("1 identical twins numbered 1 and 2", sorted(r[0] for r in twins) == [1, 2])
check("1 every row UNMAPPED", comp.where("category_mapping_state = 'UNMAPPED' AND status_mapping_state = 'UNMAPPED'").count() == len(ROWS))
c3 = comp.where("contract_id = 'C3'").first()
check("1 progress 2026 is OUT_OF_RANGE and kept", c3.progress_quality_status == "OUT_OF_RANGE" and c3.physical_progress_pct == 2026)
check("1 budget -5 is NEGATIVE", c3.budget_quality_status == "NEGATIVE")
check("1 infra_year x is UNPARSEABLE", c3.infra_year_quality_status == "UNPARSEABLE" and c3.infra_year_parsed is None)
c4 = comp.where("contract_id = 'C4'").first()
check("1 abc budget is UNPARSEABLE", c4.budget_quality_status == "UNPARSEABLE")
check("1 partial pair status", c4.coordinate_status == "PARTIAL_PAIR")
check("1 project rows equal distinct contracts", proj.count() == 4)
p2 = proj.where("contract_id = 'C2'").first()
check("1 conflicting budgets stay CONFLICT and NULL", p2.budget_resolution_status == "CONFLICT" and p2.reported_budget_pesos is None)
check("1 trimmed status resolves across spaces", p2.status_resolution_status == "RESOLVED" and p2.status_raw == "On-Going")
p1 = proj.where("contract_id = 'C1'").first()
check("1 twin budget resolves once, not summed", p1.reported_budget_pesos == 1000 and p1.budget_resolution_status == "RESOLVED_REPEATED_IDENTICAL")
p3 = proj.where("contract_id = 'C3'").first()
check("1 region resolves after trim", p3.reported_region == "Region I" and p3.reported_region_resolution_status == "RESOLVED")
check("1 contractor count uses trimmed value", p3.distinct_contractor_count == 1 and p3.contractor == "K3")
check("1 project progress quality carried", p3.progress_quality_status == "OUT_OF_RANGE")
check("1 zero progress flag for C2", p2.zero_progress_flag is True)
dq = spark.table("`04-validation`.silver_dq_results")
check("1 no FAIL rows", dq.where("status = 'FAIL'").count() == 0)
attrs = {r[0] for r in dq.select("data_quality_attribute").distinct().collect()}
check("1 all seven attributes present", attrs == {"Completeness", "Uniqueness", "Validity", "Accuracy", "Consistency", "Auditability", "Timeliness"})
first_keys = sorted(r[0] for r in comp.select("component_key").collect())
first_runs = (comp.first().run_id, proj.first().run_id)

# rerun gives the same keys and the same validation rows
for nb in NOTEBOOKS[:2]:
    run(nb)
comp = spark.table("`02-silver`.silver_dpwh_project_component")
proj = spark.table("`02-silver`.silver_project")
check("1 rerun keeps component keys", sorted(r[0] for r in comp.select("component_key").collect()) == first_keys)
check("1 rerun keeps run IDs", (comp.first().run_id, proj.first().run_id) == first_runs)

# Scenario 2: approved rules, including a same-name rule for another source system
seed(
    [
        "'dpwh_projects', 'Flood Control', '', 'Water', 'Flood control'",
        "'flood_control_projects', 'Flood Control', 'Dike', 'Water', 'Flood control'",
        "'dpwh_projects', 'Roads', '', 'Transport', 'Roads'",
    ],
    ["'dpwh_projects', 'On-Going', 'Ongoing', 'ACTIVE'", "'DPWH', 'Completed', 'Completed', 'DONE'"],
)
for nb in NOTEBOOKS:
    run(nb)
comp = spark.table("`02-silver`.silver_dpwh_project_component")
check("2 no fan-out from another source system's rule", comp.count() == len(ROWS))
check("2 Flood Control mapped for both C2 rows", comp.where("contract_id = 'C2' AND category_mapping_state = 'MAPPED'").count() == 2)
check("2 status with spaces maps after trim", comp.where("contract_id = 'C2' AND status_mapping_state = 'MAPPED'").count() == 2)
check("2 rule keyed DPWH is ignored", comp.where("contract_id = 'C1' AND status_mapping_state = 'UNMAPPED'").count() == 2)
check("2 mapped rows carry version", comp.where("category_mapping_state = 'MAPPED' AND taxonomy_version IS NULL").count() == 0)
check("2 no FAIL rows", spark.table("`04-validation`.silver_dq_results").where("status = 'FAIL'").count() == 0)

# Scenario 3: two approved rules for one raw category must stop the run
seed(
    [
        "'dpwh_projects', 'Roads', '', 'Transport', 'Roads'",
        "'dpwh_projects', 'Roads', '', 'Transport', 'Highways'",
    ],
    [],
)
try:
    run(NOTEBOOKS[0])
    check("3 duplicate approved rule stops the component run", False)
except Exception as error:  # noqa: BLE001 - the harness expects the assertion error
    check("3 duplicate approved rule stops the component run", "one rule per raw category" in str(error))

# Scenario 4: a duplicated component row must fail validation and still leave evidence
seed([], [])
run(NOTEBOOKS[0])
run(NOTEBOOKS[1])
spark.sql("INSERT INTO `02-silver`.silver_dpwh_project_component SELECT * FROM `02-silver`.silver_dpwh_project_component WHERE contract_id = 'C4'")
try:
    run(NOTEBOOKS[2])
    check("4 duplicated component row fails the gate", False)
except Exception as error:  # noqa: BLE001 - the harness expects the assertion error
    check("4 duplicated component row fails the gate", "blocking Silver project checks failed" in str(error))
failed = {r[0] for r in spark.table("`04-validation`.silver_dq_results").where("status = 'FAIL'").select("data_quality_check").collect()}
print("   FAIL checks recorded:", sorted(failed))
check("4 FAIL evidence saved before the assert", {"Component keys are unique", "Bronze DPWH rows reconcile to component rows"} <= failed)

print()
print("FAILURES:", failures if failures else "none")
spark.stop()
sys.exit(1 if failures else 0)
