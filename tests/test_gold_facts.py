import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "notebooks/03_gold"
GOLD_MODEL = ROOT / "docs/gold_model.md"
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
    labels = {
        "05_gold_fact_region_population": "'REGION_POPULATION'",
        "06_gold_fact_region_flood_exposure": "'REGION_FLOOD_EXPOSURE'",
        "07_gold_fact_project_snapshot": "'PROJECT_SNAPSHOT'",
    }
    for name, label in labels.items():
        text = sql(GOLD / f"{name}.ipynb")
        assert "XXHASH64(CONCAT_WS(" in text, name
        assert label in text, name


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
        "WHEN project_rows.region_match_status IN ('MATCHED', 'MATCHED_WITH_CONFLICT')"
        in text
    )
    assert "WHEN project_rows.flood_match_status = 'MATCHED' THEN" in text
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


def test_10_progress_is_published_only_between_0_and_100():
    text = code_without_comments(PROJECT)
    assert "WHEN project_rows.physical_progress_pct BETWEEN 0 AND 100" in text
    assert "progress-range=0:100" in text


def test_11_current_snapshot_is_maintained_and_checked():
    text = sql(PROJECT)
    assert "TRUE AS is_current_snapshot" in text
    assert "UPDATE `03-gold`.fact_project_snapshot\nSET is_current_snapshot = (" in text
    assert "'STOP: a project has more than one current snapshot row'" in text


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
