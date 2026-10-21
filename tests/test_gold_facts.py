import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "notebooks/03_gold"
GOLD_MODEL = ROOT / "docs/model/gold_model.md"
DECISIONS = ROOT / "docs/decisions.md"

NOTEBOOK_TABLES = {
    "05_gold_fact_region_population": "fact_region_population",
    "06_gold_fact_region_flood_exposure": "fact_region_flood_exposure",
    "07_gold_fact_project_snapshot": "fact_project_snapshot",
}
NOTEBOOKS = [GOLD / f"{name}.ipynb" for name in NOTEBOOK_TABLES]
PROJECT = GOLD / "07_gold_fact_project_snapshot.ipynb"


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


def squashed(path):
    """Return the code without comments, with every run of whitespace as one space."""
    return " ".join(code_without_comments(path).split())


def stop_check(text, message):
    """Return one squashed ASSERT_TRUE statement, from its start to its STOP message."""
    end = text.index(f"'{message}'")
    return text[text.rindex("SELECT ASSERT_TRUE(", 0, end) : end]


def ddl_columns(text, table):
    start = text.index(f"CREATE TABLE IF NOT EXISTS `03-gold`.{table} (\n")
    body = text[start:].split("\n", 1)[1].split("\n)\nUSING DELTA", 1)[0]
    columns = []
    for line in body.splitlines():
        match = re.match(r"^    (\w+) (\S+)(?: NOT NULL)? COMMENT '[^']+',?$", line)
        assert match, f"{table}: column line has no comment or bad shape: {line}"
        columns.append((match.group(1), match.group(2)))
    return columns


def model_columns(table):
    text = GOLD_MODEL.read_text(encoding="utf-8")
    section = text.split(f"#### `{table}`\n", 1)[1].split("\n#", 1)[0]
    rows = re.findall(
        r"^\| (?:PK|FK|None) \| `(\w+)` \| ([^|]+?) \|$", section, re.MULTILINE
    )
    assert rows, table
    return rows


def test_01_notebooks_are_valid_nbformat_sql_notebooks():
    for path in NOTEBOOKS:
        nb = notebook(path)
        assert nb["nbformat"] == 4
        meta = nb["metadata"]
        assert "kernelspec" not in meta, path.stem
        assert meta["language_info"] == {"name": "sql"}, path.stem
        assert meta["application/vnd.databricks.v1+notebook"]["language"] == "sql"
        assert (
            meta["application/vnd.databricks.v1+notebook"]["notebookName"] == path.stem
        )
        cells = nb["cells"]
        assert cells[0]["cell_type"] == "markdown"
        for index, cell in enumerate(cells):
            if cell["cell_type"] == "code":
                assert "".join(cell["source"]).startswith("%sql\n")
                assert cell["outputs"] == []
                assert cells[index - 1]["cell_type"] == "markdown"


def test_02_first_sql_uses_the_project_catalog_and_sections_exist():
    for path in NOTEBOOKS:
        assert (
            sql(path)
            .split("%sql\n", 1)[1]
            .startswith("USE CATALOG `buildabida-capstone`;")
        )
        for heading in ["## Purpose", "## Grain", "# Summary"]:
            assert heading in markdown(path), (path.stem, heading)


def test_03_tables_match_gold_model_names_types_and_order():
    for name, table in NOTEBOOK_TABLES.items():
        assert ddl_columns(sql(GOLD / f"{name}.ipynb"), table) == model_columns(table)


def test_04_tables_are_created_once_and_loaded_with_merge():
    for name, table in NOTEBOOK_TABLES.items():
        text = sql(GOLD / f"{name}.ipynb")
        upper = text.upper()
        assert text.count(f"CREATE TABLE IF NOT EXISTS `03-gold`.{table} (") == 1
        assert text.count(f"MERGE INTO `03-gold`.{table} AS target") == 1
        for token in [
            "DROP TABLE",
            "TRUNCATE",
            "CREATE OR REPLACE TABLE",
            "DELETE FROM",
        ]:
            assert token not in upper, (name, token)


def test_05_keys_are_deterministic_hashes_with_a_label():
    # the full d-33 recipe of every key, so dropping any part of it fails (#121)
    recipes = {
        "05_gold_fact_region_population": (
            "XXHASH64(CONCAT_WS( '|', 'REGION_POPULATION', CAST(region_key AS STRING), "
            "CAST(reference_year AS STRING), source_name )) AS region_population_fact_key"
        ),
        "06_gold_fact_region_flood_exposure": (
            "XXHASH64(CONCAT_WS( '|', 'REGION_FLOOD_EXPOSURE', CAST(region_key AS STRING), "
            "CAST(flood_susceptibility_key AS STRING), mgb_source_snapshot_id, "
            "boundary_version )) AS region_flood_exposure_key"
        ),
        "07_gold_fact_project_snapshot": (
            "XXHASH64(CONCAT_WS( '|', 'PROJECT_SNAPSHOT', CAST(project_key AS STRING), "
            "source_snapshot_id )) AS project_snapshot_key"
        ),
    }
    for name, recipe in recipes.items():
        assert squashed(GOLD / f"{name}.ipynb").count(recipe) == 1, name


def test_06_no_random_current_time_backslash_or_spatial_work():
    for path in NOTEBOOKS:
        code = code_without_comments(path)
        lower = code.lower()
        for token in [
            "uuid(",
            "rand(",
            "random(",
            "monotonically_increasing_id",
            "current_timestamp",
            "current_date",
            "now()",
        ]:
            assert token not in lower, (path.stem, token)
        upper = code.upper()
        assert not re.search(r"\bST_[A-Z]+\(", upper), path.stem
        assert "TRY_TO_GEOMETRY" not in upper, path.stem
        # the vs code %sql magic turns \\ into \ before spark parses the statement
        assert "\\\\" not in sql(path), path.stem


def test_07_facts_read_silver_measures_unchanged():
    population = code_without_comments(GOLD / "05_gold_fact_region_population.ipynb")
    assert "FROM `02-silver`.silver_region_population AS population" in population
    assert "population.population_count," in population
    exposure = code_without_comments(GOLD / "06_gold_fact_region_flood_exposure.ipynb")
    assert "FROM `02-silver`.silver_region_flood_exposure AS exposure" in exposure
    for column in ["susceptible_area_sqkm", "share_of_region_area_pct"]:
        assert f"exposure.{column}," in exposure
    assert "COALESCE(exposure.susceptible_area_sqkm" not in exposure


def test_08_region_and_flood_keys_only_for_clean_matches():
    text = code_without_comments(PROJECT)
    assert (
        "region_key_match_statuses ARRAY<STRING> "
        "DEFAULT ARRAY('MATCHED', 'MATCHED_WITH_CONFLICT');" in text
    )
    assert (
        "WHEN ARRAY_CONTAINS(region_key_match_statuses, "
        "project_rows.region_match_status)" in text
    )
    assert "flood_key_match_status STRING DEFAULT 'MATCHED';" in text
    assert "WHEN project_rows.flood_match_status = flood_key_match_status THEN" in text
    assert "COALESCE(status.status_key, 0) AS status_key" in text
    assert "FROM `02-silver`.silver_project_region_map" in text
    assert "FROM `02-silver`.silver_project_flood_map" in text
    # gold never redoes region or flood matching
    assert "silver_psgc_place" not in text
    assert "flood_susceptibility`" not in text.replace(
        "`03-gold`.dim_flood_susceptibility", ""
    )


def test_09_long_running_follows_d32():
    text = code_without_comments(PROJECT)
    assert "DECLARE OR REPLACE VARIABLE long_running_months INT DEFAULT 24;" in text
    squashed = " ".join(text.split())
    assert (
        "ADD_MONTHS(project_rows.start_date, long_running_months) < LEAST( "
        "COALESCE(project_rows.completion_date, selected.snapshot_date), "
        "selected.snapshot_date )" in squashed
    )
    assert "MAX(DATE(load.source_modified_at)) AS snapshot_date" in text
    decisions = " ".join(DECISIONS.read_text(encoding="utf-8").split())
    assert "| D-32 |" in decisions
    assert "completion date" in decisions.split("| D-32 |", 1)[1].split("| D-33 |")[0]


def test_09b_long_running_is_null_when_completion_is_before_start():
    # d-49: a completion before the start cannot be measured (#116)
    squashed_text = squashed(PROJECT)
    assert (
        "CASE WHEN project_rows.start_date IS NULL THEN NULL "
        "WHEN project_rows.completion_date < project_rows.start_date THEN NULL "
        "ELSE ADD_MONTHS(project_rows.start_date, long_running_months) < LEAST("
        in squashed_text
    )
    assert "'gold-delivery-v3|long-running=start-to-completion-or-snapshot>'" in (
        squashed_text
    )
    decisions = " ".join(DECISIONS.read_text(encoding="utf-8").split())
    assert "| D-49 |" in decisions


def test_10_progress_is_published_only_when_silver_marks_it_valid():
    text = code_without_comments(PROJECT)
    # silver checks the 0 to 100 range once, so gold copies its quality status
    assert (
        "DECLARE OR REPLACE VARIABLE published_progress_quality STRING "
        "DEFAULT 'VALID';" in text
    )
    assert "project.progress_quality_status," in text
    assert (
        "WHEN project_rows.progress_quality_status = published_progress_quality" in text
    )
    assert "BETWEEN 0 AND 100" not in text
    # the rule label is built from the same variable, so it cannot drift
    assert (
        "'-months|completion-before-start=null|progress=silver-quality-', "
        "published_progress_quality" in text
    )


def test_11_current_snapshot_is_maintained_and_checked():
    text = sql(PROJECT)
    assert "TRUE AS is_current_snapshot" in text
    assert "'STOP: a project has more than one current snapshot row'" in text
    # one merge is one commit, so a failure cannot leave two current rows (#116)
    squashed_text = squashed(PROJECT)
    assert "UPDATE `03-gold`.fact_project_snapshot" not in squashed_text
    assert squashed_text.count("MERGE INTO `03-gold`.fact_project_snapshot ") == 1
    assert (
        "WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT * "
        "WHEN NOT MATCHED BY SOURCE AND target.is_current_snapshot "
        "THEN UPDATE SET is_current_snapshot = FALSE;" in squashed_text
    )
    # the current snapshot is also the newest one, checked before the merge
    message = (
        "STOP: Silver holds an older DPWH snapshot than fact_project_snapshot. "
        "Load the newest snapshot first."
    )
    check = stop_check(squashed_text, message)
    assert (
        "COUNT_IF(fact.snapshot_date_key > "
        "CAST(DATE_FORMAT(selected.snapshot_date, 'yyyyMMdd') AS INT)) = 0" in check
    )
    assert squashed_text.index(f"'{message}'") < squashed_text.index(
        "MERGE INTO `03-gold`.fact_project_snapshot "
    )


def test_11b_a_silver_status_without_a_dimension_row_stops_the_load():
    # key 0 is only for an empty silver status. a stale dimension stops the run (#116)
    squashed_text = squashed(PROJECT)
    message = (
        "STOP: a Silver status has no active dim_project_status row. "
        "Rerun 03_gold_dim_project_status first."
    )
    assert (
        f"SELECT ASSERT_TRUE( COUNT(*) = 0, '{message}' ) "
        "FROM `02-silver`.silver_project AS project "
        "LEFT ANTI JOIN `03-gold`.dim_project_status AS status "
        "ON status.source_system = project_source_system "
        "AND status.source_status = project.status_raw "
        "AND status.is_active AND status.status_key <> 0 "
        "WHERE project.status_raw IS NOT NULL;" in squashed_text
    )
    # the stop uses the same join as the status lookup that falls back to key 0
    assert (
        "LEFT JOIN `03-gold`.dim_project_status AS status "
        "ON status.source_system = project_source_system "
        "AND status.source_status = project_rows.status_raw "
        "AND status.is_active AND status.status_key <> 0" in squashed_text
    )
    assert "COALESCE(status.status_key, 0) AS status_key" in squashed_text
    assert squashed_text.index(f"'{message}'") < squashed_text.index(
        "MERGE INTO `03-gold`.fact_project_snapshot "
    )


def test_12_every_fact_resolves_keys_and_gates_on_silver_validation():
    for path in NOTEBOOKS:
        text = sql(path)
        assert "`04-validation`.silver_dq_results" in text, path.stem
        assert "dq.status IN ('FAIL', 'ERROR')" in text, path.stem
        assert "'STOP: run the Gold dimension notebooks 00 to 04 before the facts'" in (
            text
        )
    project = sql(PROJECT)
    assert "LEFT ANTI JOIN `03-gold`.dim_date AS calendar" in project
    assert "COUNT(*) = (SELECT COUNT(*) FROM `02-silver`.silver_project)" in project


def test_12b_every_fact_stops_on_a_missing_key_before_its_merge():
    # each fact stops before its MERGE when a key does not resolve (#121)
    stops = {
        "05_gold_fact_region_population": (
            (
                "STOP: every population row must resolve to one official region with a "
                "unique key, a load time, and the Silver total"
            ),
            ["COUNT_IF(region_key IS NULL OR region_key = 0) = 0"],
        ),
        "06_gold_fact_region_flood_exposure": (
            (
                "STOP: every exposure row must resolve to a real region and flood level "
                "with a unique key and the Silver areas"
            ),
            [
                "COUNT_IF(region_key IS NULL OR region_key = 0) = 0",
                (
                    "COUNT_IF(flood_susceptibility_key IS NULL OR "
                    "flood_susceptibility_key = 0) = 0"
                ),
            ],
        ),
        "07_gold_fact_project_snapshot": (
            (
                "STOP: every project needs one fact row with a project, region, and "
                "flood key, and the Silver budget total"
            ),
            [
                "COUNT_IF(project_key IS NULL) = 0",
                "COUNT_IF(region_key IS NULL) = 0",
                "COUNT_IF(flood_susceptibility_key IS NULL) = 0",
            ],
        ),
    }
    for name, (message, predicates) in stops.items():
        text = squashed(GOLD / f"{name}.ipynb")
        check = stop_check(text, message)
        for predicate in predicates:
            assert predicate in check, (name, predicate)
        merge = text.index(f"MERGE INTO `03-gold`.{NOTEBOOK_TABLES[name]} ")
        assert text.index(f"'{message}'") < merge, name


def test_12c_region_joins_and_totals_are_null_safe():
    # psgc_version can be NULL, and = drops every NULL match. <=> keeps it (#121)
    predicates = {
        "05_gold_fact_region_population": [
            "AND population.psgc_version <=> region.psgc_version",
            "AND SUM(population_count) <=> (SELECT SUM(silver.population_count)",
        ],
        "06_gold_fact_region_flood_exposure": [
            "AND exposure.psgc_version <=> region.psgc_version",
            "AND SUM(susceptible_area_sqkm) <=> ( SELECT SUM(silver.susceptible_area_sqkm)",
        ],
        "07_gold_fact_project_snapshot": [
            "AND project_rows.psgc_version <=> region.psgc_version",
            "AND SUM(reported_budget_pesos) <=> ( SELECT SUM(silver.reported_budget_pesos)",
        ],
    }
    for name, expected in predicates.items():
        text = squashed(GOLD / f"{name}.ipynb")
        for predicate in expected:
            assert predicate in text, (name, predicate)


def test_13_facts_read_source_systems_from_the_dimensions():
    for path in NOTEBOOKS:
        text = code_without_comments(path)
        for literal in ["'DPWH'", "'DENR MGB flood susceptibility'"]:
            assert literal not in text, (path.stem, literal)
    exposure = code_without_comments(GOLD / "06_gold_fact_region_flood_exposure.ipynb")
    project = code_without_comments(PROJECT)
    for text in (exposure, project):
        assert "SET VAR mgb_mapping_source_system = (" in text
    assert "SET VAR project_source_system = (" in project


def test_14_markdown_quotes_no_run_counts():
    # counts change on every run, so the summary queries show them instead
    for path in NOTEBOOKS:
        text = markdown(path)
        assert not re.search(r"\b\d{1,3}(?:,\d{3})+\b", text), path.stem
