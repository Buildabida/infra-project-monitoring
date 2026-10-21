import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / "notebooks/05_analytics/01_business_questions.ipynb"
VIEWS_README = ROOT / "notebooks/05_analytics/README.md"
DECISIONS = ROOT / "docs/decisions.md"

# the six capstone insight views (D-56), in insight order, with the grain each comment states
VIEW_GRAINS = {
    "analytics_investment_distribution": (
        "One row per geography level, geography key, and infra_year cohort"
    ),
    "analytics_population_equity": "One row per province reporting area (D-57)",
    "analytics_flood_alignment": "One row per official PSGC region and flood point class",
    "analytics_implementation_monitoring": "One row per current DPWH project",
    "analytics_infrastructure_network": "One row per current DPWH project",
    "analytics_integration_coverage": (
        "One row per integration link, link outcome, and region key"
    ),
}
# the views of the retired d-50, d-51, d-54, and d-55 designs. analytics_population_equity kept its name
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
REGIONAL_VIEWS = [
    "analytics_investment_distribution",
    "analytics_population_equity",
    "analytics_flood_alignment",
]
PROJECT_VIEWS = [
    "analytics_implementation_monitoring",
    "analytics_infrastructure_network",
]
GOLD_TABLES = {
    "dim_date",
    "dim_project",
    "dim_region",
    "dim_project_status",
    "dim_flood_susceptibility",
    "dim_province_reporting_area",
    "dim_province_reporting_area_boundary",
    "fact_province_reporting_area_population",
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


def view_code(name):
    return squash(without_comments(view_sql(name)))


def column_list(name):
    text = view_sql(name)
    start = text.index(f"`05-analytics`.{name} (\n") + len(f"`05-analytics`.{name} (\n")
    return text[start : text.index("\n)\nCOMMENT '", start)]


def columns(name):
    return [line.split()[0] for line in column_list(name).splitlines() if line.strip()]


def view_comment(name):
    return view_sql(name).split("\n)\nCOMMENT '", 1)[1].split("'\nAS\n", 1)[0]


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


def test_03_every_view_section_has_the_required_parts():
    # each view has one markdown cell with its question, grain, rule, and expected result
    cells = notebook(VIEWS)["cells"]
    for name in VIEW_GRAINS:
        index = next(
            i
            for i, cell in enumerate(cells)
            if f"CREATE OR REPLACE VIEW `05-analytics`.{name} ("
            in "".join(cell["source"])
        )
        text = "".join(cells[index - 1]["source"])
        for label in [
            f"`{name}`",
            "**Business question:**",
            "**Grain:**",
            "**Interpretation rule:**",
            "**Expected result:**",
        ]:
            assert label in text, (name, label)


def test_04_first_sql_uses_the_project_catalog():
    first_code = sql(VIEWS).split("%sql\n", 1)[1]
    assert "USE CATALOG `buildabida-capstone`;" in first_code.split("\n%sql")[0]


def test_05_one_current_snapshot_is_asserted_before_any_view_is_built():
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


def test_06_builds_exactly_the_six_views_in_insight_order():
    code = without_comments(sql(VIEWS))
    views = re.findall(r"CREATE OR REPLACE VIEW `05-analytics`\.(\w+) \(", code)
    assert len(VIEW_GRAINS) == 6
    assert views == list(VIEW_GRAINS)
    for name in RETIRED_VIEWS:
        assert f"CREATE OR REPLACE VIEW `05-analytics`.{name} " not in code, name


def test_07_drops_every_retired_view_and_writes_nothing_else():
    code = without_comments(sql(VIEWS))
    drops = re.findall(r"DROP VIEW IF EXISTS `05-analytics`\.(\w+);", code)
    assert drops == RETIRED_VIEWS
    # the drops come before the first view is built
    assert code.index("DROP VIEW IF EXISTS") < code.index("CREATE OR REPLACE VIEW")
    writes = re.findall(
        r"(?:MERGE INTO|INSERT INTO|DELETE FROM|UPDATE|ALTER TABLE|TRUNCATE TABLE"
        r"|CREATE (?:OR REPLACE )?TABLE|DROP TABLE)\b",
        code,
        flags=re.IGNORECASE,
    )
    assert writes == []
    assert "CREATE SCHEMA IF NOT EXISTS `05-analytics`" in code


def test_08_reads_only_gold_and_its_own_views():
    tables = set(re.findall(r"`(\d\d-[a-z]+)`\.(\w+)", without_comments(sql(VIEWS))))
    gold = {table for schema, table in tables if schema == "03-gold"}
    analytics = {table for schema, table in tables if schema == "05-analytics"}
    assert {schema for schema, _ in tables} == {"03-gold", "05-analytics"}
    assert gold == GOLD_TABLES
    assert analytics == set(VIEW_GRAINS) | set(RETIRED_VIEWS)
    # views 2 and 3 take their regions from view 1. no other view reads a view
    for name in VIEW_GRAINS:
        reads = set(re.findall(r"FROM `05-analytics`\.(\w+)", view_code(name)))
        expected = (
            {"analytics_investment_distribution"}
            if name in ("analytics_population_equity", "analytics_flood_alignment")
            else set()
        )
        assert reads == expected, name


def test_09_no_bronze_silver_python_or_spatial_work():
    code = without_comments(sql(VIEWS))
    lowered = code.lower()
    for token in [
        "01-bronze",
        "02-silver",
        "%python",
        "h3_",
        "geometry_json",
        "boundary_geometry",
        "uuid(",
        "rand(",
        "random(",
        "monotonically_increasing_id",
    ]:
        assert token not in lowered, token
    # no geometry function runs in analytics. silver did the spatial work once
    assert not re.search(r"\bst_\w+\(", lowered)


def test_10_every_view_states_its_grain_and_names_its_insight():
    for number, (name, grain) in enumerate(VIEW_GRAINS.items(), start=1):
        comment = view_comment(name)
        assert comment.startswith(f"Insight {number}, "), name
        assert comment.split(". ", 1)[1].startswith(grain), name


def test_11_every_column_has_a_comment_and_a_snapshot_column():
    for name in VIEW_GRAINS:
        lines = [line for line in column_list(name).splitlines() if line.strip()]
        for line in lines:
            assert re.match(r"^\s{4}\w+ COMMENT '.+',?$", line), (name, line)
        assert "source_snapshot_id" in columns(name), name
    assert "mgb_source_snapshot_id" in columns("analytics_flood_alignment")


def test_12_every_project_read_uses_current_rows_only():
    code = squash(without_comments(sql(VIEWS)))
    reads = re.findall(r"FROM `03-gold`\.fact_project_snapshot(?: AS fact)?", code)
    current = re.findall(r"WHERE (?:fact\.)?is_current_snapshot = TRUE", code)
    assert reads
    assert len(reads) == len(current)


def test_13_geographic_views_leave_key_zero_out_and_project_views_keep_it():
    first = view_code("analytics_investment_distribution")
    # each level comes from its own gold key, and key 0 is left out at both
    assert (
        "region_key AS geography_key, project_key, reported_budget_pesos, infra_year FROM current_projects WHERE region_key <> 0"
        in first
    )
    assert (
        "reporting_area_key AS geography_key, project_key, reported_budget_pesos, infra_year FROM current_projects WHERE reporting_area_key <> 0"
        in first
    )
    assert "WHERE region.region_key <> 0" in first
    assert "WHERE area.reporting_area_key <> 0" in first
    assert "AND reporting_area_key <> 0" in view_code("analytics_population_equity")
    assert "AND fact.region_key <> 0" in view_code("analytics_flood_alignment")
    for name in PROJECT_VIEWS + ["analytics_integration_coverage"]:
        code = view_code(name)
        assert "fact.region_key <> 0" not in code, name
        assert "fact.reporting_area_key <> 0" not in code, name
        assert "LEFT JOIN `03-gold`.dim_project AS project" in code, name


def test_14_no_view_writes_placeholder_or_verdict_text():
    code = without_comments(sql(VIEWS))
    assert not re.search(r"'(?:Unknown|Unmapped|UNKNOWN|UNMAPPED)'", code)
    # no value a view writes claims a verdict. comments may say what a value does not mean
    assert not re.search(
        r"THEN '[A-Z_]*(?:OVERDUE|DELAY|STALL|FAIR|ADEQUA|CONNECTED)[A-Z_]*'", code
    )
    # every column name stays free of verdict words too
    for name in VIEW_GRAINS:
        for column in columns(name):
            for word in [
                "overdue",
                "delay",
                "stalled",
                "fair",
                "adequa",
                "connectivity",
            ]:
                assert word not in column, (name, column)


def test_15_province_comes_from_the_governed_gold_key_only():
    code = without_comments(sql(VIEWS))
    # never the raw dpwh location field, and no province name or code is written in analytics
    assert "location" not in code.lower()
    assert not re.search(
        r"(?:reporting_area_name|geography_name|psgc_code|psgc_reporting_area_code)\s*(?:=|IN)\s*\(?'",
        code,
    )
    assert not re.search(r"'\d{10}'", code)
    for name in [
        "analytics_investment_distribution",
        "analytics_implementation_monitoring",
        "analytics_infrastructure_network",
        "analytics_integration_coverage",
    ]:
        assert "fact.reporting_area_key" in view_code(name), name
    for name in PROJECT_VIEWS:
        assert "reporting_area_key" in columns(name), name
    assert "region_province_hierarchy_status" in columns(
        "analytics_infrastructure_network"
    )
    text = markdown(VIEWS)
    assert "DPWH `location.province` never decides it." in text
    assert "Never derive region totals by adding reporting areas." in text


def test_16_infra_year_is_a_cohort_in_the_current_snapshot():
    for name in [
        "analytics_investment_distribution",
        "analytics_implementation_monitoring",
        "analytics_infrastructure_network",
    ]:
        year = [
            line
            for line in column_list(name).splitlines()
            if line.startswith("    infra_year ")
        ]
        assert len(year) == 1, name
        assert "cohort" in year[0], name
    first = view_code("analytics_investment_distribution")
    # no year filter and no placeholder year, so a null year keeps its own row
    assert "infra_year IS NOT NULL" not in first
    assert not re.search(r"\b20[12]\d\b", first)
    assert "WHEN cohort.infra_year IS NULL THEN 'NO_INFRA_YEAR'" in first
    assert (
        "infra_year is a project cohort in the current snapshot, not a historical snapshot"
        in view_comment("analytics_investment_distribution")
    )
    assert 'never "DPWH investment in 2018"' in markdown(VIEWS)


def test_17_investment_distribution_ranks_only_reported_members_within_a_level():
    code = view_code("analytics_investment_distribution")
    for recipe in [
        "WHEN COALESCE(totals.geography_project_count, 0) = 0 THEN 'NO_MAPPED_PROJECT_DATA'",
        "WHEN member.is_barmm THEN 'LIMITED_SOURCE_COVERAGE'",
        "WHEN ranked_cohorts.source_coverage_status = 'REPORTED' THEN ranked_cohorts.cohort_budget_rank_in_status",
        "PARTITION BY geography_level, source_coverage_status ORDER BY geography_budget_pesos DESC NULLS LAST",
        "PARTITION BY geography_level, infra_year, source_coverage_status ORDER BY total_reported_budget_pesos DESC NULLS LAST",
        # a missing budget stays null, never 0
        "totals.geography_budget_pesos,",
        "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW",
        "SUM(total_reported_budget_pesos) OVER (PARTITION BY geography_level, infra_year) AS cohort_budget_pesos",
        "SUM(geography_budget_pesos) OVER (PARTITION BY geography_level) AS level_budget_pesos",
    ]:
        assert recipe in code, recipe
    assert "COALESCE(totals.geography_budget_pesos" not in code
    assert "COALESCE(cohort.total_reported_budget_pesos" not in code
    # every share and rank window is inside one level, so the levels never mix
    for window in re.findall(r"OVER \(([^)]*)\)", code):
        if "PARTITION BY" in window:
            assert "geography_level" in window or "reporting_area_key" in window, window
    assert (
        "geography_level COMMENT 'REGION for an official PSGC region or REPORTING_AREA"
        in column_list("analytics_investment_distribution")
    )


def test_18_population_equity_uses_one_comparable_set_and_no_fairness_flag():
    code = view_code("analytics_population_equity")
    for recipe in [
        "WHEN area.source_coverage_status <> 'REPORTED' THEN 'EXCLUDED_SOURCE_COVERAGE'",
        "WHEN area.geography_budget_pesos IS NULL THEN 'EXCLUDED_NO_REPORTED_BUDGET'",
        "WHEN population.population_count IS NULL THEN 'EXCLUDED_NO_POPULATION'",
        "CASE WHEN equity_comparison_status = 'COMPARABLE' THEN total_reported_budget_pesos END AS comparable_budget_pesos",
        "CASE WHEN equity_comparison_status = 'COMPARABLE' THEN population_count END AS comparable_population",
        "investment_share_pct - comparable_population_share_pct AS share_gap_pp",
        "FROM `03-gold`.fact_province_reporting_area_population WHERE is_primary_source = TRUE AND reporting_area_key <> 0",
        "QUALIFY reference_year = MAX(reference_year) OVER ()",
        "FROM `05-analytics`.analytics_investment_distribution WHERE geography_level = 'REPORTING_AREA'",
    ]:
        assert recipe in code, recipe
    assert "fact_region_population" not in code
    assert "screening indicator, not a verdict on fairness" in markdown(VIEWS)
    # no threshold invents a "substantially different" flag
    assert not [
        column for column in columns("analytics_population_equity") if "flag" in column
    ]


def test_19_flood_alignment_reuses_the_gold_flood_result():
    code = view_code("analytics_flood_alignment")
    assert (
        "WHEN fact.flood_match_status = 'MATCHED' THEN level.flood_susceptibility_level"
        in code
    )
    assert (
        "('AMBIGUOUS'), ('OUTSIDE_MAPPED_ZONES'), ('NO_USABLE_POINT'), ('INVALID_SOURCE')"
        in code
    )
    # areas come from the newest exposure run and fill only level rows
    assert (
        "QUALIFY ROW_NUMBER() OVER (ORDER BY source_load_ts DESC, run_id) = 1" in code
    )
    assert "AND point_class.flood_point_class = exposure.flood_point_class" in code
    # a region with no mapped project keeps null project figures, never 0
    assert (
        "WHEN region.source_coverage_status <> 'NO_MAPPED_PROJECT_DATA' THEN COALESCE(totals.project_count, 0)"
        in code
    )
    assert "COALESCE(totals.total_reported_budget_pesos" not in code
    assert "OUTSIDE_MAPPED_ZONES is not low risk" in column_list(
        "analytics_flood_alignment"
    )


def test_20_shared_rules_are_written_the_same_in_every_view():
    flood = (
        "WHEN fact.flood_match_status = 'UNMATCHED' AND fact.coordinate_status = 'VALID_PAIR' "
        "THEN 'OUTSIDE_MAPPED_ZONES' WHEN fact.flood_match_status = 'UNMATCHED' THEN 'NO_USABLE_POINT' "
        "ELSE fact.flood_match_status END"
    )
    for name in [
        "analytics_flood_alignment",
        "analytics_infrastructure_network",
        "analytics_integration_coverage",
    ]:
        assert flood in view_code(name), name
    status = (
        "CASE WHEN fact.status_key = 0 THEN 'NO_SOURCE_STATUS' WHEN status.status_group IS NULL "
        "THEN 'NO_APPROVED_STATUS_RULE' ELSE 'MAPPED' END AS status_mapping_status"
    )
    for name in PROJECT_VIEWS + ["analytics_integration_coverage"]:
        assert status in view_code(name), name


def test_21_implementation_monitoring_keeps_states_apart_and_builds_no_overdue():
    code = view_code("analytics_implementation_monitoring")
    for recipe in [
        "status.source_status <=> 'For Procurement' AS is_for_procurement",
        "WHEN fact.physical_progress_pct IS NULL THEN 'NOT_PUBLISHED'",
        "WHEN fact.physical_progress_pct = 0 THEN 'ZERO'",
        "status_group = 'ACTIVE' AND NOT is_for_procurement AND zero_progress_flag, FALSE",
        "COALESCE(status_group = 'ACTIVE' AND long_running_flag, FALSE) AS review_active_long_running",
        "status_group = 'ACTIVE' AND NOT is_for_procurement AND physical_progress_pct IS NULL, FALSE",
        "COALESCE(status_group = 'INACTIVE', FALSE) AS review_inactive_status",
        "status_group IS NULL AS review_unresolved_status",
    ]:
        assert recipe in code, recipe
    names = columns("analytics_implementation_monitoring")
    for column in [
        "zero_progress_flag",
        "long_running_flag",
        "physical_progress_pct",
        "needs_review",
    ]:
        assert column in names, column
    # the long-running rule is gold's. no view sets its own threshold or reads today's date
    lowered = code.lower()
    for token in ["months_between", "current_date", "now()", "datediff"]:
        assert token not in lowered, token
    assert "**Overdue is not built.**" in markdown(VIEWS)


def test_22_infrastructure_network_is_lightweight_and_claims_no_connectivity():
    code = view_code("analytics_infrastructure_network")
    assert "fact.coordinate_status <=> 'VALID_PAIR' AS is_mappable" in code
    assert (
        "CASE WHEN fact.coordinate_status <=> 'VALID_PAIR' THEN FLOOR(fact.latitude * 10) / 10 END AS map_grid_latitude"
        in code
    )
    lowered = code.lower()
    assert "cross join `03-gold`.fact_project_snapshot" not in lowered
    assert not re.search(r"\bst_\w+\(", lowered)
    # one fact read, joined to its dimensions once
    assert code.count("FROM `03-gold`.fact_project_snapshot") == 2
    assert "It cannot show network connectivity" in view_comment(
        "analytics_infrastructure_network"
    )


def test_23_integration_coverage_has_every_documented_link_once():
    code = view_code("analytics_integration_coverage")
    links = re.findall(r"'integration_link', '(\w+)'", code)
    assert links == [
        "PSGC_REGION",
        "PSGC_REPORTING_AREA",
        "REGION_PROVINCE_HIERARCHY",
        "COORDINATES",
        "POPULATION_VIA_REGION",
        "POPULATION_VIA_REPORTING_AREA",
        "FLOOD_SUSCEPTIBILITY",
        "PROJECT_CATEGORY",
        "PROJECT_STATUS",
        "REPORTED_BUDGET",
        "OFFICIAL_FLOOD_LIST",
    ]
    for link in links:
        assert f"WHEN '{link}' THEN '" in code, link
    # a missing budget is summed as null, never as 0
    assert "SUM(reported_budget_pesos) AS reported_budget_pesos" in code
    assert "COALESCE(projects.reported_budget_pesos" not in code
    assert "LEFT JOIN `03-gold`.dim_region AS region" in code


def test_24_budget_is_never_coalesced_to_zero():
    for name in VIEW_GRAINS:
        code = view_code(name)
        assert not re.search(r"COALESCE\([\w.]*reported_budget_pesos, 0\)", code), name
        assert not re.search(r"COALESCE\([\w.]*budget_pesos, 0\)", code), name


def test_25_docs_describe_the_six_views():
    readme = VIEWS_README.read_text(encoding="utf-8")
    for name in VIEW_GRAINS:
        assert f"`{name}`" in readme, name
    assert readme.index("09_validation_gold") < readme.index("01_business_questions")
    assert "02_regional_project_progress" not in readme
    decisions = DECISIONS.read_text(encoding="utf-8")
    assert "| D-56 |" in decisions
    # the team approved d-56, so it is recorded as made and no longer proposed
    made = decisions.split("## Made", 1)[1].split("## Resolved questions", 1)[0]
    assert "| D-56 |" in made
    proposed = decisions.split("## Proposed decisions", 1)[1]
    assert "| D-56 |" not in proposed.split("## Withdrawn", 1)[0]
    # d-55 is withdrawn, not silently deleted
    assert "| D-55 |" in decisions.split("## Withdrawn proposals", 1)[1]
