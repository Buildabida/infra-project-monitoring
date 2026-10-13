import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATION = ROOT / "notebooks/04_validation/10_validation_analytics.ipynb"
GOLD_VALIDATION = ROOT / "notebooks/04_validation/09_validation_gold.ipynb"
VALIDATION_DOC = ROOT / "docs/validation.md"
DECISIONS = ROOT / "docs/decisions.md"
NOTEBOOKS_README = ROOT / "notebooks/README.md"
RESULTS = "`04-validation`.analytics_dq_results"
GOLD_RESULTS = "`04-validation`.gold_dq_results"

VIEWS = [
    "analytics_regional_investment",
    "analytics_category_portfolio",
    "analytics_project_delivery_status",
    "analytics_population_equity",
    "analytics_flood_control_exposure",
    "analytics_region_category",
]

CHECK = re.compile(
    r"NAMED_STRUCT\(\n\s+'table_name', '(?P<table>\w+)', 'attribute', '(?P<attribute>\w+)',\n"
    r"\s+'check_name', '(?P<name>[^']+)',\n"
    # a long failed-rows sum can push total_rows onto the next line
    r"\s+'failed_rows', CAST\((?P<failed>[^\n]+?) AS BIGINT\),\s+"
    r"'total_rows', CAST\((?P<total>[^\n]+?) AS BIGINT\),\n"
    r"\s+'action', '(?P<action>stop|flag)',\n"
    r"\s+'details', (?P<details>.+?)\n\s+\)",
    re.DOTALL,
)


def notebook(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source(path, cell_type):
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook(path)["cells"]
        if cell["cell_type"] == cell_type
    )


def sql(path):
    return source(path, "code")


def code_without_comments(path):
    return "\n".join(line.split("--", 1)[0] for line in sql(path).splitlines())


def squash(text):
    return " ".join(text.split())


def checks():
    text = sql(VALIDATION)
    found = [match.groupdict() for match in CHECK.finditer(text)]
    assert len(found) == text.count("'check_name', '")
    return found


def check(table, name):
    own = [item for item in checks() if item["table"] == table and item["name"] == name]
    assert len(own) == 1, (table, name)
    return own[0]


def results_ddl(path, table):
    text = sql(path)
    start = text.index(f"CREATE TABLE IF NOT EXISTS `04-validation`.{table} (\n")
    body = text[start:].split("\n", 1)[1].split("\n)\nUSING DELTA", 1)[0]
    return [column.strip() for column in body.replace("\n", " ").split(",")]


def test_01_notebook_is_a_valid_nbformat_sql_notebook():
    nb = notebook(VALIDATION)
    assert nb["nbformat"] == 4
    assert nb["nbformat_minor"] >= 5
    meta = nb["metadata"]["application/vnd.databricks.v1+notebook"]
    assert meta["language"] == "sql"
    assert meta["notebookName"] == VALIDATION.stem
    ids = [cell["id"] for cell in nb["cells"]]
    assert len(ids) == len(set(ids))
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            assert "".join(cell["source"]).startswith("%sql\n")
            assert cell["outputs"] == []


def test_02_every_code_cell_has_markdown_before_it():
    cells = notebook(VALIDATION)["cells"]
    assert cells[0]["cell_type"] == "markdown"
    for index, cell in enumerate(cells):
        if cell["cell_type"] == "code":
            assert cells[index - 1]["cell_type"] == "markdown", index
    text = source(VALIDATION, "markdown")
    for heading in ["# Validate the analytics views", "## Purpose", "## Summary"]:
        assert heading in text
    for label in ["**What:**", "**Why:**", "**STOP**", "**FLAG**"]:
        assert label in text


def test_03_first_sql_uses_the_project_catalog():
    first_code = sql(VALIDATION).split("%sql\n", 1)[1]
    assert first_code.startswith("USE CATALOG `buildabida-capstone`;")


def test_04_validator_writes_only_its_results_table():
    writes = re.findall(
        r"(?:MERGE INTO|INSERT INTO|DELETE FROM|UPDATE|ALTER TABLE|DROP TABLE|TRUNCATE TABLE"
        r"|CREATE (?:OR REPLACE )?(?:TABLE|VIEW)(?: IF NOT EXISTS)?)\s+(`\d\d-[a-z]+`\.\w+)",
        code_without_comments(VALIDATION),
        flags=re.IGNORECASE,
    )
    assert writes
    assert set(writes) == {RESULTS}


def test_05_reads_only_gold_the_views_and_validation_results():
    tables = set(
        re.findall(r"`(\d\d-[a-z]+)`\.(\w+)", code_without_comments(VALIDATION))
    )
    assert {schema for schema, _ in tables} == {
        "03-gold",
        "04-validation",
        "05-analytics",
    }
    assert {table for schema, table in tables if schema == "05-analytics"} == set(VIEWS)
    assert {table for schema, table in tables if schema == "04-validation"} == {
        "gold_dq_results",
        "analytics_dq_results",
    }


def test_06_results_table_has_the_gold_dq_results_columns():
    assert results_ddl(VALIDATION, "analytics_dq_results") == results_ddl(
        GOLD_VALIDATION, "gold_dq_results"
    )
    assert "'analytics' AS layer" in sql(VALIDATION)


def test_07_validation_run_id_is_deterministic():
    text = sql(VALIDATION)
    assert (
        "SHA2(CONCAT_WS( '|', project_fact.project_fact_run_id, "
        "region_dimension.dim_region_run_id, population_fact.population_fact_run_id, "
        "exposure_fact.exposure_fact_run_id, validation_rule_version ), 256) "
        "AS validation_run_id"
    ) in squash(text)
    assert "DEFAULT 'analytics-validation-v1'" in text
    code = code_without_comments(VALIDATION).lower()
    for token in [
        "uuid(",
        "rand(",
        "random(",
        "monotonically_increasing_id",
        "%python",
    ]:
        assert token not in code, token


def test_08_evidence_merge_key_is_run_table_and_check():
    assert (
        f"MERGE INTO {RESULTS} AS target USING analytics_validation_checks AS source "
        "ON target.validation_run_id = source.validation_run_id "
        "AND target.table_name = source.table_name "
        "AND target.data_quality_check = source.data_quality_check "
        "WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *;"
    ) in squash(sql(VALIDATION))
    keys = [(item["table"], item["name"]) for item in checks()]
    assert len(keys) == len(set(keys))


def test_09_gates_run_in_order_and_evidence_is_saved_before_the_stop_gate():
    text = sql(VALIDATION)
    gates = [match.start() for match in re.finditer(r"SELECT ASSERT_TRUE\(", text)]
    assert len(gates) == 3
    snapshot_gate, gold_gate, stop_gate = gates
    first_check = text.index(
        "CREATE OR REPLACE TEMPORARY VIEW analytics_validation_q1_output"
    )
    merge = text.index(f"MERGE INTO {RESULTS} AS target")
    # the snapshot and gold gates stop the run before any check, the stop gate after the merge
    assert text.index(
        "CREATE OR REPLACE TEMPORARY VIEW analytics_validation_context"
    ) < (snapshot_gate)
    assert snapshot_gate < gold_gate < first_check < merge < stop_gate
    assert "project_snapshot_count = 1 AND project_snapshot_null_rows = 0" in squash(
        text[snapshot_gate:gold_gate]
    )
    stop_sql = squash(text[stop_gate:])
    assert (
        "COUNT(*) > 0 AND COUNT_IF(status = 'FAIL' AND action = 'stop') = 0" in stop_sql
    )
    assert f"FROM {RESULTS}" in stop_sql
    assert (
        "validation_run_id = (SELECT validation_run_id FROM analytics_validation_context)"
        in stop_sql
    )


def test_10_context_counts_the_current_snapshots():
    code = squash(code_without_comments(VALIDATION))
    for recipe in [
        "COUNT(DISTINCT source_snapshot_id) AS project_snapshot_count",
        "COUNT_IF(source_snapshot_id IS NULL) AS project_snapshot_null_rows",
        "FROM `03-gold`.fact_project_snapshot WHERE is_current_snapshot ),",
    ]:
        assert recipe in code, recipe


def test_11_gold_gate_covers_the_population_and_exposure_facts():
    code = squash(code_without_comments(VALIDATION))
    assert f"FROM {GOLD_RESULTS} AS dq" in code
    for recipe in [
        "AND gold_stop_failures = 0",
        "AND current_population_checks > 0",
        "AND current_exposure_checks > 0",
    ]:
        assert recipe in code, recipe


def test_12_check_counts_and_actions():
    found = checks()
    assert sum(item["action"] == "stop" for item in found) == 74
    assert sum(item["action"] == "flag" for item in found) == 13
    assert {item["table"] for item in found} == set(VIEWS)


def test_13_every_view_has_grain_and_lineage_checks():
    for view in VIEWS:
        own = [item for item in checks() if item["table"] == view]
        assert any(
            item["attribute"] == "Uniqueness" and item["action"] == "stop"
            for item in own
        ), view
        assert any(
            item["attribute"] == "Auditability" and item["action"] == "stop"
            for item in own
        ), view


def test_14_every_check_names_its_columns_and_every_flag_has_a_denominator():
    for item in checks():
        details = re.sub(r"\(\s+", "(", item["details"])
        assert details.startswith(("'Columns: ", "CONCAT('Columns: ")), item["name"]
        if item["action"] == "flag":
            assert item["total"].strip() not in {"0", "NULL"}, item["name"]


def test_15_contract_checks_exist_with_the_right_action():
    for table, name, action in [
        # key 0 stays out of every regional view, and q1 accounts for it
        ("analytics_regional_investment", "Region key 0 is never in the view", "stop"),
        (
            "analytics_population_equity",
            "Per-person ratios leave region key 0 out",
            "stop",
        ),
        (
            "analytics_regional_investment",
            "View, key 0, and unknown keys add up to every current project and budget",
            "stop",
        ),
        (
            "analytics_regional_investment",
            "Current projects left out on region key 0",
            "flag",
        ),
        (
            "analytics_regional_investment",
            "At most one current row per project",
            "stop",
        ),
        ("analytics_regional_investment", "BARMM is never ranked", "stop"),
        # q2 strict and broad flood shares
        (
            "analytics_category_portfolio",
            "Broad and strict flood control shares match Gold",
            "stop",
        ),
        (
            "analytics_category_portfolio",
            "Multi-sector projects counted whole in the flood control share",
            "flag",
        ),
        # q4 shares divide by one comparable set of regions
        (
            "analytics_population_equity",
            "A region outside the comparable set shows no share, gap, or per-capita value",
            "stop",
        ),
        (
            "analytics_population_equity",
            "Equity gap is investment share minus comparable population share",
            "stop",
        ),
        # q5 adds level areas only when they do not overlap
        (
            "analytics_flood_control_exposure",
            "A total area appears only when the levels may be added",
            "stop",
        ),
        (
            "analytics_flood_control_exposure",
            "Total area is the sum of the level areas where they may be added",
            "stop",
        ),
        (
            "analytics_flood_control_exposure",
            "Regions whose flood levels overlap, so no total area",
            "flag",
        ),
    ]:
        assert check(table, name)["action"] == action, (table, name)


def test_16_docs_describe_analytics_validation():
    doc = VALIDATION_DOC.read_text(encoding="utf-8")
    assert "## Analytics validation" in doc
    assert "10_validation_analytics" in doc
    assert "analytics_dq_results" in doc
    assert "| D-52 |" in DECISIONS.read_text(encoding="utf-8")
    readme = NOTEBOOKS_README.read_text(encoding="utf-8")
    gold = readme.index("04_validation/09_validation_gold")
    views = readme.index("05_analytics/01_business_questions")
    validator = readme.index("04_validation/10_validation_analytics")
    assert gold < views < validator
