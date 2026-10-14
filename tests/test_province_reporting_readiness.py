import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/02_silver/08b_profile_project_province_readiness.ipynb"
READINESS_DOC = ROOT / "docs/province_reporting_readiness.md"
DECISIONS = ROOT / "docs/decisions.md"


def notebook():
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def source(cell_type=None):
    cells = notebook()["cells"]
    if cell_type:
        cells = [cell for cell in cells if cell["cell_type"] == cell_type]
    return "\n".join("".join(cell.get("source", [])) for cell in cells)


def sql():
    return source("code")


def sql_without_comments():
    return "\n".join(line.split("--", 1)[0] for line in sql().splitlines())


def test_notebook_is_a_valid_databricks_sql_notebook():
    nb = notebook()
    assert nb["nbformat"] == 4
    assert nb["metadata"]["language_info"] == {"name": "sql"}
    databricks = nb["metadata"]["application/vnd.databricks.v1+notebook"]
    assert databricks["language"] == "sql"
    assert databricks["notebookName"] == "08b_profile_project_province_readiness"
    assert nb["cells"][0]["cell_type"] == "markdown"
    for index, cell in enumerate(nb["cells"]):
        if cell["cell_type"] == "code":
            assert "".join(cell["source"]).startswith("%sql\n")
            assert cell["outputs"] == []
            assert nb["cells"][index - 1]["cell_type"] == "markdown"


def test_profile_is_read_only_and_keeps_persistent_tables_unchanged():
    text = sql_without_comments().upper()
    for token in [
        "CREATE TABLE",
        "CREATE OR REPLACE TABLE",
        "MERGE INTO",
        "INSERT INTO",
        "UPDATE ",
        "DELETE FROM",
        "DROP TABLE",
        "TRUNCATE",
    ]:
        assert token not in text
    assert "CREATE OR REPLACE TEMPORARY VIEW" in text


def test_profile_reads_one_canonical_project_and_preserves_budget():
    text = sql_without_comments()
    assert "FROM `02-silver`.silver_project AS project" in text
    assert "COUNT(*) = COUNT(DISTINCT project_key)" in text
    assert "'STOP: readiness profiling changed the canonical project grain'" in text
    assert "SUM(reported_budget_pesos) <=>" in text
    assert (
        "'STOP: readiness profiling changed the canonical reported-budget total'"
        in text
    )


def test_raw_dpwh_province_is_only_exact_source_evidence():
    text = sql_without_comments()
    assert "GET_JSON_OBJECT(bronze.source_record_json, '$.location.province')" in text
    assert "REGEXP_REPLACE(" in text
    assert "UPPER(NULLIF(TRIM(GET_JSON_OBJECT(" in text
    assert "place_type = 'PROVINCE'" in text
    assert "project.reported_province_standardized" in text
    assert "= province.psgc_province_name_standardized" in text
    lower = text.lower()
    for forbidden in [
        "levenshtein(",
        "soundex(",
        "jaro",
        "similarity(",
        "st_distance(",
        "like concat(",
    ]:
        assert forbidden not in lower


def test_spatial_profile_is_longitude_first_and_keeps_ambiguity():
    text = sql_without_comments()
    assert "ST_COVERS(" in text
    assert "ST_POINT(project.longitude, project.latitude, 4326)" in text
    assert "COUNT(DISTINCT boundary.resolved_current_province_code)" in text
    assert "spatial_candidate_count = 0" in text
    assert "spatial_candidate_count = 1" in text
    assert "spatial_candidate_count > 1" in text
    assert "'NAME_COORDINATE_CONFLICT'" in text
    assert "'AMBIGUOUS'" in text
    assert "'UNMAPPED'" in text


def test_required_project_budget_and_special_area_outputs_exist():
    text = sql_without_comments()
    for column in [
        "total_projects",
        "projects_with_valid_coordinates",
        "projects_without_valid_coordinates",
        "projects_in_exactly_one_province_polygon",
        "valid_coordinate_projects_in_zero_province_polygons",
        "projects_in_multiple_province_polygons",
        "projects_with_exact_official_province_name",
        "projects_with_nonofficial_source_province_text",
        "projects_where_name_and_coordinate_agree",
        "projects_where_name_and_coordinate_conflict",
        "unique_spatial_project_coverage_pct",
        "unique_spatial_budget_coverage_pct",
    ]:
        assert column in text
    assert "THEN 'NCR'" in text
    assert "THEN 'BARMM'" in text
    assert "city_rows_without_official_province_parent" in text
    assert "'NOT_AVAILABLE_IN_CURRENT_SILVER_CONTRACT'" in text


def test_boundary_and_psgc_version_gaps_are_reported():
    text = sql_without_comments()
    assert "boundary.source_psgc_version AS boundary_psgc_version" in text
    assert "boundary.source_boundary_version AS boundary_version" in text
    for finding in [
        "BOUNDARY_CODES_NOT_IN_CURRENT_PSGC",
        "CURRENT_PSGC_PROVINCES_WITHOUT_BOUNDARY",
        "INVALID_OR_UNPARSEABLE_PROVINCE_BOUNDARIES",
    ]:
        assert f"'{finding}'" in text


def test_docs_keep_d34_and_record_d55_as_approved():
    readiness = READINESS_DOC.read_text(encoding="utf-8")
    decisions = DECISIONS.read_text(encoding="utf-8")
    assert "D-34 remains approved" in readiness
    assert "Databricks runtime evidence" in readiness
    assert "Option B" in readiness
    proposed = decisions.split("## Proposed decisions awaiting team approval", 1)[1]
    assert "| D-55 |" not in proposed
    made = decisions.split("## Made", 1)[1].split(
        "## Proposed decisions awaiting team approval", 1
    )[0]
    assert "| D-55 |" in made
