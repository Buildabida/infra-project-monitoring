import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / "notebooks/05_analytics/01_business_questions.ipynb"
VIEWS_README = ROOT / "notebooks/05_analytics/README.md"
DECISIONS = ROOT / "docs/decisions.md"

# the six official business-question views (D-50, D-51)
OFFICIAL_VIEWS = {
    "analytics_regional_investment": "One row per official PSGC region",
    "analytics_category_portfolio": "One row per DPWH sector and mapping status",
    "analytics_project_delivery_status": "One row per region, category, and status group",
    "analytics_population_equity": "One row per official region",
    "analytics_flood_control_exposure": "One row per official region",
    "analytics_region_category": "One row per official region, DPWH sector, and mapping status",
}
# the exploratory monitoring views (D-54)
EXPLORATORY_VIEWS = {
    "analytics_infrastructure_year_trend": "One row per infrastructure year, including NULL",
    "analytics_infrastructure_year_sector": (
        "One row per infrastructure year, DPWH sector, and mapping status"
    ),
    "analytics_delivery_cohort": (
        "One row per infrastructure year, status group, and status mapping status"
    ),
    "analytics_project_size_concentration": "One row per official PSGC region",
    "analytics_implementing_office_portfolio": (
        "One row per implementing office, including NULL"
    ),
}
VIEW_GRAINS = {**OFFICIAL_VIEWS, **EXPLORATORY_VIEWS}
REPORTING_AREA_VIEWS = (
    "analytics_reporting_area_investment",
    "analytics_reporting_area_category",
    "analytics_reporting_area_delivery_status",
    "analytics_reporting_area_population_equity",
    "analytics_reporting_area_project_size_concentration",
)
REGIONAL_VIEWS = [
    "analytics_regional_investment",
    "analytics_project_delivery_status",
    "analytics_population_equity",
    "analytics_flood_control_exposure",
    "analytics_region_category",
    "analytics_project_size_concentration",
]
COHORT_VIEWS = [
    "analytics_infrastructure_year_trend",
    "analytics_infrastructure_year_sector",
    "analytics_delivery_cohort",
]
# sha-256 of each official view cell on main when the exploratory views were added.
# a change here needs a documented bug fix or decision, never a quiet edit
OFFICIAL_VIEW_SHA256 = {
    "analytics_regional_investment": "1e848a8a6d7c3def5f4f64606b4f0f6c08d261b51baf05a9be8b0dc2ea93d740",
    "analytics_category_portfolio": "20700c02adc8460ae3148d7ce88e1d475211161eac6c82077ab6e95767e7be11",
    "analytics_project_delivery_status": "e8ade126c1df8701be8be8ed2de2c6d1684fd5c92a5db87ba0855eadee3e2c24",
    "analytics_population_equity": "a5a0c25ddd0c5a65257eab76c7e0b1fc21faa999357632823bf022950a083f65",
    "analytics_flood_control_exposure": "929f538c7fa8b4ac70156f94c6b8f7403e114b44bad908a26057a970865f7964",
    "analytics_region_category": "0f7a6ce961f24bc1d95922e23a19ea58673bb1d5b009d3113fa89faebef713cb",
}
GOLD_TABLES = {
    "dim_project",
    "dim_region",
    "dim_project_status",
    "dim_flood_susceptibility",
    "fact_project_snapshot",
    "fact_region_population",
    "fact_region_flood_exposure",
    "dim_province_reporting_area",
    "fact_province_reporting_area_population",
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


def test_05_builds_reporting_area_official_and_exploratory_views_only():
    code = without_comments(sql(VIEWS))
    views = re.findall(r"CREATE OR REPLACE VIEW `05-analytics`\.(\w+) \(", code)
    # D-55 reporting areas are built first, followed by the retained view groups.
    assert len(OFFICIAL_VIEWS) == 6
    assert len(EXPLORATORY_VIEWS) == 5
    assert not set(OFFICIAL_VIEWS) & set(EXPLORATORY_VIEWS)
    assert views == (
        list(REPORTING_AREA_VIEWS) + list(OFFICIAL_VIEWS) + list(EXPLORATORY_VIEWS)
    )
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
    assert analytics == set(VIEW_GRAINS) | set(REPORTING_AREA_VIEWS)


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
    for decision in ["| D-50 |", "| D-51 |", "| D-54 |"]:
        assert decision in decisions, decision
    # the team approved d-54, so it is a made decision with its approval recorded
    made = decisions.split("## Made", 1)[1].split("## Resolved questions", 1)[0]
    d54 = [line for line in made.splitlines() if line.startswith("| D-54 |")]
    assert len(d54) == 1
    assert d54[0].startswith("| D-54 | Oct 13 |")
    assert "The team agreed in the group chat." in d54[0]
    if "## Proposed decisions awaiting team approval" in decisions:
        proposed = decisions.split("## Proposed decisions awaiting team approval", 1)[1]
        assert "| D-54 |" not in proposed


def exploratory_code(name):
    return squash(without_comments(view_sql(name)))


def test_17_official_q1_to_q6_views_are_unchanged():
    # the exploratory work adds views and never edits the six official ones
    for name, digest in OFFICIAL_VIEW_SHA256.items():
        assert hashlib.sha256(view_sql(name).encode("utf-8")).hexdigest() == digest, (
            name
        )


def test_18_exploratory_views_are_labeled_and_cite_their_decision():
    for name in EXPLORATORY_VIEWS:
        comment = view_sql(name).split("\n)\nCOMMENT '", 1)[1]
        assert comment.startswith("Exploratory "), name
        assert "(D-54)" in comment.split(". ", 1)[0], name
    header = cell_sources(VIEWS, "markdown")[0]
    assert "6 official business-question views" in header
    assert "5 exploratory monitoring views" in header


def test_19_infra_year_is_a_cohort_in_the_current_snapshot():
    for name in COHORT_VIEWS:
        comment = view_sql(name).split("\n)\nCOMMENT '", 1)[1]
        assert "infra_year is a project cohort in the current snapshot" in comment, name
        assert "not a historical snapshot of the DPWH portfolio" in comment, name
        year = [
            line
            for line in column_list(name).splitlines()
            if line.startswith("    infra_year ")
        ]
        assert len(year) == 1, name
        assert (
            "A project cohort in the current snapshot, not a past state" in year[0]
        ), name
    assert "How did DPWH perform in 2016?" not in markdown(VIEWS).replace(
        'They cannot answer "how did DPWH perform in 2016?"', ""
    )


def test_20_null_infra_year_keeps_its_own_row():
    for name in COHORT_VIEWS:
        code = exploratory_code(name)
        # no year filter, no placeholder year, and a left join so no project drops out
        assert "infra_year IS NOT NULL" not in code, name
        assert not re.search(r"infra_year (?:BETWEEN|>|<|>=|<=|IN) ", code), name
        assert "COALESCE(project.infra_year" not in code, name
        assert not re.search(r"\b20[12]\d\b", code), name
        assert "LEFT JOIN `03-gold`.dim_project AS project" in code, name
        assert "project.infra_year," in code, name


def test_21_year_sector_share_divides_by_the_same_year():
    code = exploratory_code("analytics_infrastructure_year_sector")
    assert (
        "ROUND( 100.0 * total_reported_budget_pesos / NULLIF(SUM(total_reported_budget_pesos) "
        "OVER (PARTITION BY infra_year), 0), 4 ) AS share_of_year_budget_pct"
    ) in code
    # no share of a sector across years until a denominator is approved
    columns = [
        line.split()[0]
        for line in column_list("analytics_infrastructure_year_sector").splitlines()
    ]
    assert "share_of_sector_budget_pct" not in columns
    # the strict flood sector, so is_dpwh_flood_related is not read here
    assert "is_dpwh_flood_related" not in code


def test_22_long_running_rate_uses_the_q3_evaluated_denominator():
    q3 = exploratory_code("analytics_project_delivery_status")
    rules = [
        "COUNT(fact.long_running_flag) AS long_running_evaluated_count",
        "COUNT_IF(fact.long_running_flag = TRUE) AS long_running_count",
        "ROUND(100.0 * long_running_count / NULLIF(long_running_evaluated_count, 0), 2) AS pct_long_running",
    ]
    for rule in rules:
        assert rule in q3, rule
    for name in [
        "analytics_infrastructure_year_trend",
        "analytics_delivery_cohort",
        "analytics_implementing_office_portfolio",
    ]:
        code = exploratory_code(name)
        for rule in rules:
            assert rule in code, (name, rule)
        assert "Long-running does not mean delayed." in view_sql(name), name


def test_23_zero_progress_rate_uses_the_q3_denominator_and_discloses_for_procurement():
    rules = [
        "COUNT(fact.zero_progress_flag) AS zero_progress_evaluated_count",
        "COUNT_IF(fact.zero_progress_flag = TRUE) AS zero_progress_count",
        "ROUND(100.0 * zero_progress_count / NULLIF(zero_progress_evaluated_count, 0), 2) AS pct_zero_progress",
    ]
    for name in [
        "analytics_infrastructure_year_trend",
        "analytics_delivery_cohort",
        "analytics_implementing_office_portfolio",
    ]:
        code = exploratory_code(name)
        for rule in rules:
            assert rule in code, (name, rule)
        rate = [
            line
            for line in column_list(name).splitlines()
            if line.startswith("    pct_zero_progress ")
        ]
        assert (
            "so it includes For Procurement projects (D-46). Not a stalled rate."
            in rate[0]
        ), name
    # the two cohort views also count for procurement projects, from the source status
    for name in ["analytics_infrastructure_year_trend", "analytics_delivery_cohort"]:
        code = exploratory_code(name)
        assert (
            "COUNT(DISTINCT CASE WHEN status.source_status = 'For Procurement' THEN fact.project_key END) "
            "AS for_procurement_count"
        ) in code, name
        assert "for_procurement_count COMMENT" in column_list(name), name
    for name in EXPLORATORY_VIEWS:
        assert "stalled_flag" not in view_sql(name), name


def test_24_trend_status_counts_use_the_approved_groups():
    code = exploratory_code("analytics_infrastructure_year_trend")
    for group, column in [
        ("FINISHED", "finished_count"),
        ("ACTIVE", "active_count"),
        ("INACTIVE", "inactive_count"),
    ]:
        assert (
            f"COUNT(DISTINCT CASE WHEN status.status_group = '{group}' THEN fact.project_key END) AS {column}"
        ) in code
    assert (
        "COUNT(DISTINCT CASE WHEN status.status_group IS NULL THEN fact.project_key END) AS unmapped_status_count"
    ) in code
    for name in EXPLORATORY_VIEWS:
        assert not re.search(
            r"'(?:Completed|Ongoing|Delayed)'", without_comments(view_sql(name))
        ), name
    # the cohort view gives an unresolved status the q3 reason
    q3_reason = (
        "CASE WHEN fact.status_key = 0 THEN 'NO_SOURCE_STATUS' WHEN status.status_group IS NULL "
        "THEN 'NO_APPROVED_STATUS_RULE' ELSE 'MAPPED' END AS status_mapping_status"
    )
    assert q3_reason in exploratory_code("analytics_project_delivery_status")
    assert q3_reason in exploratory_code("analytics_delivery_cohort")
    assert (
        "ROUND( 100.0 * project_count / NULLIF(SUM(project_count) OVER (PARTITION BY infra_year), 0), 2 ) "
        "AS pct_of_year_projects"
    ) in exploratory_code("analytics_delivery_cohort")


def test_25_size_view_leaves_region_key_zero_out_and_takes_regions_from_q1():
    code = exploratory_code("analytics_project_size_concentration")
    assert "WHERE is_current_snapshot = TRUE AND region_key <> 0" in code
    assert "FROM `05-analytics`.analytics_regional_investment AS region" in code
    for column in [
        "source_coverage_status",
        "project_count",
        "total_reported_budget_pesos",
    ]:
        assert f"region.{column}," in code, column
    # no budget bands: no threshold literal compares a budget
    assert not re.search(r"reported_budget_pesos\s*(?:<|>|BETWEEN)", code)


def test_26_median_and_p90_use_only_known_reported_budgets():
    for name, cuts in [
        ("analytics_project_size_concentration", ["0.5", "0.9"]),
        ("analytics_implementing_office_portfolio", ["0.5"]),
    ]:
        code = exploratory_code(name)
        for cut in cuts:
            assert f"PERCENTILE_CONT({cut}) WITHIN GROUP (ORDER BY " in code, (
                name,
                cut,
            )
        # an aggregate skips null budgets, so nothing may turn a null into 0 first
        assert "COALESCE(fact.reported_budget_pesos" not in code, name
        assert "COALESCE(reported_budget_pesos" not in code, name
        lowered = code.lower()
        for approximate in [
            "percentile_approx",
            "approx_percentile",
            "approx_count_distinct",
        ]:
            assert approximate not in lowered, (name, approximate)
    size = exploratory_code("analytics_project_size_concentration")
    assert "COUNT_IF(reported_budget_pesos = 0) AS projects_with_zero_budget" in size


def test_27_null_implementing_office_stays_visible_with_no_rank():
    code = exploratory_code("analytics_implementing_office_portfolio")
    assert (
        "implementing_office IS NOT NULL THEN project_count_rank_in_group END AS project_count_rank"
        in code
    )
    assert (
        "implementing_office IS NOT NULL THEN budget_rank_in_group END AS budget_rank"
        in code
    )
    assert "WHERE project.implementing_office IS NOT NULL" not in code
    assert "COALESCE(project.implementing_office" not in code
    assert "LEFT JOIN `03-gold`.dim_project AS project" in code
    # ties share a rank
    assert (
        "RANK() OVER ( PARTITION BY implementing_office IS NULL ORDER BY project_count DESC )"
        in code
    )
    assert not re.search(
        r"'(?:Missing|Conflict|No office)'",
        without_comments(view_sql("analytics_implementing_office_portfolio")),
    )


def test_28_every_exploratory_view_publishes_the_current_snapshot():
    snapshot = (
        "current_snapshot AS ( SELECT MAX(source_snapshot_id) AS source_snapshot_id "
        "FROM `03-gold`.fact_project_snapshot WHERE is_current_snapshot = TRUE )"
    )
    for name in EXPLORATORY_VIEWS:
        code = exploratory_code(name)
        if name == "analytics_project_size_concentration":
            # its snapshot comes from q1, which reads the same current snapshot
            assert (
                "region.source_snapshot_id FROM `05-analytics`.analytics_regional_investment"
                in code
            )
            continue
        assert snapshot in code, name
        assert "current_snapshot.source_snapshot_id" in code, name
