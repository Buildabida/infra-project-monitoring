import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "notebooks/03_gold"
GOLD_MODEL = ROOT / "docs/gold_model.md"
REGION_MAP_NOTEBOOK = ROOT / "notebooks/02_silver/08_silver_project_region_map.ipynb"

# notebook -> gold tables it creates
NOTEBOOK_TABLES = {
    "00_gold_dim_date": ["dim_date"],
    "01_gold_dim_region": ["dim_region", "dim_region_boundary"],
    "02_gold_dim_flood_susceptibility": ["dim_flood_susceptibility"],
    "03_gold_dim_project_status": ["dim_project_status"],
    "04_gold_dim_project": ["dim_project"],
}
NOTEBOOKS = [GOLD / f"{name}.ipynb" for name in NOTEBOOK_TABLES]


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
    """Return (column, type) pairs from one CREATE TABLE statement, in order."""
    start = text.index(f"CREATE TABLE IF NOT EXISTS `03-gold`.{table} (\n")
    body = text[start:].split("\n", 1)[1].split("\n)\nUSING DELTA", 1)[0]
    columns = []
    for line in body.splitlines():
        match = re.match(r"^    (\w+) (\S+)(?: NOT NULL)? COMMENT '[^']+',?$", line)
        assert match, f"{table}: column line has no comment or bad shape: {line}"
        columns.append((match.group(1), match.group(2)))
    return columns


def model_columns(table):
    """Return (column, type) pairs for one table in docs/gold_model.md, in order."""
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
        assert nb["nbformat_minor"] >= 5
        meta = nb["metadata"]["application/vnd.databricks.v1+notebook"]
        assert meta["language"] == "sql"
        assert meta["notebookName"] == path.stem
        ids = [cell["id"] for cell in nb["cells"]]
        assert len(ids) == len(set(ids))
        code_cells = [cell for cell in nb["cells"] if cell["cell_type"] == "code"]
        assert code_cells
        for cell in code_cells:
            assert "".join(cell["source"]).startswith("%sql\n")
            assert cell["outputs"] == []


def test_02_every_code_cell_has_markdown_before_it():
    for path in NOTEBOOKS:
        cells = notebook(path)["cells"]
        assert cells[0]["cell_type"] == "markdown"
        for index, cell in enumerate(cells):
            if cell["cell_type"] == "code":
                assert cells[index - 1]["cell_type"] == "markdown"
        text = markdown(path)
        for heading in ["## Purpose", "## Grain", "# Summary"]:
            assert heading in text, (path.stem, heading)


def test_03_first_sql_uses_the_project_catalog():
    for path in NOTEBOOKS:
        first_code = sql(path).split("%sql\n", 1)[1]
        assert first_code.startswith("USE CATALOG `buildabida-capstone`;")


def test_04_tables_match_gold_model_names_types_and_order():
    for name, tables in NOTEBOOK_TABLES.items():
        text = sql(GOLD / f"{name}.ipynb")
        for table in tables:
            assert ddl_columns(text, table) == model_columns(table), table


def test_05_tables_are_created_once_and_loaded_with_merge():
    for name, tables in NOTEBOOK_TABLES.items():
        text = sql(GOLD / f"{name}.ipynb")
        upper = text.upper()
        for table in tables:
            assert text.count(f"CREATE TABLE IF NOT EXISTS `03-gold`.{table} (") == 1
            assert text.count(f"MERGE INTO `03-gold`.{table} AS target") == 1
        for token in [
            "DROP TABLE",
            "TRUNCATE",
            "CREATE OR REPLACE TABLE",
            "DELETE FROM",
        ]:
            assert token not in upper, (name, token)


def test_06_every_table_has_a_comment():
    for name, tables in NOTEBOOK_TABLES.items():
        text = sql(GOLD / f"{name}.ipynb")
        for table in tables:
            ddl = text.split(f"CREATE TABLE IF NOT EXISTS `03-gold`.{table} (", 1)[1]
            tail = ddl.split("\n)\nUSING DELTA\n", 1)[1]
            assert tail.startswith("COMMENT '"), table


def test_07_keys_are_deterministic_hashes():
    expected = {
        "00_gold_dim_date": "CAST(DATE_FORMAT(calendar.calendar_date, 'yyyyMMdd') AS INT) AS date_key",
        "01_gold_dim_region": "AS region_key",
        "02_gold_dim_flood_susceptibility": "AS flood_susceptibility_key",
        "03_gold_dim_project_status": "AS status_key",
        "04_gold_dim_project": "AS project_key",
    }
    hash_function = {
        "01_gold_dim_region": "XXHASH64(",
        "02_gold_dim_flood_susceptibility": "HASH(CONCAT_WS(",
        "03_gold_dim_project_status": "HASH(CONCAT_WS(",
        "04_gold_dim_project": "XXHASH64(",
    }
    for name, marker in expected.items():
        text = sql(GOLD / f"{name}.ipynb")
        assert marker in text, name
        if name in hash_function:
            assert hash_function[name] in text, name
    region = sql(GOLD / "01_gold_dim_region.ipynb")
    assert ")) AS boundary_key" in region
    assert "XXHASH64(CONCAT_WS(\n        '|', 'REGION_BOUNDARY'" in region
    labels = {
        "01_gold_dim_region": "'|', 'PSGC_REGION',",
        "02_gold_dim_flood_susceptibility": "'|', 'FLOOD_SUSCEPTIBILITY',",
        "03_gold_dim_project_status": "'|', 'PROJECT_STATUS',",
        "04_gold_dim_project": "'|', 'PROJECT',",
    }
    for name, label in labels.items():
        assert label in sql(GOLD / f"{name}.ipynb"), (name, label)


def test_08_no_random_or_current_time_in_any_notebook():
    for path in NOTEBOOKS:
        code = code_without_comments(path).lower()
        for token in [
            "uuid(",
            "rand(",
            "random(",
            "monotonically_increasing_id",
            "current_timestamp",
            "current_date",
            "now()",
        ]:
            assert token not in code, (path.stem, token)
        # row_number only ranks load_log audit events. it never builds a key.
        ranks = code.count("as terminal_rank") + code.count("as audit_rank")
        assert code.count("row_number()") == ranks, path.stem


def test_09_unknown_member_is_key_zero_where_facts_need_it():
    assert "0 AS date_key" in sql(GOLD / "00_gold_dim_date.ipynb")
    assert "CAST(0 AS BIGINT) AS region_key" in sql(GOLD / "01_gold_dim_region.ipynb")
    flood = sql(GOLD / "02_gold_dim_flood_susceptibility.ipynb")
    assert "0 AS flood_susceptibility_key" in flood
    assert "'Unknown' AS flood_susceptibility_level" in flood
    assert "0 AS status_key" in sql(GOLD / "03_gold_dim_project_status.ipynb")
    for path in NOTEBOOKS:
        if path.stem == "04_gold_dim_project":
            continue
        assert "= 0) = 1" in sql(path), path.stem


def test_10_gold_runs_no_spatial_matching_or_area_work():
    for path in NOTEBOOKS:
        upper = code_without_comments(path).upper()
        for token in [
            "ST_INTERSECTS",
            "ST_INTERSECTION",
            "ST_UNION_AGG",
            "ST_TRANSFORM",
            "ST_AREA",
            "ST_COVERS",
            "ST_CONTAINS",
            "ST_BUFFER",
        ]:
            assert token not in upper, (path.stem, token)


def test_11_boundary_parser_is_table_13_with_raw_literals():
    def parser(text):
        start = text.index("    TRY_TO_GEOMETRY(REGEXP_REPLACE(")
        end_marker = ")) AS boundary_geometry"
        return text[start : text.index(end_marker, start) + len(end_marker)]

    def as_raw_literals(text):
        # same regex, written as r'...' so the vs code %sql magic cannot change it
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("'\\\"") and stripped.endswith("',"):
                indent = line[: len(line) - len(line.lstrip())]
                body = stripped[1:-2].replace("\\\\", "\\").replace('\\"', '"')
                line = f"{indent}r'{body}',"
            lines.append(line)
        return "\n".join(lines)

    gold = sql(GOLD / "01_gold_dim_region.ipynb")
    expected = as_raw_literals(parser(sql(REGION_MAP_NOTEBOOK)))
    assert expected.count("r'\"") == 2
    assert parser(gold) == expected
    assert "WHERE LOWER(TRIM(boundary.administrative_level)) = 'region'" in gold


def test_11b_gold_sql_has_no_double_backslash():
    # the vs code %sql magic turns \\ into \ before spark parses the statement
    for path in NOTEBOOKS:
        assert "\\\\" not in sql(path), path.stem


def test_12_region_dimension_reuses_table_14_boundary_safety():
    text = sql(GOLD / "01_gold_dim_region.ipynb")
    assert "FROM `02-silver`.silver_region_flood_exposure" in text
    assert "status.region_boundary_status = 'VALID_REGION_BOUNDARY'" in text
    assert "status.region_boundary_status AS psgc_match_status" in text
    assert "exposure_psgc_run_id <=> psgc_run_id" in text
    assert "ST_SETSRID(parsed.boundary_geometry, 4326) AS boundary_geometry" in text


def test_13_flood_levels_come_only_from_approved_configuration():
    text = code_without_comments(GOLD / "02_gold_dim_flood_susceptibility.ipynb")
    assert "mapping.approval_status = 'APPROVED'" in text
    assert "mapping.is_active = TRUE" in text
    assert "COUNT(DISTINCT mapping_version) = 1" in text
    for literal in ["'LF'", "'MF'", "'HF'", "'VHF'", "'Low'", "'Moderate'", "'High'"]:
        assert literal not in text
    assert "'Very High'" not in text


def test_14_status_dimension_never_maps_a_status_itself():
    text = code_without_comments(GOLD / "03_gold_dim_project_status.ipynb")
    for literal in ["'Completed'", "'On-Going'", "'Terminated'", "'For Procurement'"]:
        assert literal not in text
    assert "NO_APPROVED_STATUS_MAPPING" in text
    assert "mapping.source_system = project_source_system" in text
    assert "mapping.approval_status = 'APPROVED'" in text
    assert "COUNT(DISTINCT status_mapping_version) <= 1" in text
    assert "SET is_active = FALSE" in text


def test_15_project_dimension_reuses_silver_and_exact_flood_list_matches():
    text = code_without_comments(GOLD / "04_gold_dim_project.ipynb")
    assert "FROM `02-silver`.silver_project AS project" in text
    assert "source_match.match_status = 'MATCHED_EXACT_CONTRACT_ID'" in text
    assert "MAX(target_project_run_id) = (SELECT MAX(project.run_id)" in text
    # silver publishes the parsed year since #90, so gold copies it (d-38)
    assert "project.infra_year_parsed AS infra_year" in text
    assert "TRY_CAST(project.infra_year" not in text
    # silver owns the taxonomy since #94, so gold copies it (d-37, d-39)
    assert "project.source_infra_type," in text
    assert "project.is_dpwh_flood_related," in text
    assert "project.category_classification_status AS infra_type_mapping_status" in text
    assert "category_resolution_status" not in text
    assert "CAST(NULL AS BOOLEAN) AS is_dpwh_flood_related" not in text
    # silver resolves the deo field since #95, so gold copies the office
    assert "project.implementing_office," in text
    assert "CAST(NULL AS STRING) AS implementing_office" not in text
    # flood-list cost is evidence only and never reaches the project dimension
    assert "contract_cost" not in text.lower()
    assert "01-bronze`.dpwh_projects" not in text


def test_16_every_notebook_gates_on_silver_validation():
    for path in NOTEBOOKS:
        if path.stem == "00_gold_dim_date":
            continue
        text = sql(path)
        assert "ASSERT_TRUE" in text, path.stem
        assert (
            "`04-validation`.silver_dq_results" in text
            or "`04-validation`.silver_config_dq_results" in text
        ), path.stem
        assert "dq.status IN ('FAIL', 'ERROR')" in text or (
            "status IN ('FAIL', 'ERROR')" in text
        ), path.stem


def test_17_gold_model_documents_the_dimension_answers():
    text = " ".join(GOLD_MODEL.read_text(encoding="utf-8").split())
    for phrase in [
        "XXHASH64",
        "`03_gold_dim_project_status",
        "NO_APPROVED_STATUS_MAPPING",
        "D-33",
    ]:
        assert phrase in text, phrase
