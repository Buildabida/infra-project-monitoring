import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP_NOTEBOOK = ROOT / "notebooks/02_silver/08_silver_project_region_map.ipynb"
VALIDATION_NOTEBOOK = (
    ROOT / "notebooks/04_validation/06_validation_silver_project_region_map.ipynb"
)


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


def test_01_mapping_notebook_is_valid_nbformat_json():
    nb = notebook(MAP_NOTEBOOK)
    assert nb["nbformat"] == 4
    assert nb["nbformat_minor"] >= 5
    assert all(cell["cell_type"] in {"markdown", "code"} for cell in nb["cells"])


def test_02_validation_notebook_is_valid_nbformat_json():
    nb = notebook(VALIDATION_NOTEBOOK)
    assert nb["nbformat"] == 4
    assert any(cell["cell_type"] == "code" for cell in nb["cells"])


def test_03_table_13_is_created_as_delta():
    text = sql(MAP_NOTEBOOK)
    assert "CREATE OR REPLACE TABLE `02-silver`.silver_project_region_map" in text
    assert "USING DELTA" in text


def test_04_reads_canonical_silver_project():
    text = sql(MAP_NOTEBOOK)
    assert "FROM `02-silver`.silver_project AS project" in text
    assert "project.project_key" in text


def test_05_reads_official_silver_psgc_place_regions():
    text = sql(MAP_NOTEBOOK)
    assert "`02-silver`.silver_psgc_place" in text
    assert "WHERE place_type = 'REGION'" in text


def test_06_uses_only_approved_active_alias_rules():
    text = sql(MAP_NOTEBOOK)
    alias = text[text.index("approved_project_region_aliases") :]
    assert "approval_status = 'APPROVED'" in alias
    assert "is_active = TRUE" in alias
    assert "selected.alias_version" in alias


def test_alias_config_is_read_with_the_config_key():
    map_text = sql(MAP_NOTEBOOK)
    validation_text = sql(VALIDATION_NOTEBOOK)

    assert map_text.count("source_system = 'dpwh_projects'") == 3
    assert "config_place_name_alias\nWHERE source_system = 'DPWH'" not in map_text
    assert "alias.source_system = 'DPWH'" not in map_text
    assert (
        "WHERE source_system = 'dpwh_projects' AND UPPER(TRIM(place_type)) = 'REGION'"
        in validation_text
    )


def test_07_uses_only_approved_active_manual_rules():
    text = sql(MAP_NOTEBOOK)
    manual = text[text.index("approved_manual_project_targets") :]
    assert "approval_status = 'APPROVED'" in manual
    assert "is_active = TRUE" in manual
    assert "selected.manual_mapping_version" in manual


def test_08_boundaries_are_region_only_and_used_for_spatial_evidence():
    text = sql(MAP_NOTEBOOK)
    assert "LOWER(TRIM(boundary.administrative_level)) = 'region'" in text
    assert "spatial_region_candidates" in text
    assert "ST_COVERS" in text


def test_09_does_not_reread_dpwh_bronze_business_rows():
    text = sql(MAP_NOTEBOOK).lower()
    assert "`01-bronze`.dpwh_projects" not in text
    assert "`01-bronze`.load_log" in text


def test_10_does_not_read_census_or_population_outputs():
    text = sql(MAP_NOTEBOOK).lower()
    forbidden = ["census_2024_table_c", "silver_region_population", "population_count"]
    assert not any(item in text for item in forbidden)


def test_11_does_not_read_flood_control_sources():
    text = sql(MAP_NOTEBOOK).lower()
    assert "flood_control_projects" not in text
    assert "silver_flood_control_component" not in text


def test_12_has_no_source_reconciliation_dependency():
    text = sql(MAP_NOTEBOOK).lower()
    assert "silver_project_source_match" not in text


def test_13_does_not_read_mgb():
    text = sql(MAP_NOTEBOOK).lower()
    assert "flood_susceptibility" not in text
    assert "mgb" not in text


def test_14_has_no_gold_read_or_write():
    text = sql(MAP_NOTEBOOK).lower()
    assert "03-gold" not in text
    assert "dim_region" not in text


def test_15_does_not_create_gold_region_key():
    output_select = sql(MAP_NOTEBOOK).split(
        "CREATE OR REPLACE TABLE `02-silver`.silver_project_region_map", 1
    )[1]
    assert re.search(r"\bregion_key\b", output_select, re.IGNORECASE) is None


def test_16_has_no_fuzzy_matching():
    text = sql(MAP_NOTEBOOK).lower()
    assert "fuzzy" not in text
    assert "similarity" not in text


def test_17_has_no_levenshtein_or_soundex():
    text = sql(MAP_NOTEBOOK).lower()
    assert "levenshtein" not in text
    assert "soundex" not in text


def test_18_has_no_nearest_neighbor_assignment():
    text = sql(MAP_NOTEBOOK).lower()
    assert "st_distance" not in text
    assert "nearest" not in text


def test_19_has_no_broad_substring_region_match():
    text = sql(MAP_NOTEBOOK).lower()
    assert " like " not in text
    assert "rlike" not in text


def test_20_has_no_hidden_region_iv_b_mapping():
    text = sql(MAP_NOTEBOOK).upper()
    assert "REGION IV-B" not in text
    assert "REGION IV B" not in text


def test_21_has_no_hardcoded_nir_correction():
    text = sql(MAP_NOTEBOOK).upper()
    assert "NEGROS ISLAND" not in text
    assert " NIR" not in text


def test_22_central_office_exact_non_geographic_rule_exists():
    text = sql(MAP_NOTEBOOK)
    assert "reported_region_standardized = 'CENTRAL OFFICE'" in text
    assert "'NON_GEOGRAPHIC_RULE'" in text
    assert "'NON_GEOGRAPHIC'" in text


def test_23_central_office_is_excluded_before_spatial_assignment():
    text = sql(MAP_NOTEBOOK)
    spatial = text[text.index("spatial_region_candidates") :]
    assert "reported_region_standardized <> 'CENTRAL OFFICE'" in spatial


def test_24_exact_region_name_matching_is_conservative():
    text = sql(MAP_NOTEBOOK)
    assert "reported_region_standardized = region.place_name_standardized" in text
    assert "REGEXP_REPLACE(UPPER(TRIM(project.reported_region))" in text


def test_25_approved_alias_matching_is_explicit():
    text = sql(MAP_NOTEBOOK)
    assert "APPROVED_REGION_ALIAS" in text
    assert (
        "project.reported_region_standardized = alias.raw_region_standardized" in text
    )


def test_26_coordinate_fallback_is_after_stronger_automatic_methods():
    text = sql(MAP_NOTEBOOK)
    stage = text[text.index("CASE\n            WHEN reported_region_standardized") :]
    order = [
        stage.index("manual_candidate_count"),
        stage.index("exact_candidate_count"),
        stage.index("alias_candidate_count"),
        stage.index("spatial_candidate_count"),
    ]
    assert order == sorted(order)


def test_27_project_psgc_code_stage_is_explicitly_unavailable():
    text = sql(MAP_NOTEBOOK)
    assert "PROJECT_PSGC_CODE_NOT_AVAILABLE" in text
    stage_case = text.split("CASE\n            WHEN reported_region_standardized", 1)[
        1
    ].split("END AS mapping_method", 1)[0]
    assert "THEN 'PSGC_CODE'" not in stage_case


def test_28_multiple_active_rule_versions_stop_the_run():
    text = sql(MAP_NOTEBOOK)
    assert text.count("COUNT(DISTINCT alias_version) <= 1") == 1
    assert text.count("COUNT(DISTINCT mapping_version) <= 1") == 1
    assert "STOP: multiple active approved" in text


def test_29_deterministic_map_key_uses_stable_lineage():
    text = sql(MAP_NOTEBOOK)
    assert (
        "SHA2(CONCAT_WS('|', decision.source_system, decision.project_key, decision.mapping_run_id), 256)"
        in text
    )


def test_30_deterministic_run_id_includes_all_version_domains():
    text = sql(MAP_NOTEBOOK)
    for token in [
        "project_run_id",
        "psgc_run_id",
        "boundary_source_snapshot_id",
        "boundary_version",
        "alias_version",
        "manual_mapping_version",
        "silver-project-region-map-v1",
    ]:
        assert token in text


def test_31_no_random_or_uuid_identity():
    text = sql(MAP_NOTEBOOK).lower()
    assert "uuid(" not in text
    assert "rand(" not in text
    assert "random(" not in text


def test_32_current_time_is_not_used_in_logical_identity():
    text = sql(MAP_NOTEBOOK).lower()
    assert "current_date" not in text
    assert "current_timestamp" not in text


def test_33_project_row_preservation_validation_exists():
    text = sql(VALIDATION_NOTEBOOK)
    assert "Every canonical project has one mapping result" in text
    assert "ABS(map_rows - project_rows)" in text


def test_34_final_status_accounting_validation_exists():
    text = sql(VALIDATION_NOTEBOOK)
    assert "Final statuses account for every mapping row" in text
    for status_count in [
        "matched_rows",
        "conflict_rows",
        "non_geographic_rows",
        "ambiguous_rows",
        "unmatched_rows",
        "invalid_source_rows",
    ]:
        assert status_count in text


def test_35_target_psgc_validity_uses_selected_official_regions():
    text = sql(VALIDATION_NOTEBOOK)
    assert "LEFT ANTI JOIN `02-silver`.silver_psgc_place AS region" in text
    assert "mapping.psgc_source_snapshot_id = region.source_snapshot_id" in text


def test_36_name_coordinate_conflict_validation_exists():
    text = sql(VALIDATION_NOTEBOOK)
    assert "Name-versus-coordinate conflicts remain explicit" in text
    assert "REGION_MISMATCH" in text


def test_37_boundary_quality_and_coverage_are_validated():
    text = sql(VALIDATION_NOTEBOOK)
    assert "Selected region boundary geometry parses safely" in text
    assert "Region boundary coverage is reported against official PSGC regions" in text


def test_38_match_coverage_reports_complete_denominator():
    text = sql(VALIDATION_NOTEBOOK)
    assert "Geographic match coverage is reported against all projects" in text
    assert "'Denominator=', map_rows" in text


def test_39_all_seven_data_quality_attributes_have_real_checks():
    text = sql(VALIDATION_NOTEBOOK)
    attributes = {
        "Consistency",
        "Accuracy",
        "Completeness",
        "Auditability",
        "Validity",
        "Uniqueness",
        "Timeliness",
    }
    for attribute in attributes:
        assert f"'{attribute}'" in text


def test_40_validation_evidence_persists_before_stop_gate():
    text = sql(VALIDATION_NOTEBOOK)
    assert text.index("MERGE INTO `04-validation`.silver_dq_results") < text.index(
        "SELECT ASSERT_TRUE"
    )


def test_41_major_notebook_sections_have_markdown_explanations():
    text = markdown(MAP_NOTEBOOK)
    for heading in [
        "Step 1 — Prove",
        "Step 2 — Select",
        "Step 3 — Build",
        "Step 4 — Apply",
        "Summary",
    ]:
        assert heading in text


def test_42_final_summary_documents_grain_unresolved_behavior_and_lineage():
    text = markdown(MAP_NOTEBOOK)
    assert "one canonical `silver_project` mapping result" in text
    assert "unresolved and ambiguous outcomes" in text
    assert "Project, PSGC, boundary, configuration, and rule lineage" in text


def test_43_docs_resolve_d03_without_erasing_history():
    text = (ROOT / "docs/decisions.md").read_text(encoding="utf-8")
    assert "This resolves D-03" in text
    resolved = text.split("## Resolved questions", 1)[1]
    assert "D-03" in resolved
    assert "Map point, office name, or both" in resolved


def test_44_tables_14_and_15_are_not_implemented():
    text = sql(MAP_NOTEBOOK).lower() + sql(VALIDATION_NOTEBOOK).lower()
    assert "create or replace table `02-silver`.silver_project_flood_map" not in text
    assert "silver_region_flood_exposure" not in text


def test_45_no_spatial_python_pandas_or_udf_logic():
    code = sql(MAP_NOTEBOOK).lower()
    assert "pandas" not in code
    assert "geopandas" not in code
    assert "python udf" not in code
    assert "pyspark" not in code


def test_46_spatial_point_order_is_longitude_then_latitude_with_wgs84():
    text = sql(MAP_NOTEBOOK)
    assert "ST_POINT(project.longitude, project.latitude, 4326)" in text


def test_47_geojson_numeric_strings_are_normalized_before_safe_parse():
    text = sql(MAP_NOTEBOOK)
    assert "TRY_TO_GEOMETRY(REGEXP_REPLACE" in text
    assert "boundary.geometry_json" in text


def test_48_spatial_join_broadcasts_only_the_region_boundary_set():
    text = sql(MAP_NOTEBOOK)
    assert "BROADCAST(boundary)" in text
    assert "selected_region_boundaries" in text


def test_49_candidate_selection_requires_exactly_one_region():
    text = sql(MAP_NOTEBOOK)
    assert text.count("COUNT(DISTINCT region.psgc_code) = 1") >= 2
    assert "COUNT(DISTINCT manual.canonical_region_code) = 1" in text
    assert "spatial_candidate_count = 1" in text


def test_50_unresolved_rows_never_receive_an_accepted_region():
    text = sql(MAP_NOTEBOOK)
    assert "WHEN final_candidate_count > 1 THEN 'AMBIGUOUS'" in text
    assert "WHEN accepted_region_code IS NULL THEN 'UNMATCHED'" in text


def test_51_boundary_and_psgc_version_mismatch_is_visible():
    text = sql(MAP_NOTEBOOK)
    assert "VERSION_MISMATCH_VISIBLE" in text
    assert "boundary_psgc_version" in text


def test_52_empty_alias_and_manual_tables_have_version_sentinels():
    text = sql(MAP_NOTEBOOK)
    assert "NO_APPROVED_ALIAS_VERSION" in text
    assert "NO_APPROVED_MANUAL_VERSION" in text


def test_53_optional_publisher_version_is_not_fabricated():
    mapping = sql(MAP_NOTEBOOK)
    validation = sql(VALIDATION_NOTEBOOK)
    assert "load.source_version AS project_source_version" in mapping
    assert "Optional DPWH publisher version gaps remain visible" in validation


def test_54_source_load_timestamp_comes_from_audit_lineage():
    text = sql(MAP_NOTEBOOK)
    assert "COALESCE(completed_at, started_at) AS source_load_ts" in text
    assert "project.source_modified_at AS project_source_modified_at" in text
    assert "decision.psgc_source_load_ts" in text
    assert "decision.boundary_source_load_ts" in text


def test_55_local_paths_are_not_runtime_dependencies():
    text = sql(MAP_NOTEBOOK)
    assert "/Users/" not in text
    assert "file:///" not in text


def test_56_minimum_audit_fields_are_published():
    text = sql(MAP_NOTEBOOK)
    for field in [
        "AS candidate_count",
        "AS ambiguity_reason",
        "AS exception_reason",
        "AS boundary_source_version",
        "manual_source_reference",
    ]:
        assert field in text


def test_57_coordinate_screening_bounds_are_centralized_once():
    text = sql(MAP_NOTEBOOK)
    assert "project_region_mapping_parameters" in text
    for bound in ["4.2", "21.3", "116.0", "127.0"]:
        assert text.count(bound) == 1


def test_58_reusable_upstream_validation_is_gated():
    text = sql(MAP_NOTEBOOK)
    for view in [
        "selected_project_validation",
        "selected_psgc_validation",
        "latest_config_validation",
        "latest_boundary_validation",
    ]:
        assert view in text


def test_59_manual_targets_can_resolve_through_psgc_hierarchy():
    text = sql(MAP_NOTEBOOK)
    assert "target.region_code" in text
    assert "AS canonical_region_code" in text
    assert "duplicate active approved overrides" in text


def test_60_boundary_psgc_gaps_and_central_override_conflicts_are_checked():
    text = sql(VALIDATION_NOTEBOOK)
    assert "Unresolved boundary PSGC codes remain visible" in text
    assert "Central Office override conflicts remain visible" in text
