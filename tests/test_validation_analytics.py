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

# the six capstone insight views (D-56)
VIEWS = [
    "analytics_investment_distribution",
    "analytics_population_equity",
    "analytics_flood_alignment",
    "analytics_implementation_monitoring",
    "analytics_infrastructure_network",
    "analytics_integration_coverage",
]
LAYER = "analytics_layer"
RETIRED_VIEWS = [
    "analytics_regional_investment",
    "analytics_category_portfolio",
    "analytics_project_delivery_status",
    "analytics_flood_control_exposure",
    "analytics_region_category",
    "analytics_infrastructure_year_trend",
    "analytics_infrastructure_year_sector",
    "analytics_delivery_cohort",
    "analytics_project_size_concentration",
    "analytics_implementing_office_portfolio",
    "analytics_region_project_progress",
    "analytics_reporting_area_investment",
    "analytics_reporting_area_category",
    "analytics_reporting_area_delivery_status",
    "analytics_reporting_area_population_equity",
    "analytics_reporting_area_project_size_concentration",
]
# stop and flag checks per table. a change here needs the docs to change too
CHECK_COUNTS = {
    LAYER: (4, 0),
    "analytics_investment_distribution": (17, 5),
    "analytics_population_equity": (14, 2),
    "analytics_flood_alignment": (15, 3),
    "analytics_implementation_monitoring": (12, 4),
    "analytics_infrastructure_network": (10, 3),
    "analytics_integration_coverage": (12, 11),
}

CHECK = re.compile(
    r"NAMED_STRUCT\(\n\s+'table_name', '(?P<table>\w+)', 'attribute', '(?P<attribute>\w+)',\n"
    r"\s+'check_name', '(?P<name>[^']+)',\n"
    r"\s+'failed_rows', CAST\((?P<failed>[^\n]+?) AS BIGINT\), "
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
        r"(?:MERGE INTO|INSERT INTO|DELETE FROM|UPDATE|ALTER TABLE|DROP \w+|TRUNCATE TABLE"
        r"|CREATE (?:OR REPLACE )?(?:TABLE|VIEW)(?: IF NOT EXISTS)?)\s+(`\d\d-[a-z]+`\.\w+)",
        code_without_comments(VALIDATION),
        flags=re.IGNORECASE,
    )
    assert writes
    assert set(writes) == {RESULTS}


def test_05_reads_only_gold_the_six_views_and_validation_results():
    code = code_without_comments(VALIDATION)
    tables = set(re.findall(r"`(\d\d-[a-z]+)`\.(\w+)", code))
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
    # the layer check lists every view in the schema from the catalog
    assert (
        "FROM information_schema.views AS views WHERE views.table_schema = '05-analytics'"
        in squash(code)
    )
    for token in ["01-bronze", "02-silver", "%python"]:
        assert token not in code, token


def test_06_results_table_has_the_gold_dq_results_columns():
    assert results_ddl(VALIDATION, "analytics_dq_results") == results_ddl(
        GOLD_VALIDATION, "gold_dq_results"
    )
    assert "'analytics' AS layer" in sql(VALIDATION)


def test_07_validation_run_id_is_deterministic():
    text = sql(VALIDATION)
    # the d-52 recipe gains the two d-57 province runs, so new province data gives a new id
    assert (
        "SHA2(CONCAT_WS( '|', project_fact.project_fact_run_id, "
        "region_dimension.dim_region_run_id, population_fact.population_fact_run_id, "
        "exposure_fact.exposure_fact_run_id, province_area.province_area_run_id, "
        "province_population.province_population_run_id, validation_rule_version ), 256) "
        "AS validation_run_id"
    ) in squash(text)
    assert "DEFAULT 'analytics-validation-v4'" in text
    code = code_without_comments(VALIDATION)
    for old in [
        "analytics-validation-v1",
        "analytics-validation-v2",
        "analytics-validation-v3",
    ]:
        assert old not in code, old
    lowered = code.lower()
    for token in ["uuid(", "rand(", "random(", "monotonically_increasing_id"]:
        assert token not in lowered, token


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
    assert len(gates) == 4
    snapshot_gate, gold_gate, province_gate, stop_gate = gates
    first_check = text.index(
        "CREATE OR REPLACE TEMPORARY VIEW analytics_validation_current"
    )
    rerun = text.index(
        "CREATE OR REPLACE TEMPORARY VIEW analytics_validation_rerun_metrics"
    )
    merge = text.index(f"MERGE INTO {RESULTS} AS target")
    assert (
        text.index("CREATE OR REPLACE TEMPORARY VIEW analytics_validation_context")
        < snapshot_gate
    )
    assert (
        snapshot_gate
        < gold_gate
        < province_gate
        < first_check
        < rerun
        < merge
        < stop_gate
    )
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


def test_10_gold_gate_covers_the_population_and_exposure_facts():
    code = squash(code_without_comments(VALIDATION))
    assert f"FROM {GOLD_RESULTS} AS dq" in code
    for recipe in [
        "AND gold_stop_failures = 0",
        "AND current_population_checks > 0",
        "AND current_exposure_checks > 0",
    ]:
        assert recipe in code, recipe


def test_11_check_counts_and_actions():
    found = checks()
    assert {item["table"] for item in found} == set(CHECK_COUNTS)
    for table, (stops, flags) in CHECK_COUNTS.items():
        own = [item for item in found if item["table"] == table]
        assert sum(item["action"] == "stop" for item in own) == stops, table
        assert sum(item["action"] == "flag" for item in own) == flags, table
    assert sum(item["action"] == "stop" for item in found) == 84
    assert sum(item["action"] == "flag" for item in found) == 28
    doc = VALIDATION_DOC.read_text(encoding="utf-8")
    assert "There are 84 STOP checks." in doc
    assert "There are 28 FLAG checks." in doc


def test_12_every_view_has_grain_completeness_accuracy_and_lineage_checks():
    for view in VIEWS:
        own = [
            item
            for item in checks()
            if item["table"] == view and item["action"] == "stop"
        ]
        attributes = {item["attribute"] for item in own}
        assert {
            "Uniqueness",
            "Completeness",
            "Accuracy",
            "Consistency",
            "Auditability",
        } <= attributes, view
    # each lineage check compares the view with the one snapshot the gate allowed
    code = squash(code_without_comments(VALIDATION))
    for prefix in ["inv", "eq", "fa", "im", "net", "ic"]:
        assert (
            f"FROM analytics_validation_{prefix}_output AS output CROSS JOIN analytics_validation_context AS context"
        ) in code, prefix


def test_13_every_check_names_its_columns_and_every_flag_has_a_denominator():
    for item in checks():
        details = re.sub(r"\(\s+", "(", item["details"])
        assert details.startswith(("'Columns: ", "CONCAT('Columns: ")), item["name"]
        if item["action"] == "flag":
            assert item["total"].strip() not in {"0", "NULL"}, item["name"]


def test_14_layer_contract_names_the_six_views_and_every_retired_view():
    code = squash(code_without_comments(VALIDATION))
    expected = ", ".join(f"'{view}'" for view in VIEWS)
    assert (
        f"DECLARE OR REPLACE VARIABLE expected_views ARRAY<STRING> DEFAULT ARRAY( {expected} );"
        in code
    )
    retired = ", ".join(f"'{view}'" for view in RETIRED_VIEWS)
    assert (
        f"DECLARE OR REPLACE VARIABLE retired_views ARRAY<STRING> DEFAULT ARRAY( {retired} );"
        in code
    )
    for name in [
        "All six D-56 Analytics views exist",
        "No retired or unexpected view remains in 05-analytics",
        "analytics_region_project_progress is not part of the Analytics layer",
        "A rerun on the same Gold data gives the same check results",
    ]:
        assert check(LAYER, name)["action"] == "stop", name


def test_15_contract_checks_exist_with_the_right_action():
    inv = "analytics_investment_distribution"
    eq = "analytics_population_equity"
    fa = "analytics_flood_alignment"
    im = "analytics_implementation_monitoring"
    net = "analytics_infrastructure_network"
    ic = "analytics_integration_coverage"
    for table, name, action in [
        (inv, "At most one current Gold row per project", "stop"),
        (inv, "Key 0 is never in the view at either level", "stop"),
        (
            inv,
            "Each level plus key 0 adds up to every current project and budget",
            "stop",
        ),
        (
            inv,
            "Project count, projects with a budget, and budget match Gold and a NULL budget stays NULL",
            "stop",
        ),
        (inv, "Only REPORTED members are ranked and BARMM is never ranked", "stop"),
        (
            inv,
            "Cohort shares add up to 100 within each level and cohort and member shares add up to 100 within each level",
            "stop",
        ),
        (inv, "Shares and running shares are between 0 and 100", "stop"),
        (inv, "Current projects left out on region key 0", "flag"),
        (inv, "Projects with no infrastructure year (infra_year NULL)", "flag"),
        (eq, "Per-person ratios leave key 0 out", "stop"),
        (
            eq,
            "View population adds up to the Gold primary reporting-area population",
            "stop",
        ),
        (
            eq,
            "An area outside the comparable set shows no share, gap, ratio, or per-capita value",
            "stop",
        ),
        (
            eq,
            "Investment, comparable population, and population shares each add up to 100",
            "stop",
        ),
        (eq, "Reporting areas outside the equity comparison", "flag"),
        (fa, "Every current project outside key 0 lands in a published class", "stop"),
        (
            fa,
            "Flood-control, other, and uncategorized add up to the project count",
            "stop",
        ),
        (
            fa,
            "Each region adds up to its project count in view 1, and the view adds up to Gold outside key 0",
            "stop",
        ),
        (fa, "Area appears only on MGB level rows", "stop"),
        (fa, "A region with no mapped DPWH project keeps NULL project figures", "stop"),
        (fa, "Projects whose point is in more than one MGB level (AMBIGUOUS)", "flag"),
        (im, "Rows and budget add up to every current Gold project and budget", "stop"),
        (
            im,
            "Review indicators, reason count, and needs_review follow the documented rules",
            "stop",
        ),
        (im, "A For Procurement project never raises a progress indicator", "stop"),
        (
            im,
            "Progress, flags, and budget match Gold and unavailable values stay NULL",
            "stop",
        ),
        (im, "Projects with at least one review indicator", "flag"),
        (
            net,
            "Each mappable point sits in its own display cell and other rows have none",
            "stop",
        ),
        (
            net,
            "Region and reporting-area population match Gold and key 0 has none",
            "stop",
        ),
        (net, "Projects without a mappable point", "flag"),
        (ic, "Exactly the eleven documented links are present", "stop"),
        (
            ic,
            "Matched and unmatched rows of every link add up to every current Gold project and budget",
            "stop",
        ),
        (
            ic,
            "Geography-linked projects equal the Gold projects with an official region",
            "stop",
        ),
        (ic, "Shares of every link add up to 100", "stop"),
        (ic, "Projects not placed in one MGB flood level", "flag"),
    ]:
        assert check(table, name)["action"] == action, (table, name)


def test_16_rebuilds_are_written_apart_from_the_views():
    code = squash(code_without_comments(VALIDATION))
    for recipe in [
        # one current gold read with left joins, so a missing dimension row breaks the totals
        "FROM `03-gold`.fact_project_snapshot AS fact LEFT JOIN `03-gold`.dim_region AS region",
        # the flood class and status reason in a different form from the views
        (
            "CASE fact.flood_match_status WHEN 'MATCHED' THEN level.flood_susceptibility_level WHEN 'UNMATCHED' THEN "
            "IF(fact.coordinate_status <=> 'VALID_PAIR', 'OUTSIDE_MAPPED_ZONES', 'NO_USABLE_POINT')"
        ),
        "CASE WHEN status.status_group IS NOT NULL THEN 'MAPPED' WHEN fact.status_key = 0 THEN 'NO_SOURCE_STATUS'",
        # counts with count(*) and count_if, where the views count distinct projects
        "COUNT(*) AS project_count, COUNT_IF(reported_budget_pesos IS NOT NULL) AS projects_with_budget",
        # the links rebuilt with union all, where the view uses one inline pass
        "SELECT 'PSGC_REGION' AS integration_link",
        "UNION ALL SELECT 'OFFICIAL_FLOOD_LIST' AS integration_link",
        # null-safe comparison, so a null that turned into 0 is a break
        "NOT (output.total_reported_budget_pesos <=> expected.budget)",
        # the newest primary population with a join, where the views use qualify
        "INNER JOIN newest_year ON population.reference_year = newest_year.reference_year",
    ]:
        assert recipe in code, recipe
    assert "LATERAL VIEW" not in code


def test_17_checks_save_under_the_right_run_and_snapshot():
    text = squash(sql(VALIDATION))
    assert (
        "CASE checks.table_name WHEN 'analytics_population_equity' THEN context.population_fact_run_id "
        "WHEN 'analytics_flood_alignment' THEN context.exposure_fact_run_id "
        "ELSE context.project_fact_run_id END"
    ) in text
    assert (
        "CASE checks.table_name WHEN 'analytics_flood_alignment' THEN context.mgb_source_snapshot_id "
        "ELSE context.project_snapshot_id END AS source_snapshot_id"
    ) in text


def test_18_rerun_check_compares_with_saved_evidence_of_the_same_run():
    code = squash(code_without_comments(VALIDATION))
    assert (
        f"LEFT JOIN {RESULTS} AS saved ON saved.validation_run_id = context.validation_run_id "
        "AND saved.table_name = current_checks.table_name "
        "AND saved.data_quality_check = current_checks.check_name"
    ) in code
    assert "NOT (saved.failed_rows <=> current_checks.failed_rows)" in code


def test_19_docs_describe_analytics_validation():
    doc = VALIDATION_DOC.read_text(encoding="utf-8")
    assert "## Analytics validation" in doc
    assert "10_validation_analytics" in doc
    assert "analytics_dq_results" in doc
    assert "analytics-validation-v4" in doc
    assert "11_validation_regional_project_progress" not in doc
    decisions = DECISIONS.read_text(encoding="utf-8")
    for decision in ["| D-52 |", "| D-56 |"]:
        assert decision in decisions, decision
    readme = NOTEBOOKS_README.read_text(encoding="utf-8")
    gold = readme.index("04_validation/09_validation_gold")
    views = readme.index("05_analytics/01_business_questions")
    validator = readme.index("04_validation/10_validation_analytics")
    assert gold < views < validator
    assert not (
        ROOT / "notebooks/04_validation/11_validation_regional_project_progress.ipynb"
    ).exists()
    assert not (
        ROOT / "notebooks/05_analytics/02_regional_project_progress.ipynb"
    ).exists()


def test_20_province_gate_and_checks_cover_d57():
    code = squash(code_without_comments(VALIDATION))
    # the province gold validation must pass before any analytics check
    for recipe in [
        "DECLARE OR REPLACE VARIABLE gold_province_rule_version STRING DEFAULT 'gold-province-reporting-validation-v2';",
        "WHERE dq.rule_version = gold_province_rule_version",
        "AND province_stop_failures = 0",
        "AND province_population_checks > 0",
        # a later partial gold run cannot hide the full gold validation of the same data
        "WHERE covered_current_facts = 3",
        # each level is rebuilt from its own gold key
        "SELECT 'REGION' AS geography_level, region_key AS geography_key",
        "SELECT 'REPORTING_AREA' AS geography_level, reporting_area_key AS geography_key",
        "IF(area.region_key <=> fact.region_key, 'CONSISTENT', 'CONFLICT')) AS expected_hierarchy_status",
        "FROM `03-gold`.fact_province_reporting_area_population AS population INNER JOIN newest_year",
    ]:
        assert recipe in code, recipe
    for table, name, action in [
        (
            "analytics_investment_distribution",
            "Current projects left out on reporting area key 0",
            "flag",
        ),
        (
            "analytics_infrastructure_network",
            "Region and province hierarchy status follows the two Gold keys",
            "stop",
        ),
        (
            "analytics_infrastructure_network",
            "Projects whose region differs from the parent region of their reporting area",
            "flag",
        ),
        (
            "analytics_integration_coverage",
            "Reporting-area-linked projects equal the Gold projects with a reporting area",
            "stop",
        ),
        (
            "analytics_integration_coverage",
            "Projects whose region and reporting area disagree",
            "flag",
        ),
        (
            "analytics_integration_coverage",
            "Projects not linked to a province reporting area",
            "flag",
        ),
    ]:
        assert check(table, name)["action"] == action, (table, name)
