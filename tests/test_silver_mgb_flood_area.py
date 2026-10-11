import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AREA_NOTEBOOK = ROOT / "notebooks/02_silver/08a_silver_mgb_flood_area.ipynb"
VALIDATION_NOTEBOOK = (
    ROOT / "notebooks/04_validation/06a_validation_silver_mgb_flood_area.ipynb"
)
READER_NOTEBOOKS = [
    ROOT / "notebooks/02_silver/09_silver_region_flood_exposure.ipynb",
    ROOT / "notebooks/02_silver/10_silver_project_flood_map.ipynb",
    ROOT / "notebooks/04_validation/07_validation_silver_region_flood_exposure.ipynb",
    ROOT / "notebooks/04_validation/08_validation_silver_project_flood_map.ipynb",
]
TABLE = "`02-silver`.silver_mgb_flood_area"


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


def esri_parser_block():
    text = sql(AREA_NOTEBOOK)
    start = text.index("esri_ring_source AS (")
    end_marker = "    FROM esri_ring_parts\n)"
    return text[start : text.index(end_marker, start) + len(end_marker)]


def test_01_notebooks_are_valid_nbformat_sql_notebooks():
    for path in (AREA_NOTEBOOK, VALIDATION_NOTEBOOK):
        nb = notebook(path)
        assert nb["nbformat"] == 4
        assert nb["nbformat_minor"] >= 5
        meta = nb["metadata"]["application/vnd.databricks.v1+notebook"]
        assert meta["language"] == "sql"
        assert meta["notebookName"] == path.stem
        code_cells = [cell for cell in nb["cells"] if cell["cell_type"] == "code"]
        assert code_cells
        assert all("".join(cell["source"]).startswith("%sql\n") for cell in code_cells)
        assert all(cell["outputs"] == [] for cell in code_cells)


def test_02_table_has_explicit_schema_and_documented_grain():
    text = sql(AREA_NOTEBOOK)
    assert f"CREATE TABLE IF NOT EXISTS {TABLE} (" in text
    for column in [
        "mgb_flood_area_key STRING NOT NULL",
        "object_id STRING NOT NULL",
        "raw_susceptibility_code STRING",
        "geometry_wkb BINARY",
        "geometry_srid INT",
        "geometry_parse_method STRING NOT NULL",
        "source_geometry_status STRING NOT NULL",
        "mgb_source_snapshot_id STRING NOT NULL",
        "parse_rule_version STRING NOT NULL",
        "run_id STRING NOT NULL",
        "source_load_ts TIMESTAMP",
    ]:
        assert column in text
    grain = (
        "One MGB flood-susceptibility polygon (one Bronze source row) "
        "per Bronze snapshot per parse rule version"
    )
    assert f"COMMENT '{grain}'" in text
    assert grain.lower() in markdown(AREA_NOTEBOOK).lower()


def test_03_upstream_safety_uses_newest_terminal_load_and_validation():
    text = sql(AREA_NOTEBOOK)
    assert "ORDER BY COALESCE(completed_at, started_at) DESC, started_at DESC" in text
    assert (
        "'STOP: latest MGB Bronze load is missing, failed, unidentified, or empty'"
        in text
    )
    assert "'STOP: latest MGB Bronze validation is missing or unsafe'" in text
    assert (
        "'STOP: current MGB Bronze rows do not match the validated MGB snapshot'"
        in text
    )


def test_04_object_id_must_identify_one_polygon_before_keys_are_built():
    text = sql(AREA_NOTEBOOK)
    assert (
        "COUNT(*) - COUNT(DISTINCT TRIM(object_id)) AS duplicate_object_id_rows" in text
    )
    assert (
        "'STOP: MGB object_id is blank or repeated, so it cannot identify one polygon'"
        in text
    )
    assert (
        "SHA2(CONCAT_WS('||', classified.object_id, selected.mgb_source_snapshot_id, "
        "selected.parse_rule_version), 256)\n        AS mgb_flood_area_key"
    ) in text


def test_05_run_id_is_deterministic_and_includes_the_parse_rule():
    text = code_without_comments(AREA_NOTEBOOK)
    run_id = text[text.index("SHA2(CONCAT_WS(\n        '||',\n        mgb_context") :]
    run_id = run_id[: run_id.index("AS mgb_flood_area_run_id")]
    assert "parse_rule_version" in run_id
    assert "mgb_source_snapshot_id" in run_id
    for nondeterministic in ["CURRENT_TIMESTAMP", "NOW()", "UUID", "RAND"]:
        assert nondeterministic not in run_id.upper()


def test_06_an_unchanged_snapshot_is_not_parsed_again():
    text = sql(AREA_NOTEBOOK)
    assert "DECLARE OR REPLACE VARIABLE mgb_flood_area_is_current BOOLEAN;" in text
    assert "published.published_rows = selected.audited_rows_loaded" in text
    assert "published.selected_run_rows = published.published_rows" in text
    assert "WHEN mgb_flood_area_is_current" in text
    assert f"ELSE 'INSERT OVERWRITE {TABLE}" in text
    assert "EXECUTE IMMEDIATE mgb_flood_area_publish_sql;" in text
    # the reconciliation gate reads the published table, so a skip is checked as well
    gate = text[text.rindex("SELECT\n    accounting.*") :]
    assert f"FROM {TABLE} AS area" in gate
    assert (
        "'STOP: published MGB flood areas do not reconcile with the selected Bronze snapshot'"
        in gate
    )


def test_07_geometry_is_stored_as_wkb_and_codes_stay_raw():
    text = code_without_comments(AREA_NOTEBOOK)
    assert "ST_ASWKB(classified.mgb_geometry) AS geometry_wkb" in text
    assert "ST_SRID(classified.mgb_geometry) AS geometry_srid" in text
    # the approved mapping is applied by the readers, so a new mapping version never forces a parse
    assert "config_mgb_susceptibility_mapping" not in text
    assert "standardized_level" not in text


def test_08_geometry_statuses_and_parse_methods_use_the_governed_vocabulary():
    text = sql(AREA_NOTEBOOK)
    for status in [
        "BLANK_GEOMETRY",
        "UNPARSEABLE_GEOMETRY",
        "EMPTY_GEOMETRY",
        "UNSUPPORTED_GEOMETRY_TYPE",
        "INVALID_GEOMETRY",
        "REPAIRED_GEOMETRY",
        "USABLE_GEOMETRY",
        "GEOJSON_AS_PUBLISHED",
        "GEOJSON_QUOTED_NUMBERS_NORMALIZED",
        "ESRI_JSON_CONVERTED",
    ]:
        assert f"'{status}'" in text
    assert "WHEN NOT ST_ISVALID(parsed.mgb_geometry) THEN 'INVALID_GEOMETRY'" in text
    # the zero-distance buffer is the D-43 repair and appears only once
    assert text.upper().count("ST_BUFFER(") == 1


def test_18_only_invalid_polygons_are_repaired_within_the_d43_area_tolerance():
    text = sql(AREA_NOTEBOOK)
    assert (
        "DECLARE OR REPLACE VARIABLE repair_area_tolerance_ratio DOUBLE DEFAULT 0.01;"
        in text
    )
    assert (
        "DECLARE OR REPLACE VARIABLE repair_area_tolerance_sqm DOUBLE DEFAULT 10000;"
        in text
    )
    # the zero-distance buffer runs only for an OGC-invalid polygon
    assert text.count("ST_BUFFER(") == 1
    assert (
        "WHEN classified.source_geometry_status = 'INVALID_GEOMETRY'\n"
        "            THEN ST_BUFFER(classified.mgb_geometry, 0)"
    ) in text
    # the repair must be a valid polygon whose area stays close to the MGB Shape__Area
    assert "ST_AREA(ST_TRANSFORM(repaired_geometry, source_area_srid))" in text
    assert (
        "<= GREATEST(repair_area_tolerance_ratio * source_shape_area, repair_area_tolerance_sqm)"
        in text
    )
    assert (
        "CASE WHEN is_repaired THEN 'REPAIRED_GEOMETRY' ELSE source_geometry_status END"
        in text
    )
    # the rule version changes with the tolerance, so a new tolerance forces a new parse
    assert "'|makevalid-invalid-within-ratio=', repair_area_tolerance_ratio," in text


def test_19_readers_use_repaired_geometry_as_usable_and_keep_it_visible():
    for path in READER_NOTEBOOKS:
        code = code_without_comments(path)
        assert "ST_MAKEVALID" not in code.upper(), path.name
        assert "ST_BUFFER" not in code.upper(), path.name
        assert "'REPAIRED_GEOMETRY'" in code, path.name
        assert "AS is_repaired_geometry" in code, path.name
    region_check = sql(READER_NOTEBOOKS[2])
    assert "'Repaired MGB geometry used in area remains visible'" in region_check
    project_check = sql(READER_NOTEBOOKS[3])
    assert (
        "'Matched projects that depend on repaired MGB geometry remain visible'"
        in project_check
    )


def test_09_parser_is_targeted_not_global_quote_stripping():
    text = sql(AREA_NOTEBOOK)
    assert "REPLACE(mgb.geometry_json, '\"'" not in text
    assert "REPLACE(geometry_text, '\"'" not in text
    # GeoJSON readers skip Esri rows, since Esri JSON is never GeoJSON
    assert (
        "WHEN esri_text.esri_rings_text IS NULL\n            THEN TRY_TO_GEOMETRY(esri_text.geometry_text)"
        in text
    )
    assert (
        "WHEN esri_rings_text IS NULL\n            THEN TRY_TO_GEOMETRY(REGEXP_REPLACE("
        in text
    )


def test_10_esri_holes_are_read_as_holes_only_when_the_first_reading_is_invalid():
    parser = esri_parser_block()
    # Esri outer rings run clockwise and holes counterclockwise, read by the shoelace sign
    assert "ring[i - 1][0] * ring[i][1] - ring[i][0] * ring[i - 1][1]" in parser
    assert "part -> part.area < 0" in parser
    assert "part -> part.area > 0" in parser
    # a valid first reading is never changed
    assert (
        "esri_ring_geometry IS NOT NULL AND ST_ISVALID(esri_ring_geometry) AS esri_ring_geometry_is_valid"
        in parser
    )
    assert (
        "WHEN esri_ring_geometry_is_valid\n                        THEN esri_ring_geometry"
        in parser
    )
    assert "THEN ST_DIFFERENCE(" in parser


def test_11_esri_rings_are_read_as_text_and_as_arrays_only_for_holes():
    parser = esri_parser_block()
    # arrays of the largest MGB polygons run out of executor memory
    assert (
        "REGEXP_REPLACE(esri_rings_text, '\\\\]\\\\s*\\\\]\\\\s*,\\\\s*\\\\[\\\\s*\\\\[', ']]],[[[')"
        in parser
    )
    first_reading = parser[: parser.index("esri_ring_checked AS (")]
    assert "FROM_JSON(" not in first_reading
    assert "TO_JSON(" not in first_reading
    assert "GET_JSON_OBJECT" not in sql(AREA_NOTEBOOK)
    assert (
        "WHEN esri_rings_text IS NOT NULL AND NOT esri_ring_geometry_is_valid\n"
        "            THEN FROM_JSON(esri_rings_text, 'ARRAY<ARRAY<ARRAY<DOUBLE>>>')"
    ) in parser


def test_12_only_this_notebook_parses_mgb_geometry():
    assert "mgb.geometry_json" in sql(AREA_NOTEBOOK)
    for path in READER_NOTEBOOKS:
        code = code_without_comments(path)
        assert "mgb.geometry_json" not in code, path.name
        assert "direct_parse" not in code, path.name
        assert "FROM_JSON(" not in code, path.name
        assert f"{TABLE} AS area" in code, path.name
        assert "ST_GEOMFROMWKB(area.geometry_wkb)" in code, path.name


def test_13_transformations_require_safe_parsed_geometry_evidence():
    for path in READER_NOTEBOOKS[:2]:
        text = sql(path)
        assert "WHERE table_name = 'silver_mgb_flood_area'" in text
        assert "'STOP: Silver MGB flood-area validation is missing or unsafe'" in text
        assert "not built from the latest validated MGB snapshot" in text
        assert "AND area.run_id = selected.mgb_flood_area_run_id;" in text


def test_14_validator_compares_with_bronze_on_object_id():
    text = sql(VALIDATION_NOTEBOOK)
    assert (
        "FULL OUTER JOIN published\n        ON bronze.object_id = published.object_id"
        in text
    )
    assert "mgb.geometry_json" not in text
    for metric in [
        "bronze_rows_not_published",
        "published_rows_without_bronze",
        "raw_code_mismatches",
        "duplicate_keys",
        "key_mismatches",
        "usable_rows_failing_rebuild",
    ]:
        assert f"AS {metric}" in text


def test_15_validator_covers_seven_attributes_and_persists_before_the_gate():
    text = sql(VALIDATION_NOTEBOOK)
    for attribute in [
        "Consistency",
        "Accuracy",
        "Completeness",
        "Auditability",
        "Validity",
        "Uniqueness",
        "Timeliness",
    ]:
        assert f"'attribute', '{attribute}'" in text
    assert "'silver_mgb_flood_area' AS table_name" in text
    merge = text.index("MERGE INTO `04-validation`.silver_dq_results")
    gate = text.index("blocking Silver MGB flood-area checks failed")
    assert merge < gate


def test_16_every_validator_check_has_a_known_action():
    text = sql(VALIDATION_NOTEBOOK)
    actions = re.findall(r"'action', '(\w+)'", text)
    assert actions
    assert set(actions) <= {"stop", "flag"}


def run_id_parts(text, start, end):
    segment = text[text.index(start) :]
    segment = segment[: segment.index(end)]
    segment = re.sub(r"'[^']*'", "", segment.split("CONCAT_WS(", 1)[1])
    names = re.findall(r"(?:\w+\.)?(\w+)", segment)
    return [name for name in names if name.upper() not in {"COALESCE", "SHA2"}]


def test_17_validators_recompute_run_ids_with_the_same_parts_as_the_transformations():
    exposure = run_id_parts(
        sql(READER_NOTEBOOKS[0]),
        "SHA2(CONCAT_WS(\n        '||',\n        mgb_context",
        ") AS exposure_run_id",
    )
    exposure_check = run_id_parts(
        sql(READER_NOTEBOOKS[2]),
        "published.run_id <> SHA2(CONCAT_WS(",
        ") AS invalid_run_ids",
    )
    flood_map = run_id_parts(
        sql(READER_NOTEBOOKS[1]),
        "SHA2(CONCAT_WS(\n        '||',\n        project_context",
        ") AS project_flood_run_id",
    )
    flood_map_check = run_id_parts(
        sql(READER_NOTEBOOKS[3]),
        "COUNT_IF(run_id <> SHA2(CONCAT_WS(",
        ") AS invalid_run_ids",
    )
    assert "mgb_flood_area_run_id" in exposure
    assert exposure == exposure_check
    assert "mgb_flood_area_run_id" in flood_map
    assert flood_map == flood_map_check


def test_20_validator_checks_the_d43_repair_independently():
    text = sql(VALIDATION_NOTEBOOK)
    assert (
        "DECLARE OR REPLACE VARIABLE repair_area_tolerance_ratio DOUBLE DEFAULT 0.01;"
        in text
    )
    assert "'REPAIRED_GEOMETRY', 'USABLE_GEOMETRY'" in text
    assert "ST_AREA(ST_TRANSFORM(published.usable_geometry, source_area_srid))" in text
    stop = text.split(
        "'Repaired geometry keeps the MGB area within the D-43 tolerance'", 1
    )[1]
    assert "'action', 'stop'" in stop.split("NAMED_STRUCT", 1)[0]
    flag = text.split("'Repaired MGB geometry remains visible'", 1)[1]
    assert "'action', 'flag'" in flag.split("NAMED_STRUCT", 1)[0]
