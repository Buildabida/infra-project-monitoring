import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPOSURE_NOTEBOOK = ROOT / "notebooks/02_silver/09_silver_region_flood_exposure.ipynb"
VALIDATION_NOTEBOOK = (
    ROOT / "notebooks/04_validation/07_validation_silver_region_flood_exposure.ipynb"
)
TABLE = "`02-silver`.silver_region_flood_exposure"


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


def publish_select():
    return sql(EXPOSURE_NOTEBOOK).split(f"CREATE OR REPLACE TABLE {TABLE}", 1)[1]


def view_body(text, view):
    start = text.index(f"CREATE OR REPLACE TEMPORARY VIEW {view} AS")
    end = text.find("CREATE OR REPLACE", start + 1)
    return text[start : end if end > 0 else len(text)]


def test_01_notebooks_are_valid_nbformat_sql_notebooks():
    for path in (EXPOSURE_NOTEBOOK, VALIDATION_NOTEBOOK):
        nb = notebook(path)
        assert nb["nbformat"] == 4
        assert nb["nbformat_minor"] >= 5
        meta = nb["metadata"]["application/vnd.databricks.v1+notebook"]
        assert meta["language"] == "sql"
        assert meta["notebookName"] == path.stem
        code_cells = [cell for cell in nb["cells"] if cell["cell_type"] == "code"]
        assert code_cells
        assert all("".join(cell["source"]).startswith("%sql\n") for cell in code_cells)


def test_02_creates_silver_region_flood_exposure_as_delta_with_replace():
    text = sql(EXPOSURE_NOTEBOOK)
    assert text.count(f"CREATE OR REPLACE TABLE {TABLE}") == 1
    assert "USING DELTA" in publish_select()
    assert "DROP TABLE" not in text.upper()
    assert "INSERT INTO" not in text.upper()


def test_03_reads_bronze_mgb_for_selected_snapshot():
    text = sql(EXPOSURE_NOTEBOOK)
    assert "FROM `01-bronze`.flood_susceptibility AS mgb" in text
    assert "mgb._source_snapshot_id = selected.mgb_source_snapshot_id" in text
    assert "mgb.flood_susceptibility_code" in text
    assert "mgb.geometry_json" in text


def test_04_reads_bronze_boundaries_for_selected_snapshot():
    text = sql(EXPOSURE_NOTEBOOK)
    assert "FROM `01-bronze`.boundaries AS boundary" in text
    assert "boundary._source_snapshot_id = selected.boundary_source_snapshot_id" in text


def test_05_reads_official_regions_from_silver_psgc_place():
    body = view_body(sql(EXPOSURE_NOTEBOOK), "official_flood_exposure_regions")
    assert "FROM `02-silver`.silver_psgc_place" in body
    assert "WHERE place_type = 'REGION'" in body


def test_06_reads_mgb_mapping_config():
    text = sql(EXPOSURE_NOTEBOOK)
    assert "`02-silver`.config_mgb_susceptibility_mapping" in text


def test_07_consumes_only_active_approved_mapping_of_selected_version():
    body = view_body(sql(EXPOSURE_NOTEBOOK), "approved_mgb_susceptibility_mapping")
    assert "mapping.approval_status = 'APPROVED'" in body
    assert "mapping.is_active = TRUE" in body
    assert "mapping.mapping_version = selected.susceptibility_mapping_version" in body


def test_08_no_hardcoded_mgb_code_mapping():
    code = code_without_comments(EXPOSURE_NOTEBOOK)
    for literal in ["'LF'", "'MF'", "'HF'", "'VHF'", "'Low'", "'Moderate'", "'High'"]:
        assert literal not in code
    assert "'Very High'" not in code
    assert not re.search(r"WHEN\s+'?(LF|MF|HF|VHF)'?\s+THEN", code)


def test_09_blank_and_no_rating_are_never_mapped_to_unknown():
    code = code_without_comments(EXPOSURE_NOTEBOOK).upper()
    assert "UNKNOWN" not in code
    assert "'NO RATING'" not in code
    assert "'UNMAPPED'" in code


def test_10_no_dpwh_bronze_read():
    code = code_without_comments(EXPOSURE_NOTEBOOK).lower()
    assert "dpwh_projects" not in code
    assert "silver_dpwh_project_component" not in code


def test_11_no_silver_project_read():
    code = code_without_comments(EXPOSURE_NOTEBOOK).lower()
    assert re.search(r"\bsilver_project\b", code) is None
    assert "silver_project_source_match" not in code


def test_12_no_table_13_dependency():
    for path in (EXPOSURE_NOTEBOOK, VALIDATION_NOTEBOOK):
        assert "silver_project_region_map" not in code_without_comments(path).lower()


def test_13_no_flood_control_project_read():
    code = code_without_comments(EXPOSURE_NOTEBOOK).lower()
    assert "flood_control_projects" not in code
    assert "silver_flood_control_component" not in code


def test_14_no_census_or_table_c_read():
    code = code_without_comments(EXPOSURE_NOTEBOOK).lower()
    assert "census" not in code
    assert "table_c" not in code


def test_15_no_population_read():
    code = code_without_comments(EXPOSURE_NOTEBOOK).lower()
    assert "silver_region_population" not in code
    assert "population" not in code


def test_16_no_gold_read_or_write():
    for path in (EXPOSURE_NOTEBOOK, VALIDATION_NOTEBOOK):
        code = code_without_comments(path).lower()
        assert "03-gold" not in code
        assert "fact_region_flood_exposure" not in code
        assert "dim_flood_susceptibility" not in code


def test_17_table_15_is_not_implemented():
    for path in (EXPOSURE_NOTEBOOK, VALIDATION_NOTEBOOK):
        assert "silver_project_flood_map" not in code_without_comments(path).lower()
    assert not (ROOT / "notebooks/02_silver/10_silver_project_flood_map.ipynb").exists()


def test_18_complete_region_by_level_grid_is_built_from_dynamic_sets():
    body = view_body(sql(EXPOSURE_NOTEBOOK), "region_flood_exposure_grid")
    assert "FROM official_flood_exposure_regions AS region" in body
    assert "CROSS JOIN approved_susceptibility_levels AS level" in body
    assert "LEFT JOIN region_level_exposure_area AS exposure" in body
    assert "FROM region_flood_exposure_grid AS grid" in publish_select()


def test_19_official_region_count_is_dynamic():
    for path in (EXPOSURE_NOTEBOOK, VALIDATION_NOTEBOOK):
        code = code_without_comments(path)
        assert not re.search(r"(=|<>|>|<)\s*(17|18)\b(?!,)", code)
        assert not re.search(r"\b(17|18)\s*\*", code)
    validation = sql(VALIDATION_NOTEBOOK)
    assert "COUNT(*) AS official_region_count" in validation


def test_20_susceptibility_level_count_is_dynamic():
    for path in (EXPOSURE_NOTEBOOK, VALIDATION_NOTEBOOK):
        code = code_without_comments(path)
        assert not re.search(r"\b72\b", code)
        assert not re.search(r"level_count\s*=\s*4\b", code)
    validation = sql(VALIDATION_NOTEBOOK)
    assert "(SELECT COUNT(*) FROM expected_grid) AS expected_grid_rows" in validation
    assert "CROSS JOIN approved_levels AS level" in validation


def test_21_deterministic_exposure_key_uses_region_level_and_run():
    assert (
        "SHA2(CONCAT_WS(\n        '|', grid.psgc_region_code, grid.flood_susceptibility_level, "
        "selected.exposure_run_id\n    ), 256) AS region_flood_exposure_key"
    ) in publish_select()


def test_22_deterministic_run_id_hashes_every_contract_domain():
    body = view_body(sql(EXPOSURE_NOTEBOOK), "selected_flood_exposure_versions")
    run_hash = body.split("SHA2(CONCAT_WS(", 1)[1].split("AS exposure_run_id", 1)[0]
    for token in [
        "mgb_source_snapshot_id",
        "mgb_source_ingest_run_id",
        "'NO_PUBLISHER_VERSION'",
        "susceptibility_mapping_version",
        "mgb_mapping_source_version",
        "boundary_source_snapshot_id",
        "boundary_source_ingest_run_id",
        "boundary_version",
        "psgc_source_snapshot_id",
        "psgc_run_id",
        "psgc_version",
        "area_calculation_crs",
        "area_rule_version",
        "transformation_rule_version",
    ]:
        assert token in run_hash


def test_23_no_uuid_or_random_identity():
    for path in (EXPOSURE_NOTEBOOK, VALIDATION_NOTEBOOK):
        code = code_without_comments(path).lower()
        for token in ["uuid(", "rand(", "random(", "monotonically_increasing_id"]:
            assert token not in code


def test_24_no_current_time_in_exposure_identity():
    code = code_without_comments(EXPOSURE_NOTEBOOK).lower()
    assert "current_date" not in code
    assert "current_timestamp" not in code
    assert "now()" not in code


def test_25_area_crs_is_declared_once_and_reused():
    code = code_without_comments(EXPOSURE_NOTEBOOK)
    assert len(re.findall(r"\b6933\b", code)) == 1
    assert "DECLARE OR REPLACE VARIABLE area_calculation_srid INT DEFAULT 6933" in code
    assert (
        "SET VAR area_calculation_crs = CONCAT('EPSG:', area_calculation_srid)" in code
    )
    assert "area_calculation_crs" in view_body(code, "selected_flood_exposure_versions")
    assert "selected.area_calculation_crs" in publish_select()
    assert "selected.area_rule_version" in publish_select()


def test_26_area_is_only_measured_on_projected_geometry():
    code = code_without_comments(EXPOSURE_NOTEBOOK)
    areas = re.findall(r"ST_AREA\(([^)]*)", code)
    assert areas
    for argument in areas:
        assert argument.startswith(("ST_TRANSFORM(", "projected_")), argument
    assert code.count("ST_TRANSFORM(") >= 3
    assert "/ square_metres_per_sqkm" in code


def test_27_native_spatial_intersection_only_for_intersecting_pairs():
    body = view_body(sql(EXPOSURE_NOTEBOOK), "region_mgb_intersection_fragments")
    assert "ON ST_INTERSECTS(region.boundary_geometry, mgb.mgb_geometry)" in body
    assert (
        "ST_INTERSECTION(region.boundary_geometry, mgb.mgb_geometry) AS fragment_geometry"
        in body
    )
    assert "BROADCAST(region)" in body


def test_28_only_region_level_boundaries_drive_the_spatial_join():
    code = code_without_comments(EXPOSURE_NOTEBOOK)
    assert "LOWER(TRIM(boundary.administrative_level)) = 'region'" in code
    for level in ["'barangay'", "'province'", "'municipality'", "'city'"]:
        assert level not in code.lower()
    body = view_body(code, "region_mgb_intersection_fragments")
    assert "INNER JOIN safe_region_boundaries AS region" in body
    assert "`01-bronze`.boundaries" not in body


def test_29_no_python_pandas_geopandas_shapely_or_udf():
    for path in (EXPOSURE_NOTEBOOK, VALIDATION_NOTEBOOK):
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
        ]:
            assert token not in code


def test_30_mgb_source_row_accounting_is_enforced_in_both_notebooks():
    exposure = sql(EXPOSURE_NOTEBOOK)
    assert "'STOP: MGB source-row accounting does not reconcile'" in exposure
    assert "accounting.selected_mgb_rows = accounting.audited_rows_loaded" in exposure
    for bucket in [
        "mapped_usable_rows",
        "mapped_unusable_rows",
        "unmapped_usable_rows",
        "unmapped_unusable_rows",
    ]:
        assert f"accounting.{bucket}" in exposure
    validation = sql(VALIDATION_NOTEBOOK)
    assert "MGB source rows reconcile to mapping and geometry buckets" in validation
    assert (
        "ABS(mgb_rows - mapped_usable_rows - mapped_unusable_rows - unmapped_usable_rows - unmapped_unusable_rows)"
        in validation
    )


def test_31_zero_versus_no_data_semantics_are_built_and_validated():
    select = publish_select()
    assert "CASE WHEN grid.has_safe_boundary" in select
    assert "COALESCE(grid.susceptible_area_sqkm_unrounded, 0)" in select
    assert "'NO_SAFE_REGION_BOUNDARY'" in select
    assert "'NO_MAPPED_EXPOSURE'" in select
    validation = sql(VALIDATION_NOTEBOOK)
    assert "Missing geography is published as NULL, never zero" in validation
    assert "Safe regions without exposure are published as real zero" in validation


def test_32_output_grain_and_grid_validation_exist():
    validation = sql(VALIDATION_NOTEBOOK)
    assert "Every official region and approved level has exactly one output row" in (
        validation
    )
    assert "One row exists per region, level, and run" in validation
    assert "Region flood exposure keys are unique" in validation


def test_33_percentage_range_validation_exists():
    validation = sql(VALIDATION_NOTEBOOK)
    assert "published.share_of_region_area_pct < 0" in validation
    assert "published.share_of_region_area_pct > 100" in validation
    assert "Share of region area is between 0 and 100" in validation


def test_34_non_negative_and_positive_area_validation_exists():
    validation = sql(VALIDATION_NOTEBOOK)
    assert "published.susceptible_area_sqkm < 0" in validation
    assert "published.region_area_sqkm <= 0" in validation
    assert "Susceptible area is non-negative" in validation
    assert "Calculated region area is positive" in validation


def test_35_region_denominator_consistency_check_exists():
    validation = sql(VALIDATION_NOTEBOOK)
    assert "COUNT(DISTINCT region_area_sqkm) AS region_area_values" in validation
    assert "Each region uses one area denominator across levels" in validation


def test_36_within_level_overlap_is_dissolved_and_checked():
    exposure = sql(EXPOSURE_NOTEBOOK)
    assert "ST_UNION_AGG(fragment_geometry) AS dissolved_geometry" in exposure
    assert "fragment_area_sum_sqkm - dissolved_area_sqkm" in exposure
    validation = sql(VALIDATION_NOTEBOOK)
    assert "Dissolve never increases area within a level" in validation
    assert "Within-level source overlap removed by dissolve remains visible" in (
        validation
    )


def test_37_cross_level_overlap_is_measured_without_severity_precedence():
    exposure = code_without_comments(EXPOSURE_NOTEBOOK)
    assert (
        "GROUP BY GROUPING SETS ((psgc_region_code, flood_susceptibility_level), (psgc_region_code))"
        in exposure
    )
    assert "'NON_ADDITIVE_CROSS_LEVEL_OVERLAP'" in exposure
    assert not re.search(r"ORDER BY\s+severity_rank\s+DESC", exposure)
    assert "ST_DIFFERENCE" not in exposure
    validation = sql(VALIDATION_NOTEBOOK)
    assert "Cross-level overlap between approved levels remains visible" in validation
    assert "Cross-level additivity status matches measured overlap" in validation


def test_38_boundary_version_mismatch_remains_visible():
    select = publish_select()
    assert "'VERSION_MISMATCH_VISIBLE'" in select
    assert "selected.boundary_psgc_version" in select
    assert "selected.psgc_version" in select
    assert "Boundary and PSGC version differences remain visible" in sql(
        VALIDATION_NOTEBOOK
    )


def test_39_no_hardcoded_nir_correction_or_region_codes():
    for path in (EXPOSURE_NOTEBOOK, VALIDATION_NOTEBOOK):
        code = code_without_comments(path).upper()
        assert "NEGROS" not in code
        assert " NIR" not in code
        assert not re.search(r"'[0-9]{10}'", code)


def test_40_barmm_is_not_excluded():
    for path in (EXPOSURE_NOTEBOOK, VALIDATION_NOTEBOOK):
        code = code_without_comments(path).upper()
        assert "BARMM" not in code
        assert "BANGSAMORO" not in code
    assert "BARMM stays in scope" in markdown(EXPOSURE_NOTEBOOK)


def test_41_unmapped_susceptibility_rows_remain_visible_in_validation():
    validation = sql(VALIDATION_NOTEBOOK)
    assert "Unmapped or unrated MGB rows remain visible" in validation
    assert "raw_susceptibility_code = 'NO RATING'" in validation
    assert "raw_susceptibility_code = '<BLANK>'" in validation


def test_42_lineage_is_published_and_checked():
    select = publish_select()
    for column in [
        "mgb_source_snapshot_id",
        "mgb_source_ingest_run_id",
        "mgb_source_version",
        "mgb_source_load_ts",
        "mgb_mapping_source_version",
        "susceptibility_mapping_version",
        "boundary_source_snapshot_id",
        "boundary_source_ingest_run_id",
        "boundary_source_system",
        "boundary_psgc_version",
        "boundary_version",
        "boundary_source_load_ts",
        "psgc_source_snapshot_id",
        "psgc_source_ingest_run_id",
        "psgc_version",
        "psgc_run_id",
        "psgc_source_load_ts",
        "area_calculation_crs",
        "area_rule_version",
        "AS run_id",
        "AS source_load_ts",
    ]:
        assert column in select
    assert (
        "Mandatory snapshot, mapping, boundary, PSGC, CRS, rule, and run lineage"
        in (sql(VALIDATION_NOTEBOOK))
    )


def test_43_all_seven_attributes_have_executable_checks():
    checks = sql(VALIDATION_NOTEBOOK).split("NAMED_STRUCT(")[1:]
    for attribute in [
        "Consistency",
        "Accuracy",
        "Completeness",
        "Auditability",
        "Validity",
        "Uniqueness",
        "Timeliness",
    ]:
        own = [check for check in checks if f"'attribute', '{attribute}'" in check]
        assert len(own) >= 2
        assert any("'action', 'stop'" in check for check in own)


def test_44_validation_results_persist_before_stop_gate():
    validation = sql(VALIDATION_NOTEBOOK)
    merge = validation.index("MERGE INTO `04-validation`.silver_dq_results")
    gate = validation.index("SELECT ASSERT_TRUE")
    assert merge < gate
    gate_sql = validation[gate:]
    assert "FROM `04-validation`.silver_dq_results" in gate_sql
    assert "table_name = 'silver_region_flood_exposure'" in gate_sql


def test_45_every_major_code_section_has_markdown_before_it():
    cells = notebook(EXPOSURE_NOTEBOOK)["cells"]
    for index, cell in enumerate(cells):
        if cell["cell_type"] == "code":
            assert cells[index - 1]["cell_type"] == "markdown"
    text = markdown(EXPOSURE_NOTEBOOK)
    for heading in [
        "## Purpose",
        "## Grain",
        "## Source authority",
        "## 1. Confirm upstream source safety",
        "## 2. Select deterministic source and mapping versions",
        "## 3. Profile MGB susceptibility and geometry",
        "## 4. Prepare active approved susceptibility mapping",
        "## 5. Prepare official PSGC region set",
        "## 6. Prepare safe region boundary geometry",
        "## 7. Parse and validate MGB geometry",
        "## 8. Perform region × MGB spatial intersection",
        "## 9. Dissolve exposure geometry by region and level",
        "## 10. Calculate projected area measures",
        "## 11. Build complete region × level output grid",
        "## 12. Publish `silver_region_flood_exposure`",
        "# Summary",
    ]:
        assert heading in text
    validation_cells = notebook(VALIDATION_NOTEBOOK)["cells"]
    for index, cell in enumerate(validation_cells):
        if cell["cell_type"] == "code":
            assert validation_cells[index - 1]["cell_type"] == "markdown"


def test_46_final_summary_documents_contract_and_runtime_boundary():
    summary = markdown(EXPOSURE_NOTEBOOK).split("# Summary", 1)[1]
    for phrase in [
        "**Grain:**",
        "**Primary key:**",
        "**MGB mapping version:**",
        "**Boundary version:**",
        "**PSGC version:**",
        "**CRS used:**",
        "**Area rule version:**",
        "**Missing boundary behavior:**",
        "**Unmapped MGB behavior:**",
        "**Source row accounting:**",
        "**Gold dependency:**",
        "requires Databricks execution",
    ]:
        assert phrase in summary


def test_47_upstream_safety_uses_newest_terminal_load_and_validation_evidence():
    code = sql(EXPOSURE_NOTEBOOK)
    assert "status IN ('STARTED', 'SUCCESS', 'FAILED', 'SKIPPED_IDEMPOTENT')" in code
    assert "COUNT_IF(status IN ('SUCCESS', 'SKIPPED_IDEMPOTENT')) = 2" in code
    for view in [
        "latest_flood_exposure_bronze_validation",
        "selected_psgc_validation",
        "latest_config_validation",
    ]:
        assert view in code
    assert "/Volumes/" not in code


def test_48_multiple_active_mapping_versions_stop_the_run():
    code = sql(EXPOSURE_NOTEBOOK)
    assert "COUNT(DISTINCT mapping.mapping_version) = 1" in code
    assert "COUNT(*) = COUNT(DISTINCT raw_susceptibility_code)" in code
    assert "STOP: approved MGB levels and severity ranks are not one-to-one" in code


def test_49_invalid_geometry_is_excluded_not_repaired():
    for path in (EXPOSURE_NOTEBOOK, VALIDATION_NOTEBOOK):
        code = code_without_comments(path)
        assert "ST_ISVALID" in code
        assert "ST_BUFFER" not in code
        assert "ST_MAKEVALID" not in code.upper()
    assert "WHEN NOT ST_ISVALID(parsed.mgb_geometry) THEN 'INVALID_GEOMETRY'" in sql(
        EXPOSURE_NOTEBOOK
    )


def test_50_geometry_parser_is_targeted_not_global_quote_stripping():
    code = sql(EXPOSURE_NOTEBOOK)
    assert "TRY_TO_GEOMETRY(geometry_text) AS published_geometry" in code
    assert "'GEOJSON_QUOTED_NUMBERS_NORMALIZED'" in code
    assert "REPLACE(mgb.geometry_json, '\"'" not in code
    assert "REPLACE(geometry_text, '\"'" not in code


def test_51_published_types_match_fact_constellation_target():
    select = publish_select()
    assert "AS DECIMAL(18, 4)) AS region_area_sqkm" in select
    assert "AS DECIMAL(7, 4)) AS share_of_region_area_pct" in select
    assert "AS susceptible_area_sqkm" in select


def test_52_no_clamping_hides_invalid_area():
    code = code_without_comments(EXPOSURE_NOTEBOOK)
    assert "ABS(" not in code
    assert "LEAST(" not in code
    # greatest is used once, only to pick the latest upstream load timestamp
    assert code.count("GREATEST(") == 1
    assert "GREATEST(\n        selected.mgb_source_load_ts" in code


def test_53_crs_validation_is_a_stop_condition():
    validation = sql(VALIDATION_NOTEBOOK)
    assert "Published areas use the approved projected equal-area CRS" in validation
    assert "Published region areas are square kilometres, not square degrees" in (
        validation
    )
    crs_check = validation.split(
        "Published region areas are square kilometres, not square degrees", 1
    )[1].split("NAMED_STRUCT", 1)[0]
    assert "'action', 'stop'" in crs_check


def test_54_unrated_and_invalid_source_findings_are_flags_not_failures():
    validation = sql(VALIDATION_NOTEBOOK)
    for name in [
        "Unmapped or unrated MGB rows remain visible",
        "Blank MGB geometry remains visible",
        "Invalid MGB geometry is excluded without repair",
        "Official regions without a safe boundary remain no data",
        "Full boundary source lineage duplicates remain visible",
    ]:
        check = validation.split(name, 1)[1].split("NAMED_STRUCT", 1)[0]
        assert "'action', 'flag'" in check


def test_55_regression_spatial_pipeline_is_referenced_once_in_publish_path():
    code = code_without_comments(EXPOSURE_NOTEBOOK)
    assert len(re.findall(r"\bregion_level_exposure_area\b", code)) == 2
    assert len(re.findall(r"\bregion_level_dissolved_exposure\b", code)) == 2
    assert len(re.findall(r"\bregion_mgb_intersection_fragments\b", code)) == 2


def test_56_area_transforms_use_area_calculation_srid():
    code = code_without_comments(EXPOSURE_NOTEBOOK)
    for view_name in (
        "region_boundary_assessment",
        "region_mgb_intersection_fragments",
        "region_level_exposure_area",
    ):
        body = view_body(code, view_name)
        assert "ST_TRANSFORM(" in body
        assert "area_calculation_srid" in body


def test_57_validation_unpivots_one_metrics_row():
    validation = sql(VALIDATION_NOTEBOOK)
    assert "SELECT INLINE(ARRAY(" in validation
    assert "FROM flood_exposure_validation_metrics" in validation
    assert "UNION ALL" not in validation


def test_58_validation_reads_tolerance_from_published_rule_version():
    validation = sql(VALIDATION_NOTEBOOK)
    assert "'overlap-tolerance-sqkm=([0-9.Ee+-]+)'" in validation
    assert "overlap-tolerance-sqkm=" in sql(EXPOSURE_NOTEBOOK)


def test_59_docs_mark_table_14_implemented():
    data_model = (ROOT / "docs/data-model.md").read_text(encoding="utf-8")
    assert "`02-silver.silver_region_flood_exposure`" in data_model
    contract = (ROOT / "docs/silver_region_flood_exposure.md").read_text(
        encoding="utf-8"
    )
    for phrase in ["EPSG:6933", "NO_SAFE_REGION_BOUNDARY", "Requires Databricks"]:
        assert phrase in contract


def test_60_regression_divisions_are_safe_under_ansi_mode():
    exposure = code_without_comments(EXPOSURE_NOTEBOOK)
    assert "/ NULLIF(grid.region_area_sqkm_unrounded, 0)" in exposure
    validation = code_without_comments(VALIDATION_NOTEBOOK)
    assert "/ NULLIF(ST_AREA(boundary_geometry), 0)" in validation
    assert "CASE WHEN checks.total_rows > 0" in validation
