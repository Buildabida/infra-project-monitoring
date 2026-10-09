import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOOD_MAP_NOTEBOOK = ROOT / "notebooks/02_silver/10_silver_project_flood_map.ipynb"
VALIDATION_NOTEBOOK = (
    ROOT / "notebooks/04_validation/08_validation_silver_project_flood_map.ipynb"
)
EXPOSURE_NOTEBOOK = ROOT / "notebooks/02_silver/09_silver_region_flood_exposure.ipynb"
REGION_MAP_NOTEBOOK = ROOT / "notebooks/02_silver/08_silver_project_region_map.ipynb"
CONTRACT_DOC = ROOT / "docs/silver_project_flood_mapping.md"
TABLE = "`02-silver`.silver_project_flood_map"
ATTRIBUTES = [
    "Consistency",
    "Accuracy",
    "Completeness",
    "Auditability",
    "Validity",
    "Uniqueness",
    "Timeliness",
]


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


def publish_select():
    return sql(FLOOD_MAP_NOTEBOOK).split(f"CREATE OR REPLACE TABLE {TABLE}", 1)[1]


def view_body(text, view):
    start = text.index(f"CREATE OR REPLACE TEMPORARY VIEW {view} AS")
    end = text.find("CREATE OR REPLACE", start + 1)
    return text[start : end if end > 0 else len(text)]


def classified_view(text):
    start = text.index("CREATE OR REPLACE TEMPORARY VIEW mgb_source_classified AS")
    end_marker = "ON parsed.raw_susceptibility_code = mapping.raw_susceptibility_code;"
    return text[start : text.index(end_marker, start) + len(end_marker)]


def parser_ctes(text):
    start = text.index("direct_parse AS (")
    end_marker = "FROM normalized\n)"
    return text[start : text.index(end_marker, start) + len(end_marker)]


def geometry_status_case(text):
    start = text.index("WHEN parsed.geometry_text IS NULL THEN 'BLANK_GEOMETRY'")
    end_marker = "END AS source_geometry_status"
    return text[start : text.index(end_marker, start) + len(end_marker)]


def validation_checks():
    return sql(VALIDATION_NOTEBOOK).split("NAMED_STRUCT(\n")[1:]


def check_block(name):
    own = [check for check in validation_checks() if f"'{name}'" in check]
    assert len(own) == 1, name
    return own[0]


def test_01_notebooks_are_valid_nbformat_sql_notebooks():
    for path in (FLOOD_MAP_NOTEBOOK, VALIDATION_NOTEBOOK):
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
            text = "".join(cell["source"])
            assert text.startswith("%sql\n")
            assert cell["outputs"] == []


def test_02_every_code_cell_has_markdown_before_it_and_sections_exist():
    for path in (FLOOD_MAP_NOTEBOOK, VALIDATION_NOTEBOOK):
        cells = notebook(path)["cells"]
        assert cells[0]["cell_type"] == "markdown"
        for index, cell in enumerate(cells):
            if cell["cell_type"] == "code":
                assert cells[index - 1]["cell_type"] == "markdown"
    text = markdown(FLOOD_MAP_NOTEBOOK)
    for heading in [
        "# Silver Table 15: project flood mapping",
        "## Purpose",
        "## Grain",
        "## 1. Confirm upstream safety and select versions",
        "## 2. Prepare canonical project points",
        "## 3. Reuse the governed MGB classification contract",
        "## 4. Build project-to-MGB spatial candidates",
        "## 5. Resolve one final project flood classification",
        "## 6. Build deterministic lineage and publish Table 15",
        "## 7. Inspect compact runtime evidence",
        "# Summary",
    ]:
        assert heading in text
    for label in ["**What:**", "**Why:**", "**Protects:**", "**Expected validation:**"]:
        assert label in text


def test_03_first_sql_uses_the_project_catalog():
    for path in (FLOOD_MAP_NOTEBOOK, VALIDATION_NOTEBOOK):
        first_code = sql(path).split("%sql\n", 1)[1]
        assert first_code.startswith("USE CATALOG `buildabida-capstone`;")


def test_04_creates_target_table_once_as_delta_with_replace():
    text = sql(FLOOD_MAP_NOTEBOOK)
    assert text.count(f"CREATE OR REPLACE TABLE {TABLE}") == 1
    assert "USING DELTA" in publish_select()
    for token in ["DROP TABLE", "INSERT INTO", "MERGE INTO", "TRUNCATE"]:
        assert token not in text.upper()


def test_05_grain_and_uniqueness_are_documented():
    text = squash(markdown(FLOOD_MAP_NOTEBOOK))
    assert (
        "One final project-to-flood classification result per canonical "
        "`silver_project` row per deterministic project-flood mapping run" in text
    )
    assert "Every canonical project produces exactly one row" in text
    assert "`(source_system, contract_id, run_id)`" in text
    doc = squash(CONTRACT_DOC.read_text(encoding="utf-8"))
    assert "`UNIQUE(source_system, contract_id, run_id)`" in doc


def test_06_deterministic_key_uses_source_system_project_and_run():
    select = squash(publish_select())
    assert (
        "SHA2(CONCAT_WS( '|', decision.source_system, decision.project_key, "
        "selected.project_flood_run_id ), 256) AS project_flood_map_key" in select
    )
    assert "selected.project_flood_run_id AS run_id" in select


def test_07_run_id_hashes_every_meaningful_contract_and_no_tuning_knob():
    body = view_body(sql(FLOOD_MAP_NOTEBOOK), "selected_project_flood_versions")
    run_hash = body.split("SHA2(CONCAT_WS(", 1)[1].split("AS project_flood_run_id", 1)[
        0
    ]
    for token in [
        "project_run_id",
        "project_source_snapshot_id",
        "project_source_ingest_run_id",
        "mgb_source_snapshot_id",
        "mgb_source_ingest_run_id",
        "COALESCE(mgb_publisher.mgb_source_version, 'NO_PUBLISHER_VERSION')",
        "susceptibility_mapping_version",
        "mgb_mapping_source_version",
        "classification_rule",
        "classification_rule_version",
    ]:
        assert token in run_hash
    # the grid only changes performance, so it never changes logical identity
    assert "candidate_grid_cell_degrees" not in run_hash


def test_08_no_uuid_random_or_current_time_in_logical_identity():
    code = code_without_comments(FLOOD_MAP_NOTEBOOK).lower()
    for token in [
        "uuid(",
        "rand(",
        "random(",
        "monotonically_increasing_id",
        "current_timestamp",
        "current_date",
        "now()",
    ]:
        assert token not in code
    validation = code_without_comments(VALIDATION_NOTEBOOK).lower()
    for token in ["uuid(", "rand(", "random(", "monotonically_increasing_id"]:
        assert token not in validation


def test_09_rule_version_is_declared_once_and_covers_the_contract():
    code = code_without_comments(FLOOD_MAP_NOTEBOOK)
    assert len(re.findall(r"silver-project-flood-map-v2", code)) == 1
    assert "DECLARE OR REPLACE VARIABLE classification_rule STRING" in code
    rule = squash(code.split("SET VAR classification_rule_version = CONCAT(", 1)[1])
    rule = rule.split(");", 1)[0]
    for token in [
        "silver-project-flood-map-v2|predicate=ST_INTERSECTS",
        "coordinate-screen-latitude=",
        "min_latitude",
        "max_latitude",
        "min_longitude",
        "max_longitude",
    ]:
        assert token in rule
    declared = code.split("DECLARE OR REPLACE VARIABLE classification_rule STRING", 1)
    assert "NO_SEVERITY_PRECEDENCE" in declared[1].split(";", 1)[0]


def test_10_only_active_approved_mgb_mapping_of_one_version_is_used():
    text = sql(FLOOD_MAP_NOTEBOOK)
    body = view_body(text, "approved_mgb_susceptibility_mapping")
    assert "mapping.approval_status = 'APPROVED'" in body
    assert "mapping.is_active = TRUE" in body
    assert "mapping.mapping_version = selected.susceptibility_mapping_version" in body
    assert "COUNT(DISTINCT mapping.mapping_version) = 1" in text
    assert "COUNT(DISTINCT mapping.source_version) = 1" in text
    assert "STOP: approved MGB levels and severity ranks are not one-to-one" in text


def test_11_no_hardcoded_code_mapping_and_no_unknown_level():
    code = code_without_comments(FLOOD_MAP_NOTEBOOK)
    for literal in ["'LF'", "'MF'", "'HF'", "'VHF'", "'Low'", "'Moderate'", "'High'"]:
        assert literal not in code
    assert "'Very High'" not in code
    assert not re.search(r"WHEN\s+'?(LF|MF|HF|VHF)'?\s+THEN", code)
    upper = code.upper()
    assert "UNKNOWN" not in upper
    assert "'NO RATING'" not in upper
    assert "'UNMAPPED'" in upper


def test_12_table_14_parser_is_reused_without_change():
    exposure = classified_view(sql(EXPOSURE_NOTEBOOK))
    flood_map = classified_view(sql(FLOOD_MAP_NOTEBOOK))
    expected = exposure.replace(
        "CROSS JOIN selected_flood_exposure_versions AS selected",
        "CROSS JOIN selected_project_flood_versions AS selected",
    ).replace(
        "mapping.standardized_level AS flood_susceptibility_level,\n",
        "mapping.standardized_level AS flood_susceptibility_level,\n"
        "    mapping.severity_rank,\n",
    )
    assert flood_map == expected


def test_13_validator_reuses_table_14_parser_and_geometry_statuses():
    exposure = sql(EXPOSURE_NOTEBOOK)
    validation = sql(VALIDATION_NOTEBOOK)
    assert parser_ctes(validation) == parser_ctes(exposure)
    assert geometry_status_case(validation) == geometry_status_case(exposure)


def test_14_esri_rings_and_targeted_normalization_paths_are_present():
    text = sql(FLOOD_MAP_NOTEBOOK)
    if "$.rings" in sql(EXPOSURE_NOTEBOOK):
        assert "GET_JSON_OBJECT(esri_ring_parts.geometry_text, '$.rings')" in text
        assert "'ESRI_JSON_CONVERTED'" in text
    assert "TRY_TO_GEOMETRY(geometry_text) AS published_geometry" in text
    assert "'GEOJSON_QUOTED_NUMBERS_NORMALIZED'" in text
    assert (
        "COALESCE(\n            published_geometry,\n            normalized_geometry,\n            esri_geometry\n        )"
        in text
    )
    assert "REPLACE(geometry_text, '\"'" not in text


def test_15_geometry_statuses_follow_table_14_vocabulary():
    text = sql(FLOOD_MAP_NOTEBOOK)
    for status in [
        "BLANK_GEOMETRY",
        "UNPARSEABLE_GEOMETRY",
        "EMPTY_GEOMETRY",
        "UNSUPPORTED_GEOMETRY_TYPE",
        "INVALID_GEOMETRY",
        "USABLE_GEOMETRY",
    ]:
        assert f"'{status}'" in text


def test_16_only_mapped_usable_mgb_geometry_enters_the_spatial_join():
    body = view_body(sql(FLOOD_MAP_NOTEBOOK), "approved_mgb_candidate_cells")
    assert "mgb.susceptibility_mapping_status = 'MAPPED_APPROVED'" in body
    assert "mgb.source_geometry_status = 'USABLE_GEOMETRY'" in body
    assert "FROM mgb_source_classified AS mgb" in body


def test_17_project_points_use_the_table_13_coordinate_contract():
    region_map = sql(REGION_MAP_NOTEBOOK)
    flood_map = sql(FLOOD_MAP_NOTEBOOK)
    for bound, value in [
        ("min_latitude", "4.2"),
        ("max_latitude", "21.3"),
        ("min_longitude", "116.0"),
        ("max_longitude", "127.0"),
    ]:
        assert f"CAST({value} AS DOUBLE) AS {bound}" in region_map
        assert f"DECLARE OR REPLACE VARIABLE {bound} DOUBLE DEFAULT {value};" in (
            flood_map
        )
        assert len(re.findall(rf"\b{re.escape(value)}\b", flood_map)) == 1
    body = view_body(flood_map, "project_flood_input")
    for status in ["MISSING_PAIR", "PARTIAL_PAIR", "OUT_OF_RANGE", "VALID_PAIR"]:
        assert f"'{status}'" in body
        assert f"'{status}'" in region_map
    assert "FROM `02-silver`.silver_project AS project" in body
    assert "project.latitude_parsed" in body
    assert "project.longitude_parsed" in body


def test_18_points_are_only_built_for_safe_coordinates():
    body = view_body(sql(FLOOD_MAP_NOTEBOOK), "project_flood_points")
    assert "ST_POINT(longitude, latitude, source_geometry_srid)" in body
    assert "WHERE coordinate_status = 'VALID_PAIR'" in body
    assert "AND has_valid_identity" in body
    assert sql(FLOOD_MAP_NOTEBOOK).count("ST_POINT(") == 1


def test_19_native_spatial_predicate_with_grid_equality_and_no_cross_join():
    body = squash(view_body(sql(FLOOD_MAP_NOTEBOOK), "project_flood_candidates"))
    assert (
        "FROM project_flood_points AS point INNER JOIN approved_mgb_candidate_cells "
        "AS polygon ON point.grid_x = polygon.grid_x AND point.grid_y = polygon.grid_y "
        "AND ST_INTERSECTS(polygon.mgb_geometry, point.project_point)" in body
    )
    code = code_without_comments(FLOOD_MAP_NOTEBOOK)
    cross_joined = set(re.findall(r"CROSS JOIN\s+([`\w.-]+)", code))
    assert cross_joined <= {
        "selected_project_flood_versions",
        "project_audit",
        "mgb_context",
        "mgb_publisher",
        "mapping_context",
        "latest_project_flood_source_load",
    }
    assert not re.search(r"\bJOIN\b(?<!INNER JOIN)(?<!LEFT JOIN)(?<!CROSS JOIN)", code)
    assert "RIGHT JOIN" not in code.upper()


def test_20_grid_cells_cover_the_whole_bounding_box_with_one_variable():
    code = code_without_comments(FLOOD_MAP_NOTEBOOK)
    body = view_body(code, "approved_mgb_candidate_cells")
    for edge in ["ST_XMIN", "ST_XMAX", "ST_YMIN", "ST_YMAX"]:
        assert f"FLOOR({edge}(mgb.mgb_geometry) / candidate_grid_cell_degrees)" in body
    assert "SEQUENCE(polygon.grid_x_min, polygon.grid_x_max)" in body
    assert "SEQUENCE(polygon.grid_y_min, polygon.grid_y_max)" in body
    points = view_body(code, "project_flood_points")
    assert "FLOOR(longitude / candidate_grid_cell_degrees)" in points
    assert "FLOOR(latitude / candidate_grid_cell_degrees)" in points
    assert len(re.findall(r"DEFAULT 0\.1;", code)) == 1


def test_21_no_python_geopandas_udf_or_spatial_library():
    for path in (FLOOD_MAP_NOTEBOOK, VALIDATION_NOTEBOOK):
        code = code_without_comments(path).lower()
        for token in [
            "pandas",
            "geopandas",
            "shapely",
            "udf",
            "create function",
            "create temporary function",
            "%python",
            "import ",
            "pyspark",
            "collect()",
            "topandas",
        ]:
            assert token not in code


def test_22_no_nearest_polygon_buffer_or_repair():
    for path in (FLOOD_MAP_NOTEBOOK, VALIDATION_NOTEBOOK):
        code = code_without_comments(path).upper()
        for token in [
            "ST_BUFFER",
            "ST_MAKEVALID",
            "ST_DISTANCE",
            "ST_DWITHIN",
            "NEAREST",
            "ST_CLOSESTPOINT",
        ]:
            assert token not in code


def test_23_candidates_are_aggregated_once_before_publish():
    code = code_without_comments(FLOOD_MAP_NOTEBOOK)
    body = view_body(code, "project_flood_candidates")
    assert "GROUP BY point.project_key" in body
    # each expensive view is defined once and consumed once, so the spatial join runs once
    for view in [
        "project_flood_candidates",
        "approved_mgb_candidate_cells",
        "project_flood_decisions",
    ]:
        assert len(re.findall(rf"\b{view}\b", code)) == 2, view
    assert len(re.findall(r"\bmgb_source_classified\b", code)) == 3
    assert "CACHE" not in code.upper()
    assert "REPARTITION" not in code.upper()


def test_24_final_output_keeps_every_canonical_project():
    code = code_without_comments(FLOOD_MAP_NOTEBOOK)
    body = squash(view_body(code, "project_flood_decisions"))
    assert (
        "FROM project_flood_input AS project LEFT JOIN project_flood_candidates "
        "AS candidate ON project.project_key = candidate.project_key" in body
    )
    assert "COALESCE(candidate.matched_polygon_count, 0)" in body
    statement = publish_select().split(";", 1)[0]
    assert "FROM project_flood_decisions AS decision" in statement
    assert "WHERE" not in statement.upper()


def test_25_unique_level_rule_matches_same_level_overlap_and_flags_distinct_levels():
    code = code_without_comments(FLOOD_MAP_NOTEBOOK)
    candidates = squash(view_body(code, "project_flood_candidates"))
    assert "COUNT(*) AS matched_polygon_count" in candidates
    assert (
        "COUNT(DISTINCT polygon.flood_susceptibility_level) AS matched_level_count"
        in candidates
    )
    assert (
        "WHEN COUNT(DISTINCT polygon.flood_susceptibility_level) = 1 THEN "
        "ELEMENT_AT(SORT_ARRAY(COLLECT_SET(polygon.flood_susceptibility_level)), 1)"
        in candidates
    )
    decisions = squash(view_body(code, "project_flood_decisions"))
    assert "WHEN evidence.matched_level_count = 1 THEN 'MATCHED'" in decisions
    assert "WHEN evidence.matched_level_count > 1 THEN 'AMBIGUOUS'" in decisions
    assert (
        "WHEN classified.match_status = 'MATCHED' THEN "
        "classified.unique_flood_susceptibility_level" in decisions
    )
    assert (
        "WHEN classified.match_status = 'AMBIGUOUS' THEN "
        "'MULTIPLE_APPROVED_FLOOD_LEVELS'" in decisions
    )


def test_26_no_severity_precedence_shortcut_resolves_ambiguity():
    for path in (FLOOD_MAP_NOTEBOOK, VALIDATION_NOTEBOOK):
        code = squash(code_without_comments(path)).upper()
        for pattern in [
            r"(MAX|MIN|GREATEST|LEAST|MAX_BY|MIN_BY|FIRST|LAST)\([^)]*SEVERITY_RANK",
            r"ORDER BY [\w.]*SEVERITY_RANK DESC",
            r"ROW_NUMBER\(\) OVER \([^)]*SEVERITY",
            r"ARRAY_MAX|ARRAY_MIN",
        ]:
            assert not re.search(pattern, code), pattern


def test_27_controlled_statuses_methods_qualities_and_reasons():
    code = code_without_comments(FLOOD_MAP_NOTEBOOK)
    for value in [
        "MATCHED",
        "AMBIGUOUS",
        "UNMATCHED",
        "INVALID_SOURCE",
        "COORDINATE_MGB_POLYGON",
        "NONE",
        "SPATIAL",
        "REVIEW_REQUIRED",
        "UNRESOLVED",
        "MULTIPLE_APPROVED_FLOOD_LEVELS",
        "MISSING_COORDINATE_PAIR",
        "PARTIAL_COORDINATE_PAIR",
        "COORDINATE_OUT_OF_RANGE",
        "NO_APPROVED_MGB_INTERSECTION",
        "MISSING_STABLE_SOURCE_IDENTITY",
    ]:
        assert f"'{value}'" in code
    validation = sql(VALIDATION_NOTEBOOK)
    for value in ["'MATCHED', 'AMBIGUOUS', 'UNMATCHED', 'INVALID_SOURCE'"]:
        assert value in validation


def test_28_no_forbidden_data_dependencies():
    for path in (FLOOD_MAP_NOTEBOOK, VALIDATION_NOTEBOOK):
        code = code_without_comments(path).lower()
        for token in [
            "03-gold",
            "dim_flood_susceptibility",
            "fact_project_snapshot",
            "flood_susceptibility_key",
            "population",
            "census",
            "table_c",
            "flood_control_projects",
            "silver_flood_control_component",
            "silver_project_source_match",
            "silver_project_region_map",
            "silver_region_flood_exposure",
            "`01-bronze`.dpwh_projects",
            "/volumes/",
        ]:
            assert token not in code, token


def test_29_reads_only_allowed_tables():
    allowed = {
        "`02-silver`.silver_project",
        "`01-bronze`.flood_susceptibility",
        "`02-silver`.config_mgb_susceptibility_mapping",
        "`01-bronze`.load_log",
        "`04-validation`.dq_results",
        "`04-validation`.silver_config_dq_results",
        "`04-validation`.silver_dq_results",
        TABLE,
    }
    for path in (FLOOD_MAP_NOTEBOOK, VALIDATION_NOTEBOOK):
        tables = set(re.findall(r"`\d\d-[a-z]+`\.\w+", code_without_comments(path)))
        assert tables <= allowed, tables - allowed


def test_30_upstream_safety_uses_newest_terminal_load_and_validation():
    code = sql(FLOOD_MAP_NOTEBOOK)
    assert "WHERE table_name IN ('flood_susceptibility', 'dpwh_projects')" in code
    assert "status IN ('STARTED', 'SUCCESS', 'FAILED', 'SKIPPED_IDEMPOTENT')" in code
    assert "COUNT_IF(status IN ('SUCCESS', 'SKIPPED_IDEMPOTENT')) = 2" in code
    for view in [
        "latest_project_flood_bronze_validation",
        "selected_project_validation",
        "latest_config_validation",
    ]:
        assert view in code
    assert "built from the latest validated DPWH snapshot" in code
    assert "STOP: current MGB Bronze rows do not match the validated MGB snapshot" in (
        code
    )


def test_31_mgb_source_accounting_is_enforced_in_both_notebooks():
    flood_map = sql(FLOOD_MAP_NOTEBOOK)
    assert "'STOP: MGB source-row accounting does not reconcile'" in flood_map
    assert "accounting.selected_mgb_rows = accounting.audited_rows_loaded" in flood_map
    for bucket in [
        "mapped_usable_rows",
        "mapped_unusable_rows",
        "unmapped_usable_rows",
        "unmapped_unusable_rows",
    ]:
        assert f"accounting.{bucket}" in flood_map
    check = check_block("MGB source rows reconcile to mapping and geometry buckets")
    assert "'action', 'stop'" in check
    assert "latest_mgb_rows_loaded" in check


def test_32_no_hardcoded_runtime_counts_decide_correctness():
    flood_map = code_without_comments(FLOOD_MAP_NOTEBOOK)
    for count in ["63684", "63,684", "1815", "265661", "215139", "50522"]:
        assert count not in flood_map
    validation = code_without_comments(VALIDATION_NOTEBOOK)
    assert "DECLARE OR REPLACE VARIABLE reference_mgb_rows BIGINT DEFAULT 63684" in (
        validation
    )
    reference = check_block(
        "Runtime MGB counts are compared with historical Bronze references"
    )
    assert "'action', 'flag'" in reference
    for check in validation_checks():
        if "reference_mgb_rows" in check or "reference_blank_geometry_rows" in check:
            assert "'action', 'flag'" in check


def test_33_published_output_contract_and_lineage():
    select = publish_select()
    for column in [
        "AS project_flood_map_key",
        "decision.source_system",
        "decision.project_key",
        "decision.contract_id",
        "decision.latitude",
        "decision.longitude",
        "decision.coordinate_status",
        "decision.flood_susceptibility_level",
        "decision.severity_rank",
        "decision.match_status",
        "decision.match_method",
        "decision.match_quality",
        "AS INT) AS matched_polygon_count",
        "AS INT) AS matched_level_count",
        "decision.candidate_levels",
        "decision.ambiguity_reason",
        "decision.exception_reason",
        "selected.classification_rule,",
        "selected.classification_rule_version",
        "selected.project_source_snapshot_id",
        "selected.project_source_ingest_run_id",
        "selected.project_source_version",
        "selected.project_run_id",
        "selected.project_rule_version",
        "selected.project_source_load_ts",
        "selected.mgb_source_snapshot_id",
        "selected.mgb_source_ingest_run_id",
        "selected.mgb_source_version",
        "selected.mgb_source_load_ts",
        "selected.susceptibility_mapping_version",
        "selected.mgb_mapping_source_version",
        "AS run_id",
        "AS source_load_ts",
    ]:
        assert column in select, column


def test_34_publisher_versions_come_only_from_load_log():
    body = view_body(sql(FLOOD_MAP_NOTEBOOK), "selected_project_flood_versions")
    assert "MAX(NULLIF(TRIM(log.source_version), '')) AS mgb_source_version" in body
    assert "MAX(NULLIF(TRIM(log.source_version), '')) AS project_source_version" in body
    assert body.count("FROM `01-bronze`.load_log AS log") == 2
    check = check_block(
        "Publisher versions come only from load_log and are never fabricated"
    )
    assert "'action', 'stop'" in check


def test_35_validator_covers_all_seven_attributes_with_stop_checks():
    checks = validation_checks()
    for attribute in ATTRIBUTES:
        own = [check for check in checks if f"'attribute', '{attribute}'" in check]
        assert len(own) >= 2, attribute
        assert any("'action', 'stop'" in check for check in own), attribute
    assert "UNION ALL" not in sql(VALIDATION_NOTEBOOK)
    assert "SELECT INLINE(ARRAY(" in sql(VALIDATION_NOTEBOOK)


def test_36_validator_recomputes_spatial_evidence_independently():
    validation = code_without_comments(VALIDATION_NOTEBOOK)
    candidates = squash(view_body(validation, "project_flood_validation_candidates"))
    assert "ST_INTERSECTS(polygon.mgb_geometry, point.project_point)" in candidates
    assert "susceptibility_mapping_status = 'MAPPED_APPROVED'" in candidates
    assert "source_geometry_status = 'USABLE_GEOMETRY'" in candidates
    assert "expected_coordinate_status = 'VALID_PAIR'" in candidates
    grid = re.search(
        r"validation_grid_cell_degrees DOUBLE DEFAULT ([0-9.]+);", validation
    ).group(1)
    transform = re.search(
        r"candidate_grid_cell_degrees DOUBLE DEFAULT ([0-9.]+);",
        code_without_comments(FLOOD_MAP_NOTEBOOK),
    ).group(1)
    assert float(grid) != float(transform)
    for name in [
        "Published candidate evidence equals an independent spatial recomputation",
        "Matched project points intersect at least one approved usable polygon",
        "Multiple distinct levels are never collapsed by severity",
        "Same-level overlapping polygons resolve to one level and keep their count",
        "Blank, No rating, and unapproved codes never drive a classification",
        "Published coordinates and statuses follow the Table 13 contract",
        "Only safe coordinates take part in spatial matching",
    ]:
        assert "'action', 'stop'" in check_block(name), name


def test_37_validator_declares_the_coordinate_screen_independently():
    validation = code_without_comments(VALIDATION_NOTEBOOK)
    for bound, value in [
        ("expected_min_latitude", "4.2"),
        ("expected_max_latitude", "21.3"),
        ("expected_min_longitude", "116.0"),
        ("expected_max_longitude", "127.0"),
    ]:
        assert f"DECLARE OR REPLACE VARIABLE {bound} DOUBLE DEFAULT {value};" in (
            validation
        )
    points = view_body(validation, "project_flood_validation_points")
    assert "FROM `02-silver`.silver_project AS project" in points
    assert "silver_project_flood_map" not in points


def test_38_validation_status_and_completeness_checks_exist():
    for name, action in [
        ("Every canonical project has exactly one output row", "stop"),
        ("Project flood map keys are unique", "stop"),
        ("One row exists per source system, Contract ID, and run", "stop"),
        ("No project fans out into more than one row", "stop"),
        ("Matched rows publish exactly one distinct candidate level", "stop"),
        ("Ambiguous rows publish multiple candidate levels and no final level", "stop"),
        ("Unmatched and invalid rows publish no level, rank, or candidate", "stop"),
        ("Published levels and ranks match the approved configuration", "stop"),
        (
            "Run ID reproduces from published project, MGB, mapping, and rule lineage",
            "stop",
        ),
        ("Published project snapshot is the latest validated DPWH snapshot", "stop"),
        ("Published MGB snapshot is the latest validated MGB snapshot", "stop"),
        ("Flood classification coverage is reported against all projects", "flag"),
        (
            "Flood classification coverage is reported against usable coordinates",
            "flag",
        ),
        ("Projects without usable coordinates remain present", "flag"),
        ("Usable points without an approved MGB intersection remain visible", "flag"),
        (
            "Projects across multiple approved levels remain ambiguous and visible",
            "flag",
        ),
        ("Projects inside several same-level polygons remain visible", "flag"),
        ("Unmapped or unrated MGB rows remain visible", "flag"),
        ("Invalid MGB geometry is excluded without repair", "flag"),
        ("Optional MGB publisher version gaps remain visible", "flag"),
    ]:
        assert f"'action', '{action}'" in check_block(name), name


def test_39_every_flag_has_a_denominator():
    for check in validation_checks():
        if "'action', 'flag'" in check:
            total = check.split("'total_rows',", 1)[1].split("'action'", 1)[0]
            assert "CAST(" in total
            assert "CAST(0 AS BIGINT)" not in total


def test_40_validation_results_persist_before_stop_gate():
    validation = sql(VALIDATION_NOTEBOOK)
    merge = validation.index("MERGE INTO `04-validation`.silver_dq_results")
    gate = validation.index("SELECT ASSERT_TRUE")
    assert merge < gate
    gate_sql = validation[gate:]
    assert "FROM `04-validation`.silver_dq_results" in gate_sql
    assert "table_name = 'silver_project_flood_map'" in gate_sql
    assert "validation_run_id = project_flood_validation_run_id" in gate_sql
    assert (
        "SHA2(CONCAT_WS('|', run_id, validation_rule_version), 256) AS validation_run_id"
        in validation
    )
    assert "silver-project-flood-map-validation-v1" in validation


def test_41_docs_mark_table_15_implemented_and_gold_status():
    contract = CONTRACT_DOC.read_text(encoding="utf-8")
    for phrase in [
        "`02-silver.silver_project_flood_map`",
        "MULTIPLE_APPROVED_FLOOD_LEVELS",
        "NO_APPROVED_MGB_INTERSECTION",
        "no severity precedence",
        "## Gold handoff",
        "## Known limitations",
    ]:
        assert phrase in contract
    for temporary in ["this PR", "once this branch", "waiting for approval"]:
        assert temporary not in contract
    data_model = (ROOT / "docs/data-model.md").read_text(encoding="utf-8")
    assert "Project-flood mapping remains planned" not in data_model
    assert "| Gold | Planned |" not in data_model
    assert "| Gold | Partially implemented |" in data_model
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Project-flood mapping and Gold remain planned" not in readme
    assert "Gold remains planned" not in readme
    assert "The six Gold dimensions are implemented" in readme
    for path in ["notebooks/README.md", "docs/validation.md", "docs/README.md"]:
        assert "silver_project_flood_map" in (ROOT / path).read_text(encoding="utf-8")


def test_42_summary_documents_contract_and_runtime_boundary():
    summary = markdown(FLOOD_MAP_NOTEBOOK).split("# Summary", 1)[1]
    for phrase in [
        "**Grain:**",
        "**Primary key:**",
        "**Source dependencies:**",
        "**Classification behavior:**",
        "**Ambiguity behavior:**",
        "**Idempotency:**",
        "**Validation handoff:**",
        "**Gold dependency:**",
        "**Known limitations:**",
        "requires Databricks execution",
    ]:
        assert phrase in summary
