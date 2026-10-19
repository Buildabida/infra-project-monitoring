"""Tests for notebooks/06_data_quality/01_end_to_end_quality_gate.py.

The scenario tests run the real notebook on local Spark with Delta against small
synthetic tables. They never touch Databricks or production data. Without pyspark
and delta-spark installed they are skipped, and the contract tests still run.
"""

import copy
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
import spark_harness

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "notebooks/06_data_quality/01_end_to_end_quality_gate.py"
JOB = ROOT / "resources/buildabida_full_pipeline.job.yml"

BRONZE_EVENT = datetime(2026, 10, 16, 0, 0, 0, tzinfo=timezone.utc)
VALIDATED = BRONZE_EVENT + timedelta(hours=1)
SNAPSHOT = "metadata-dpwh-current"
BRONZE_TABLES = [
    "boundaries",
    "census_2024_table_c",
    "dpwh_projects",
    "flood_control_projects",
    "flood_susceptibility",
    "psgc",
]
SILVER_VALIDATORS = {
    "silver-geography": [
        "silver_psgc_place",
        "silver_population_place_reconciliation",
        "silver_region_population",
    ],
    "silver-province": [
        "silver_project_province_map",
        "silver_province_reporting_area",
        "silver_province_reporting_area_population",
    ],
    "silver-projects": ["silver_dpwh_project_component", "silver_project"],
    "silver-source-match": [
        "silver_flood_control_component",
        "silver_project_source_match",
    ],
    "silver-region-map": ["silver_project_region_map"],
    "silver-mgb": ["silver_mgb_flood_area"],
    "silver-exposure": ["silver_region_flood_exposure"],
    "silver-flood-map": ["silver_project_flood_map"],
}
GOLD_RUNS = {
    "fact_project_snapshot": "gold-project-run",
    "fact_region_population": "gold-population-run",
    "fact_region_flood_exposure": "gold-exposure-run",
}
GOLD_TABLES = [
    "dim_date",
    "dim_flood_susceptibility",
    "dim_project",
    "dim_project_status",
    "dim_region",
    "dim_region_boundary",
    *GOLD_RUNS,
]
ANALYTICS_TABLES = [
    "analytics_investment_distribution",
    "analytics_population_equity",
    "analytics_flood_alignment",
    "analytics_implementation_monitoring",
    "analytics_infrastructure_network",
    "analytics_integration_coverage",
    "analytics_layer",
]
# each validator saves all its rows in one write with one timestamp, at its own time
SAVED_AT = {
    name: VALIDATED + timedelta(minutes=minute)
    for minute, name in enumerate(
        [
            "bronze-run-1",
            "config-run",
            *SILVER_VALIDATORS,
            "gold-run",
            "gold-province-run",
            "analytics-run",
        ]
    )
}
# like the real geography validator before #138: one validation run ID per table
PER_TABLE_RUN_IDS = {"silver-geography"}
EVIDENCE_COLUMNS = (
    "validation_run_id string, pipeline_run_id string, table_name string, "
    "source_snapshot_id string, status string, action string, run_ts timestamp"
)


def evidence_row(validator, table, pipeline_run_id="run", **changes):
    run_id = f"{validator}-{table}" if validator in PER_TABLE_RUN_IDS else validator
    row = {
        "validation_run_id": run_id,
        "pipeline_run_id": pipeline_run_id,
        "table_name": table,
        "source_snapshot_id": SNAPSHOT,
        "status": "PASS",
        "action": "stop",
        "run_ts": SAVED_AT[validator],
    }
    row.update(changes)
    return row


def healthy_world():
    """Every validator passed after the latest Bronze load, and the layers agree."""
    projects = [(1, Decimal("100.00")), (2, Decimal("250.50")), (3, None)]
    return {
        "load_log": [
            {
                "table_name": table,
                "snapshot_id": SNAPSHOT
                if table == "dpwh_projects"
                else f"snap-{table}",
                "status": "SKIPPED_IDEMPOTENT",
                "started_at": BRONZE_EVENT - timedelta(minutes=5),
                "completed_at": BRONZE_EVENT,
            }
            for table in BRONZE_TABLES
        ],
        "dq_results": [
            {
                "run_id": "bronze-run-1",
                "table_name": table,
                "snapshot_id": SNAPSHOT
                if table == "dpwh_projects"
                else f"snap-{table}",
                "status": "PASS",
                "action": "stop",
                "run_ts": SAVED_AT["bronze-run-1"],
            }
            for table in BRONZE_TABLES
        ],
        "silver_config_dq_results": [
            {
                "run_id": "config-run",
                "table_name": "config_place_name_alias",
                "status": "PASS",
                "action": "stop",
                "run_ts": SAVED_AT["config-run"],
            }
        ],
        "silver_dq_results": [
            evidence_row(run, table)
            for run, tables in SILVER_VALIDATORS.items()
            for table in tables
        ],
        "gold_dq_results": [
            evidence_row("gold-run", table, GOLD_RUNS.get(table, "dimension-run"))
            for table in GOLD_TABLES
        ]
        + [
            evidence_row("gold-province-run", table, "gold-project-run")
            for table in [
                "dim_province_reporting_area",
                "fact_project_snapshot",
                "fact_province_reporting_area_population",
            ]
        ],
        "analytics_dq_results": [
            evidence_row("analytics-run", table, "gold-project-run")
            for table in ANALYTICS_TABLES
        ],
        "silver_project": [
            {
                "project_key": key,
                "source_snapshot_id": SNAPSHOT,
                "reported_budget_pesos": budget,
                "run_id": "silver-project-run",
            }
            for key, budget in projects
        ],
        "fact_project_snapshot": [
            {
                "project_key": key,
                "is_current_snapshot": True,
                "source_snapshot_id": SNAPSHOT,
                "reported_budget_pesos": budget,
                "run_id": "gold-project-run",
            }
            for key, budget in projects
        ]
        # an older snapshot row is history and must not count
        + [
            {
                "project_key": 1,
                "is_current_snapshot": False,
                "source_snapshot_id": "metadata-dpwh-older",
                "reported_budget_pesos": Decimal("90.00"),
                "run_id": "gold-project-run-old",
            }
        ],
        "fact_region_population": [{"run_id": "gold-population-run"}],
        "fact_region_flood_exposure": [{"run_id": "gold-exposure-run"}],
        "analytics_implementation_monitoring": [
            {
                "project_key": key,
                "reported_budget_pesos": budget,
                "source_snapshot_id": SNAPSHOT,
            }
            for key, budget in projects
        ],
    }


SCHEMAS = {
    "load_log": (
        "s01_bronze",
        (
            "table_name string, snapshot_id string, status string, "
            "started_at timestamp, completed_at timestamp"
        ),
    ),
    "dq_results": (
        "s04_validation",
        (
            "run_id string, table_name string, snapshot_id string, status string, "
            "action string, run_ts timestamp"
        ),
    ),
    "silver_config_dq_results": (
        "s04_validation",
        "run_id string, table_name string, status string, action string, run_ts timestamp",
    ),
    "silver_dq_results": ("s04_validation", EVIDENCE_COLUMNS),
    "gold_dq_results": ("s04_validation", EVIDENCE_COLUMNS),
    "analytics_dq_results": ("s04_validation", EVIDENCE_COLUMNS),
    "silver_project": (
        "s02_silver",
        (
            "project_key bigint, source_snapshot_id string, "
            "reported_budget_pesos decimal(38,2), run_id string"
        ),
    ),
    "fact_project_snapshot": (
        "s03_gold",
        (
            "project_key bigint, is_current_snapshot boolean, source_snapshot_id string, "
            "reported_budget_pesos decimal(38,2), run_id string"
        ),
    ),
    "fact_region_population": ("s03_gold", "run_id string"),
    "fact_region_flood_exposure": ("s03_gold", "run_id string"),
    "analytics_implementation_monitoring": (
        "s05_analytics",
        "project_key bigint, reported_budget_pesos decimal(38,2), source_snapshot_id string",
    ),
}


@pytest.fixture(scope="module")
def spark():
    session = spark_harness.start_spark()
    if session is None:
        pytest.skip("pyspark and delta-spark are not installed")
    yield session
    spark_harness.stop_spark(session)


def write_world(spark, world):
    for table, (schema, columns) in SCHEMAS.items():
        spark.sql(f"CREATE DATABASE IF NOT EXISTS {schema}")
        names = [part.split()[0] for part in columns.split(", ")]
        rows = [tuple(row[name] for name in names) for row in world[table]]
        spark.createDataFrame(rows, columns).write.mode("overwrite").format(
            "parquet"
        ).saveAsTable(f"{schema}.{table}")


@pytest.fixture
def world(spark):
    spark.sql("DROP TABLE IF EXISTS s04_validation.quality_gate_results")
    spark.sql("DROP VIEW IF EXISTS s04_validation.quality_gate_summary")
    return copy.deepcopy(healthy_world())


def run_gate(spark, world, job_run_id="123"):
    write_world(spark, world)
    return spark_harness.run_notebook(spark, GATE, {"job_run_id": job_run_id})


def gate_rows(spark, gate_run_id):
    return {
        row["check_scope"]: row
        for row in spark.sql(
            "SELECT * FROM s04_validation.quality_gate_results WHERE gate_run_id = :id",
            args={"id": gate_run_id},
        ).collect()
    }


def summary(spark, layer="ALL"):
    return spark.sql(
        "SELECT * FROM s04_validation.quality_gate_summary WHERE layer = :layer "
        "ORDER BY evaluated_at DESC LIMIT 1",
        args={"layer": layer},
    ).first()


def latest_gate_id(spark):
    return spark.sql(
        "SELECT gate_run_id FROM s04_validation.quality_gate_results "
        "ORDER BY run_ts DESC LIMIT 1"
    ).first()["gate_run_id"]


def expect_stop(spark, world, match):
    with pytest.raises(RuntimeError, match=match):
        run_gate(spark, world)
    # the result is saved before the gate raises
    return gate_rows(spark, latest_gate_id(spark))


# Scenario 1: all required validations pass
def test_gate_passes_when_every_validator_passed(spark, world):
    namespace = run_gate(spark, world)
    rows = gate_rows(spark, namespace["gate_run_id"])
    assert len(rows) == 13 + 4
    assert {row["status"] for row in rows.values()} == {"PASS"}
    overall = summary(spark)
    assert overall["gate_status"] == "PASS"
    assert overall["failed_stop_checks"] == 0
    assert overall["missing_checks"] == 0
    assert overall["job_run_id"] == "123"
    assert overall["source_snapshot_id"] == SNAPSHOT


# Scenario 2: one STOP validation fails
def test_one_failed_stop_check_stops_the_gate(spark, world):
    world["silver_dq_results"][-1]["status"] = "FAIL"
    rows = expect_stop(spark, world, "silver_validation_project_flood_map")
    failed = rows["silver_validation_project_flood_map"]
    assert failed["status"] == "FAIL"
    assert failed["failed_stop_checks"] == 1
    assert "1 blocking checks failed" in failed["details"]
    assert summary(spark)["gate_status"] == "STOP"
    assert summary(spark, "silver")["gate_status"] == "STOP"
    assert summary(spark, "gold")["gate_status"] == "PASS"


def test_bronze_error_blocks_even_on_a_flag_check(spark, world):
    world["dq_results"][0].update(status="ERROR", action="flag")
    rows = expect_stop(spark, world, "bronze_validation")
    assert rows["bronze_validation"]["failed_stop_checks"] == 1


# Scenario 3: one non-blocking FLAG exists
def test_flag_findings_pass_and_stay_visible(spark, world):
    world["gold_dq_results"].append(
        evidence_row(
            "gold-run",
            "fact_project_snapshot",
            "gold-project-run",
            status="FLAG",
            action="flag",
        )
    )
    # the october 16 09a run saved two flag findings as FAIL with action flag
    world["gold_dq_results"].append(
        evidence_row(
            "gold-province-run",
            "fact_project_snapshot",
            "gold-project-run",
            status="FAIL",
            action="flag",
        )
    )
    namespace = run_gate(spark, world)
    rows = gate_rows(spark, namespace["gate_run_id"])
    assert rows["gold_validation"]["status"] == "FLAG"
    assert rows["gold_validation_province_reporting"]["status"] == "FLAG"
    overall = summary(spark)
    assert overall["gate_status"] == "FLAG"
    assert overall["flagged_checks"] == 2
    assert overall["failed_stop_checks"] == 0


# Scenario 4: a required validation result is missing
def test_missing_validator_evidence_never_passes(spark, world):
    world["analytics_dq_results"] = []
    rows = expect_stop(spark, world, "analytics_validation")
    missing = rows["analytics_validation"]
    assert missing["status"] == "FAIL"
    assert missing["missing_checks"] == len(ANALYTICS_TABLES)
    assert "no saved evidence" in missing["details"]
    assert rows["evidence_matches_current_gold"]["status"] == "FAIL"
    assert summary(spark)["missing_checks"] >= len(ANALYTICS_TABLES)


def test_validator_run_missing_one_table_stops(spark, world):
    world["dq_results"] = [
        row for row in world["dq_results"] if row["table_name"] != "psgc"
    ]
    rows = expect_stop(spark, world, "missing tables: psgc")
    assert rows["bronze_validation"]["missing_checks"] == 1


# Scenario 5: validation results belong to a different snapshot or run
def test_analytics_evidence_from_another_snapshot_stops(spark, world):
    for row in world["analytics_dq_results"]:
        row["source_snapshot_id"] = "metadata-dpwh-older"
    rows = expect_stop(spark, world, "evidence_matches_current_gold")
    assert rows["evidence_matches_current_gold"]["status"] == "FAIL"


def test_gold_evidence_for_an_older_fact_run_stops(spark, world):
    for row in world["fact_region_population"]:
        row["run_id"] = "gold-population-run-rebuilt-after-validation"
    rows = expect_stop(spark, world, "Gold facts with evidence for the current run=2")
    assert rows["evidence_matches_current_gold"]["failed_stop_checks"] == 1


def test_layers_on_different_snapshots_stop(spark, world):
    for row in world["analytics_implementation_monitoring"]:
        row["source_snapshot_id"] = "metadata-dpwh-older"
    rows = expect_stop(spark, world, "dpwh_snapshot_lineage")
    assert rows["dpwh_snapshot_lineage"]["status"] == "FAIL"


def test_evidence_older_than_the_latest_bronze_load_is_stale(spark, world):
    world["load_log"].append(
        {
            "table_name": "psgc",
            "snapshot_id": "snap-psgc",
            "status": "FAILED",
            "started_at": VALIDATED + timedelta(hours=1),
            "completed_at": VALIDATED + timedelta(hours=1),
        }
    )
    rows = expect_stop(spark, world, "stale")
    assert rows["silver_validation_projects"]["status"] == "FAIL"
    assert rows["silver_validation_projects"]["missing_checks"] == 2


# Scenario 6: the same accepted data is evaluated twice
def test_evaluating_the_same_evidence_twice_adds_no_rows(spark, world):
    first = run_gate(spark, world, job_run_id="1")["gate_run_id"]
    second = run_gate(spark, world, job_run_id="2")["gate_run_id"]
    assert first == second
    count = spark.sql(
        "SELECT COUNT(*) AS n, MAX(job_run_id) AS job FROM s04_validation.quality_gate_results"
    ).first()
    assert count["n"] == 17
    assert count["job"] == "2"


# Scenario 7: a failed gate blocks the dashboard refresh. The job wiring is in
# test_pipeline_job_and_dashboard.py; here the gate task itself must fail.
def test_failed_gate_raises_so_the_dashboard_task_cannot_start(spark, world):
    world["fact_project_snapshot"].append(dict(world["fact_project_snapshot"][0]))
    rows = expect_stop(spark, world, "STOP: end-to-end quality gate")
    assert rows["project_count_reconciliation"]["status"] == "FAIL"
    assert rows["reported_budget_reconciliation"]["status"] == "FAIL"
    assert "gate_status" in summary(spark).asDict()


# Scenario 8: recovery after the underlying problem is fixed
def test_gate_recovers_after_the_validator_is_fixed_and_rerun(spark, world):
    world["gold_dq_results"][0]["status"] = "FAIL"
    expect_stop(spark, world, "gold_validation")
    # the validator reruns on the same data: same validation run ID, new run time
    world["gold_dq_results"][0]["status"] = "PASS"
    for row in world["gold_dq_results"]:
        if row["validation_run_id"] == "gold-run":
            row["run_ts"] = VALIDATED + timedelta(minutes=30)
    namespace = run_gate(spark, world)
    rows = gate_rows(spark, namespace["gate_run_id"])
    assert {row["status"] for row in rows.values()} == {"PASS"}
    assert summary(spark)["gate_status"] == "PASS"


def test_missing_budget_that_became_zero_stops(spark, world):
    # a sum ignores NULL, so only the count of projects with a budget sees this
    world["analytics_implementation_monitoring"][2]["reported_budget_pesos"] = Decimal(
        "0.00"
    )
    rows = expect_stop(spark, world, "reported_budget_reconciliation")
    assert rows["reported_budget_reconciliation"]["failed_stop_checks"] == 1
    assert "Analytics=3" in rows["reported_budget_reconciliation"]["details"]


def test_changed_budget_total_stops(spark, world):
    world["fact_project_snapshot"][1]["reported_budget_pesos"] = Decimal("250.00")
    rows = expect_stop(spark, world, "reported_budget_reconciliation")
    assert rows["reported_budget_reconciliation"]["status"] == "FAIL"


# Contract tests: these run without Spark.
def gate_registry():
    text = GATE.read_text(encoding="utf-8")
    return re.findall(r"\('(bronze|silver|gold|analytics)', '(\w+)'", text)


def test_registry_lists_every_validator_task_in_the_job():
    job_validators = set(
        re.findall(r"task_key: (\w*validation\w*)\n", JOB.read_text(encoding="utf-8"))
    )
    assert {task for _, task in gate_registry()} == job_validators


def test_registry_notebooks_exist():
    text = GATE.read_text(encoding="utf-8")
    for notebook in re.findall(r"'(04_validation/\w+)'", text):
        found = [
            (ROOT / "notebooks" / notebook).with_suffix(suffix)
            for suffix in (".ipynb", ".py", ".sql")
        ]
        assert any(path.exists() for path in found), notebook


def test_gate_saves_evidence_before_it_raises():
    text = GATE.read_text(encoding="utf-8")
    assert text.index("MERGE INTO `04-validation`.quality_gate_results") < text.index(
        "raise RuntimeError"
    )


def test_gate_uses_no_third_party_quality_framework():
    text = GATE.read_text(encoding="utf-8").lower()
    for name in ("great_expectations", "great expectations", "soda", "deequ"):
        assert name not in text


# Regression tests for the first Databricks run on October 19, 2026, where the gate
# grouped evidence by run ID and wrongly reported missing geography tables.
def test_validator_that_gives_each_table_its_own_run_id_passes(spark, world):
    namespace = run_gate(spark, world)
    geography = gate_rows(spark, namespace["gate_run_id"])[
        "silver_validation_geography_population"
    ]
    assert geography["status"] == "PASS"
    assert geography["required_checks"] == 3
    assert geography["missing_checks"] == 0


def test_gold_validators_that_share_a_table_stay_separate(spark, world):
    # both Gold validators write fact_project_snapshot rows to gold_dq_results
    world["gold_dq_results"].append(
        evidence_row(
            "gold-province-run",
            "fact_project_snapshot",
            "gold-project-run",
            status="FAIL",
        )
    )
    rows = expect_stop(spark, world, "gold_validation_province_reporting")
    assert rows["gold_validation_province_reporting"]["failed_stop_checks"] == 1
    assert rows["gold_validation"]["status"] == "PASS"


def test_rows_from_an_older_run_of_the_same_validator_are_ignored(spark, world):
    world["silver_dq_results"].append(
        evidence_row(
            "silver-projects",
            "silver_project",
            status="FAIL",
            run_ts=SAVED_AT["silver-projects"] - timedelta(minutes=30),
        )
    )
    namespace = run_gate(spark, world)
    rows = gate_rows(spark, namespace["gate_run_id"])
    assert rows["silver_validation_projects"]["status"] == "PASS"
    assert rows["silver_validation_projects"]["required_checks"] == 2
