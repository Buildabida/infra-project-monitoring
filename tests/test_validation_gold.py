import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATION = ROOT / "notebooks/04_validation/09_validation_gold.ipynb"
PROJECT_FACT = ROOT / "notebooks/03_gold/07_gold_fact_project_snapshot.ipynb"
SILVER_VALIDATION = (
    ROOT / "notebooks/04_validation/08_validation_silver_project_flood_map.ipynb"
)
VALIDATION_DOC = ROOT / "docs/validation.md"
DECISIONS = ROOT / "docs/decisions.md"
NOTEBOOKS_README = ROOT / "notebooks/README.md"
RESULTS = "`04-validation`.gold_dq_results"

GOLD_TABLES = [
    "fact_project_snapshot",
    "fact_region_population",
    "fact_region_flood_exposure",
    "dim_date",
    "dim_region",
    "dim_region_boundary",
    "dim_flood_susceptibility",
    "dim_project_status",
    "dim_project",
]

CHECK = re.compile(
    r"NAMED_STRUCT\(\n\s+'table_name', '(?P<table>\w+)', 'attribute', '(?P<attribute>\w+)',\n"
    r"\s+'check_name', '(?P<name>[^']+)',\n"
    r"\s+'failed_rows', CAST\((?P<failed>.+?) AS BIGINT\), "
    r"'total_rows', CAST\((?P<total>.+?) AS BIGINT\),\n"
    r"\s+'action', '(?P<action>stop|flag)',\n"
    r"\s+'details', (?P<details>.+?)\n\s+\)",
    re.DOTALL,
)


def notebook(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source(path, cell_type=None):
    cells = notebook(path)["cells"]
    if cell_type:
        cells = [cell for cell in cells if cell["cell_type"] == cell_type]
    return "\n".join("".join(cell.get("source", [])) for cell in cells)


def sql(path):
    return source(path, "code")


def markdown(path):
    return source(path, "markdown")


def code_without_comments(path):
    return "\n".join(line.split("--", 1)[0] for line in sql(path).splitlines())


def squash(text):
    return " ".join(text.split())


def checks():
    found = [match.groupdict() for match in CHECK.finditer(sql(VALIDATION))]
    assert len(found) == sql(VALIDATION).count("'check_name', '")
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
    code_cells = [cell for cell in nb["cells"] if cell["cell_type"] == "code"]
    assert code_cells
    for cell in code_cells:
        assert "".join(cell["source"]).startswith("%sql\n")
        assert cell["outputs"] == []


def test_02_every_code_cell_has_markdown_before_it():
    cells = notebook(VALIDATION)["cells"]
    assert cells[0]["cell_type"] == "markdown"
    for index, cell in enumerate(cells):
        if cell["cell_type"] == "code":
            assert cells[index - 1]["cell_type"] == "markdown"
    text = markdown(VALIDATION)
    for heading in ["# Validate Gold facts and dimensions", "## Purpose", "## Summary"]:
        assert heading in text
    for label in ["**What:**", "**Why:**", "**STOP**", "**FLAG**"]:
        assert label in text
    for issue in ["#60", "#61", "#62", "#63", "#64"]:
        assert f"Issue {issue}:" in text


def test_03_first_sql_uses_the_project_catalog():
    first_code = sql(VALIDATION).split("%sql\n", 1)[1]
    assert first_code.startswith("USE CATALOG `buildabida-capstone`;")


def test_04_validator_never_changes_gold_or_silver():
    code = code_without_comments(VALIDATION)
    writes = re.findall(
        r"(?:MERGE INTO|INSERT INTO|DELETE FROM|UPDATE|ALTER TABLE|DROP TABLE|TRUNCATE TABLE"
        r"|CREATE (?:OR REPLACE )?TABLE(?: IF NOT EXISTS)?)\s+(`\d\d-[a-z]+`\.\w+)",
        code,
        flags=re.IGNORECASE,
    )
    assert writes
    assert set(writes) == {RESULTS}


def test_05_reads_only_gold_silver_and_its_results_table():
    allowed = {f"`03-gold`.{table}" for table in GOLD_TABLES} | {
        "`02-silver`.silver_project",
        "`02-silver`.silver_project_region_map",
        "`02-silver`.silver_project_flood_map",
        "`02-silver`.silver_region_population",
        "`02-silver`.silver_region_flood_exposure",
        "`02-silver`.silver_population_place_reconciliation",
        "`02-silver`.silver_psgc_place",
        RESULTS,
    }
    tables = set(re.findall(r"`\d\d-[a-z]+`\.\w+", code_without_comments(VALIDATION)))
    assert tables <= allowed, tables - allowed
    for table in GOLD_TABLES:
        assert f"`03-gold`.{table}" in tables, table


def test_06_results_table_has_the_silver_dq_results_columns():
    gold = results_ddl(VALIDATION, "gold_dq_results")
    silver = results_ddl(SILVER_VALIDATION, "silver_dq_results")
    assert gold == silver
    assert "'gold' AS layer" in sql(VALIDATION)


def test_07_evidence_is_saved_before_the_stop_gate():
    text = sql(VALIDATION)
    merge = text.index(f"MERGE INTO {RESULTS} AS target")
    gate = text.index("SELECT ASSERT_TRUE(")
    assert merge < gate
    assert text.count("SELECT ASSERT_TRUE(") == 1
    gate_sql = text[gate:]
    assert f"FROM {RESULTS}" in gate_sql
    assert (
        "COUNT(*) > 0 AND COUNT_IF(status = 'FAIL' AND action = 'stop') = 0" in gate_sql
    )
    assert (
        "validation_run_id = (SELECT validation_run_id FROM gold_validation_context)"
        in (gate_sql)
    )
    # the same Gold runs always give the same validation run ID
    assert (
        "SHA2(CONCAT_WS( '|', project_fact.project_fact_run_id, "
        "population_fact.population_fact_run_id, exposure_fact.exposure_fact_run_id, "
        "validation_rule_version ), 256) AS validation_run_id"
    ) in squash(text)
    # the rule version changes whenever a check changes, so old evidence keeps its own ID
    assert "DEFAULT 'gold-validation-v2'" in text


def test_08_every_check_names_its_columns():
    for item in checks():
        details = item["details"]
        assert details.startswith(("'Columns: ", "CONCAT('Columns: ")), item["name"]


def test_09_check_names_are_unique_within_each_table():
    # the merge key is the validation run, the table and the check name
    keys = [(item["table"], item["name"]) for item in checks()]
    assert len(keys) == len(set(keys))


def test_10_every_table_has_a_uniqueness_check():
    for table in GOLD_TABLES:
        own = [item for item in checks() if item["table"] == table]
        assert any(
            item["attribute"] == "Uniqueness" and item["action"] == "stop"
            for item in own
        ), table


def test_11_issue_checks_exist_with_the_right_action():
    for table, name, action in [
        # issue #60
        ("fact_project_snapshot", "At most one current row per project", "stop"),
        ("fact_project_snapshot", "Physical progress is 0 to 100 or empty", "stop"),
        ("fact_project_snapshot", "Reported budget is zero or more, or empty", "stop"),
        ("fact_project_snapshot", "Source snapshot ID is never empty", "stop"),
        ("fact_project_snapshot", "Every key finds its dimension row", "stop"),
        (
            "fact_project_snapshot",
            "Current rows equal Silver projects, with no stale current rows",
            "stop",
        ),
        (
            "dim_flood_susceptibility",
            "Silver project flood map has a load time on every row",
            "stop",
        ),
        # the regional facts have no current flag, so old rows must not stay (#60)
        ("fact_region_population", "Rows equal Silver, with no old rows left", "stop"),
        (
            "fact_region_flood_exposure",
            "Rows equal Silver, with no old rows left",
            "stop",
        ),
        # issue #61
        ("fact_region_population", "Primary population is above zero", "stop"),
        (
            "fact_region_population",
            "Each region has exactly one primary source per year",
            "stop",
        ),
        (
            "fact_region_population",
            "No population row uses region key 0, so ratios leave it out",
            "stop",
        ),
        (
            "fact_region_population",
            "Region total is below the 2024 census total",
            "flag",
        ),
        # issue #62
        ("fact_region_flood_exposure", "Flood area is zero or more", "stop"),
        ("fact_region_flood_exposure", "Share of region area is 0 to 100", "stop"),
        (
            "fact_region_flood_exposure",
            "Areas use the equal-area CRS, not degrees",
            "stop",
        ),
        (
            "dim_flood_susceptibility",
            "Levels are Unknown, Low, Moderate, High or Very High",
            "stop",
        ),
        (
            "dim_flood_susceptibility",
            "Severity rank is unique within each source system and version",
            "stop",
        ),
        # issue #63
        ("fact_project_snapshot", "One row per project and snapshot", "stop"),
        ("fact_region_population", "One row per region, year and source", "stop"),
        (
            "fact_region_flood_exposure",
            "One row per region, level, MGB snapshot and boundary version",
            "stop",
        ),
        (
            "dim_region",
            "Region key 0 exists once and is not a geographic region",
            "stop",
        ),
        (
            "fact_project_snapshot",
            "Central Office projects use region key 0 and the non-geographic status",
            "stop",
        ),
        (
            "fact_project_snapshot",
            "Region key 0 only when the region match is not MATCHED or MATCHED_WITH_CONFLICT",
            "stop",
        ),
        (
            "fact_project_snapshot",
            "Flood key 0 only when the flood match is not MATCHED",
            "stop",
        ),
        (
            "fact_project_snapshot",
            "Status key 0 only when the Silver status is missing or conflicting",
            "stop",
        ),
        ("fact_project_snapshot", "Date key 0 only when the date is missing", "stop"),
        # issue #64
        ("fact_project_snapshot", "Project count by region equals Silver", "stop"),
        ("fact_project_snapshot", "Budget by region equals Silver", "stop"),
        ("fact_project_snapshot", "Current rows use the Silver DPWH snapshot", "stop"),
        ("fact_project_snapshot", "Projects without a region (key 0)", "flag"),
        ("fact_project_snapshot", "Projects without a flood level (key 0)", "flag"),
    ]:
        assert check(table, name)["action"] == action, (table, name)


def test_12_lineage_is_checked_on_every_table_with_lineage_columns():
    # dim_date is built from a date range, so it has no lineage columns
    for table in GOLD_TABLES:
        if table == "dim_date":
            continue
        item = check(table, "Lineage columns are filled")
        assert item["action"] == "stop", table
        assert "run_id, source_load_ts" in item["details"], table


def test_13_crs_check_names_the_crs_it_found():
    item = check(
        "fact_region_flood_exposure", "Areas use the equal-area CRS, not degrees"
    )
    assert "crs_found" in item["details"]
    assert (
        "DECLARE OR REPLACE VARIABLE expected_area_crs STRING DEFAULT 'EPSG:6933';"
        in (sql(VALIDATION))
    )


def test_14_population_check_records_the_ratio_denominator():
    item = check(
        "fact_region_population",
        "No population row uses region key 0, so ratios leave it out",
    )
    assert "population.primary_people" in item["details"]
    assert "population.primary_rows" in item["details"]


def test_15_reconciliation_records_the_runs_and_snapshot_on_both_sides():
    item = check("fact_project_snapshot", "Project count by region equals Silver")
    for value in [
        "context.project_fact_run_id",
        "context.silver_project_run_id",
        "context.silver_region_map_run_id",
        "context.project_snapshot_id",
    ]:
        assert value in item["details"], value


def test_16_key_zero_rules_match_the_project_fact_notebook():
    validation = squash(code_without_comments(VALIDATION))
    project_fact = squash(code_without_comments(PROJECT_FACT))
    for declaration in [
        (
            "DECLARE OR REPLACE VARIABLE region_key_match_statuses ARRAY<STRING> "
            "DEFAULT ARRAY('MATCHED', 'MATCHED_WITH_CONFLICT');"
        ),
        "DECLARE OR REPLACE VARIABLE flood_key_match_status STRING DEFAULT 'MATCHED';",
    ]:
        assert declaration in validation, declaration
        assert declaration in project_fact, declaration


def test_17_key_zero_and_current_row_rules_are_full_recipes():
    code = squash(code_without_comments(VALIDATION))
    for recipe in [
        # an empty value never passes a STOP check
        (
            "COUNT_IF(is_primary_source AND (population_count IS NULL OR "
            "population_count <= 0)) AS non_positive_rows"
        ),
        (
            "COUNT_IF(region_match_method = non_geographic_method AND NOT ( region_key = 0 "
            "AND region_match_status <=> non_geographic_match_status )) AS central_office_breaks"
        ),
        (
            "COUNT_IF(region_key = 0 AND NOT (is_geographic_region <=> FALSE)) "
            "AS region_key_zero_geographic_rows"
        ),
        # key 0 exactly when the documented case applies, never more and never less
        (
            "COUNT_IF((region_key = 0) = COALESCE( ARRAY_CONTAINS(region_key_match_statuses, "
            "region_match_status), FALSE )) AS region_key_rule_breaks"
        ),
        (
            "COUNT_IF((flood_susceptibility_key = 0) = COALESCE( flood_match_status = "
            "flood_key_match_status, FALSE )) AS flood_key_rule_breaks"
        ),
        (
            "COUNT_IF(is_current_snapshot AND in_silver AND (status_key = 0) <> "
            "(silver_status_raw IS NULL)) AS status_key_rule_breaks"
        ),
        (
            "COUNT_IF(snapshot_date_key = 0 OR (is_current_snapshot AND in_silver AND ( "
            "(start_date_key = 0) <> (silver_start_date IS NULL) OR "
            "(source_completion_date_key = 0) <> (silver_completion_date IS NULL) ))) "
            "AS date_key_rule_breaks"
        ),
        # one current row per project, and current rows come from the Silver snapshot
        (
            "COUNT_IF(is_current_snapshot) - COUNT(DISTINCT CASE WHEN is_current_snapshot "
            "THEN project_key END) AS extra_current_rows"
        ),
        "COUNT_IF(is_current_snapshot AND NOT in_silver) AS stale_current_rows",
        (
            "COUNT_IF(is_current_snapshot AND in_silver AND NOT (source_snapshot_id <=> "
            "silver_snapshot_id)) AS snapshot_mismatch_rows"
        ),
        # Silver gets the same region key rule as Gold before the totals are compared
        (
            "WHEN ARRAY_CONTAINS(region_key_match_statuses, region_map.match_status) "
            "THEN region_map.psgc_region_code ELSE 'KEY_0' END AS region_code"
        ),
    ]:
        assert recipe in code, recipe
    for table in ["population", "exposure"]:
        item = [
            check
            for check in checks()
            if check["name"] == "Rows equal Silver, with no old rows left"
            and check["failed"] == f"ABS({table}.fact_rows - {table}.silver_rows)"
        ]
        assert len(item) == 1, table


def test_18_every_flag_has_a_denominator():
    for item in checks():
        if item["action"] == "flag":
            assert item["total"].strip() not in {"0", "NULL"}, item["name"]


def test_19_no_random_values_or_spatial_work():
    code = code_without_comments(VALIDATION)
    for token in ["uuid(", "rand(", "random(", "monotonically_increasing_id"]:
        assert token not in code.lower(), token
    assert not re.search(r"\bST_\w+\(", code.upper())
    assert "%python" not in code.lower()


def test_20_docs_describe_gold_validation():
    doc = VALIDATION_DOC.read_text(encoding="utf-8")
    assert "## Gold validation" in doc
    assert "09_validation_gold" in doc
    assert "gold_dq_results" in doc
    assert "| D-47 |" in DECISIONS.read_text(encoding="utf-8")
    readme = NOTEBOOKS_README.read_text(encoding="utf-8")
    gold_fact = readme.index("03_gold/07_gold_fact_project_snapshot")
    validator = readme.index("04_validation/09_validation_gold")
    assert gold_fact < validator
