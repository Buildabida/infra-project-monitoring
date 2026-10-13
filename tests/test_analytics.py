import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / "notebooks/05_analytics/01_business_questions.ipynb"
VIEWS_README = ROOT / "notebooks/05_analytics/README.md"
DECISIONS = ROOT / "docs/decisions.md"

VIEW_GRAINS = {
    "analytics_regional_investment": "One row per official PSGC region",
    "analytics_category_portfolio": "One row per DPWH sector and mapping status",
    "analytics_project_delivery_status": "One row per region, category, and status group",
    "analytics_population_equity": "One row per official region",
    "analytics_flood_control_exposure": "One row per official region",
    "analytics_region_category": "One row per official region, DPWH sector, and mapping status",
}
REGIONAL_VIEWS = [
    "analytics_regional_investment",
    "analytics_project_delivery_status",
    "analytics_population_equity",
    "analytics_flood_control_exposure",
    "analytics_region_category",
]
GOLD_TABLES = {
    "dim_project",
    "dim_region",
    "dim_project_status",
    "dim_flood_susceptibility",
    "fact_project_snapshot",
    "fact_region_population",
    "fact_region_flood_exposure",
}


def notebook(path):
    return json.loads(path.read_text(encoding="utf-8"))


def cell_sources(path, cell_type):
    return [
        "".join(cell.get("source", []))
        for cell in notebook(path)["cells"]
        if cell["cell_type"] == cell_type
    ]


def sql(path):
    return "\n".join(cell_sources(path, "code"))


def markdown(path):
    return "\n".join(cell_sources(path, "markdown"))


def without_comments(text):
    return "\n".join(line.split("--", 1)[0] for line in text.splitlines())


def squash(text):
    return " ".join(text.split())


def view_sql(name):
    own = [
        cell
        for cell in cell_sources(VIEWS, "code")
        if f"CREATE OR REPLACE VIEW `05-analytics`.{name} (" in cell
    ]
    assert len(own) == 1, name
    return own[0]


def column_list(name):
    text = view_sql(name)
    start = text.index(f"`05-analytics`.{name} (\n") + len(f"`05-analytics`.{name} (\n")
    return text[start : text.index("\n)\nCOMMENT '", start)]


def test_01_notebook_is_a_valid_nbformat_sql_notebook():
    nb = notebook(VIEWS)
    assert nb["nbformat"] == 4
    assert nb["nbformat_minor"] >= 5
    meta = nb["metadata"]["application/vnd.databricks.v1+notebook"]
    assert meta["language"] == "sql"
    assert meta["notebookName"] == VIEWS.stem
    ids = [cell["id"] for cell in nb["cells"]]
    assert len(ids) == len(set(ids))
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            assert "".join(cell["source"]).startswith("%sql\n")
            assert cell["outputs"] == []


def test_02_every_code_cell_has_markdown_before_it():
    cells = notebook(VIEWS)["cells"]
    assert cells[0]["cell_type"] == "markdown"
    for index, cell in enumerate(cells):
        if cell["cell_type"] == "code":
            assert cells[index - 1]["cell_type"] == "markdown", index
    text = markdown(VIEWS)
    for label in ["**What:**", "**Why:**", "**Expected result:**"]:
        assert label in text


def test_03_first_sql_uses_the_project_catalog():
    first_code = sql(VIEWS).split("%sql\n", 1)[1]
    assert "USE CATALOG `buildabida-capstone`;" in first_code.split("\n%sql")[0]


def test_04_one_current_snapshot_is_asserted_before_any_view_is_built():
    code = sql(VIEWS)
    gate = code.index("SELECT ASSERT_TRUE(")
    assert gate < code.index("CREATE SCHEMA IF NOT EXISTS `05-analytics`")
    assert gate < code.index("CREATE OR REPLACE VIEW")
    assert (
        "COUNT(DISTINCT source_snapshot_id) = 1 AND COUNT_IF(source_snapshot_id IS NULL) = 0, "
        "'STOP: current Gold project rows span multiple DPWH snapshots. "
        "Rebuild Gold before analytics.' ) FROM `03-gold`.fact_project_snapshot "
        "WHERE is_current_snapshot = TRUE;"
    ) in squash(code)


def test_05_builds_exactly_the_six_views_and_nothing_else():
    code = without_comments(sql(VIEWS))
    views = re.findall(r"CREATE OR REPLACE VIEW `05-analytics`\.(\w+) \(", code)
    assert views == list(VIEW_GRAINS)
    writes = re.findall(
        r"(?:MERGE INTO|INSERT INTO|DELETE FROM|UPDATE|ALTER TABLE|DROP \w+|TRUNCATE TABLE"
        r"|CREATE (?:OR REPLACE )?TABLE)\b",
        code,
        flags=re.IGNORECASE,
    )
    assert writes == []
    assert "CREATE SCHEMA IF NOT EXISTS `05-analytics`" in code


def test_06_reads_only_gold_and_its_own_views():
    tables = set(re.findall(r"`(\d\d-[a-z]+)`\.(\w+)", without_comments(sql(VIEWS))))
    gold = {table for schema, table in tables if schema == "03-gold"}
    analytics = {table for schema, table in tables if schema == "05-analytics"}
    assert {schema for schema, _ in tables} == {"03-gold", "05-analytics"}
    assert gold == GOLD_TABLES
    assert analytics == set(VIEW_GRAINS)


def test_07_every_view_states_its_grain():
    for name, grain in VIEW_GRAINS.items():
        comment = view_sql(name).split("\n)\nCOMMENT '", 1)[1]
        assert comment.split(". ", 1)[1].startswith(grain), name


def test_08_every_column_has_a_comment_and_a_snapshot_column():
    for name in VIEW_GRAINS:
        lines = [line for line in column_list(name).splitlines() if line.strip()]
        for line in lines:
            assert re.match(r"^\s{4}\w+ COMMENT '.+',?$", line), (name, line)
        columns = [line.split()[0] for line in lines]
        assert "source_snapshot_id" in columns, name
    assert "mgb_source_snapshot_id" in column_list("analytics_flood_control_exposure")


def test_09_every_project_read_uses_current_rows_only():
    code = squash(without_comments(sql(VIEWS)))
    reads = re.findall(r"FROM `03-gold`\.fact_project_snapshot(?: AS fact)?", code)
    current = re.findall(r"WHERE (?:fact\.)?is_current_snapshot = TRUE", code)
    assert reads
    assert len(reads) == len(current)


def test_10_regional_views_leave_region_key_zero_out():
    for name in REGIONAL_VIEWS:
        code = squash(without_comments(view_sql(name)))
        if name in {"analytics_population_equity"}:
            # population is filtered, and regions come from q1
            assert "AND region_key <> 0" in code
            assert "FROM `05-analytics`.analytics_regional_investment AS region" in code
            continue
        assert re.search(r"(?:fact\.)?region_key <> 0", code), name
    q1 = squash(without_comments(view_sql("analytics_regional_investment")))
    assert "WHERE region.region_key <> 0" in q1
    # q3 to q6 take their regions and coverage status from q1
    for name in REGIONAL_VIEWS[1:]:
        assert (
            "FROM `05-analytics`.analytics_regional_investment AS region"
            in view_sql(name)
        )
    # q2 is national, so it keeps key 0 projects
    assert "region_key" not in without_comments(
        view_sql("analytics_category_portfolio")
    )


def test_11_q2_has_a_strict_and_a_broad_flood_share():
    code = squash(without_comments(view_sql("analytics_category_portfolio")))
    assert (
        "100.0 * SUM(CASE WHEN is_dpwh_flood_related THEN total_reported_budget_pesos "
        "ELSE 0 END) OVER () / NULLIF(SUM(total_reported_budget_pesos) OVER (), 0), 4 ) "
        "AS flood_control_share_of_portfolio_pct"
    ) in code
    assert (
        "CASE WHEN standardized_sector = 'Flood Control and Drainage' THEN "
        "total_reported_budget_pesos ELSE 0 END ) OVER () / "
        "NULLIF(SUM(total_reported_budget_pesos) OVER (), 0), 4 ) "
        "AS flood_control_single_sector_share_pct"
    ) in code
    # every current project stays in the portfolio, even with no dimension row (D-36)
    assert "LEFT JOIN `03-gold`.dim_project AS project" in code


def test_12_q4_shares_use_one_comparable_set_of_regions():
    code = squash(without_comments(view_sql("analytics_population_equity")))
    comparable = (
        "WHEN region.source_coverage_status = 'REPORTED' AND "
        "region.total_reported_budget_pesos IS NOT NULL AND "
        "population.population_count IS NOT NULL THEN {value} END AS {name}"
    )
    assert (
        comparable.format(
            value="region.total_reported_budget_pesos", name="comparable_budget_pesos"
        )
        in code
    )
    assert (
        comparable.format(
            value="population.population_count", name="comparable_population"
        )
        in code
    )
    for recipe in [
        (
            "100.0 * comparable_budget_pesos / NULLIF(SUM(comparable_budget_pesos) OVER (), 0), 4 ) "
            "AS investment_share_pct"
        ),
        (
            "100.0 * comparable_population / NULLIF(SUM(comparable_population) OVER (), 0), 4 ) "
            "AS comparable_population_share_pct"
        ),
        "investment_share_pct - comparable_population_share_pct AS equity_gap_pp",
        (
            "ROUND(comparable_budget_pesos / NULLIF(comparable_population, 0), 2) "
            "AS investment_per_capita_pesos"
        ),
        # only the newest primary census year, so two years never add up
        "QUALIFY reference_year = MAX(reference_year) OVER ()",
    ]:
        assert recipe in code, recipe


def test_13_q5_adds_level_areas_only_when_they_do_not_overlap():
    code = squash(without_comments(view_sql("analytics_flood_control_exposure")))
    for recipe in [
        (
            "WHEN COUNT_IF(exposure.level_area_additivity_status = 'NOT_EVALUATED') > 0 "
            "THEN 'NOT_EVALUATED'"
        ),
        (
            "WHEN COUNT_IF(NOT exposure.level_area_additivity_status <=> "
            "'ADDITIVE_WITHIN_TOLERANCE') > 0 THEN 'NON_ADDITIVE_CROSS_LEVEL_OVERLAP'"
        ),
        (
            "WHEN exposure.exposure_area_status = 'ADDITIVE_WITHIN_TOLERANCE' THEN "
            "exposure.summed_level_area_sqkm END AS total_susceptible_area_sqkm"
        ),
        "NULLIF(total_susceptible_area_sqkm, 0)",
        # the newest exposure run only, so older mgb snapshots never add up
        "QUALIFY ROW_NUMBER() OVER (ORDER BY source_load_ts DESC, run_id) = 1",
    ]:
        assert recipe in code, recipe


def test_14_no_view_writes_placeholder_text():
    code = without_comments(sql(VIEWS))
    assert not re.search(r"'(?:Unknown|Unmapped|UNKNOWN|UNMAPPED)'", code)


def test_15_no_random_values_or_python():
    code = without_comments(sql(VIEWS)).lower()
    for token in [
        "uuid(",
        "rand(",
        "random(",
        "monotonically_increasing_id",
        "%python",
    ]:
        assert token not in code, token


def test_16_docs_describe_the_views():
    readme = VIEWS_README.read_text(encoding="utf-8")
    for name in VIEW_GRAINS:
        assert f"`{name}`" in readme, name
    assert readme.index("09_validation_gold") < readme.index("01_business_questions")
    decisions = DECISIONS.read_text(encoding="utf-8")
    for decision in ["| D-50 |", "| D-51 |"]:
        assert decision in decisions, decision
