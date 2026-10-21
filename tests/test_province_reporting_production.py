import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AREA = ROOT / "notebooks/02_silver/01a_silver_province_reporting_area.ipynb"
POPULATION = (
    ROOT / "notebooks/02_silver/03a_silver_province_reporting_area_population.ipynb"
)
PROFILE = ROOT / "notebooks/02_silver/08b_profile_project_province_readiness.ipynb"
PROJECT_MAP = ROOT / "notebooks/02_silver/08c_silver_project_province_map.ipynb"
SILVER_VALIDATION = (
    ROOT / "notebooks/04_validation/03b_validation_silver_province_reporting.ipynb"
)
GOLD_AREA = ROOT / "notebooks/03_gold/01a_gold_dim_province_reporting_area.ipynb"
GOLD_POPULATION = (
    ROOT / "notebooks/03_gold/05a_gold_fact_province_reporting_area_population.ipynb"
)
GOLD_PROJECT = ROOT / "notebooks/03_gold/07_gold_fact_project_snapshot.ipynb"
GOLD_VALIDATION = (
    ROOT / "notebooks/04_validation/09a_validation_gold_province_reporting.ipynb"
)
ANALYTICS = ROOT / "notebooks/05_analytics/01_business_questions.ipynb"
ANALYTICS_VALIDATION = ROOT / "notebooks/04_validation/10_validation_analytics.ipynb"
ACCEPTANCE_EVIDENCE = (
    ROOT / "notebooks/04_validation/11_publish_acceptance_evidence.sql"
)

NOTEBOOKS = [
    AREA,
    POPULATION,
    PROFILE,
    PROJECT_MAP,
    SILVER_VALIDATION,
    GOLD_AREA,
    GOLD_POPULATION,
    GOLD_PROJECT,
    GOLD_VALIDATION,
    ANALYTICS,
    ANALYTICS_VALIDATION,
]


def notebook(path):
    return json.loads(path.read_text(encoding="utf-8"))


def text(path, cell_type=None):
    cells = notebook(path)["cells"]
    if cell_type:
        cells = [cell for cell in cells if cell["cell_type"] == cell_type]
    return "\n".join("".join(cell.get("source", [])) for cell in cells)


def sql(path):
    return text(path, "code")


def test_production_notebooks_are_valid_databricks_sql():
    for path in NOTEBOOKS:
        nb = notebook(path)
        assert nb["nbformat"] == 4
        meta = nb["metadata"]["application/vnd.databricks.v1+notebook"]
        assert meta["language"] == "sql"
        assert meta["notebookName"] == path.stem
        for cell in nb["cells"]:
            if cell["cell_type"] == "code":
                assert "".join(cell["source"]).startswith("%sql\n")
                assert cell["outputs"] == []


def test_reporting_area_policy_has_unknown_ncr_and_independent_city():
    area = sql(AREA)
    assert "'PROVINCE' AS reporting_area_type" in area
    assert "'INDEPENDENT_CITY' AS reporting_area_type" in area
    assert "'NCR' AS reporting_area_type" in area
    assert "'UNKNOWN' AS reporting_area_type" in area
    assert "province_code IS NULL" in area
    assert "region_code <> ncr_region_code" in area
    assert "CAST(0 AS BIGINT)" in area
    assert "parent_region_code" in area


def test_raw_source_province_and_district_office_are_not_authority():
    mapping = sql(PROJECT_MAP)
    assert (
        "GET_JSON_OBJECT(bronze.source_record_json, '$.location.province')" in mapping
    )
    assert "DPWH_PROVINCE_REPORTING_AREA" in mapping
    assert "approval_status = 'APPROVED'" in mapping
    assert "alias.is_active" in mapping
    assert "exact_name_reporting_area_key" in mapping
    decision = mapping.split("decision AS (", 1)[1].split("classified AS (", 1)[0]
    assert "exact_name_reporting_area_key" not in decision
    assert "deo" not in mapping.lower()


def test_matching_is_normalized_exact_governed_and_not_fuzzy():
    mapping = sql(PROJECT_MAP)
    assert "REGEXP_REPLACE(UPPER(TRIM(" in mapping
    assert "WHEN alias_candidate_count = 1 THEN alias_reporting_area_key" in mapping
    assert (
        "WHEN manual_reporting_area_key IS NOT NULL THEN manual_reporting_area_key"
        in mapping
    )
    lowered = mapping.lower()
    for forbidden in [
        "levenshtein(",
        "soundex(",
        "similarity(",
        "st_distance(",
        "nearest",
        "like concat(",
    ]:
        assert forbidden not in lowered


def test_spatial_mapping_is_one_join_longitude_first_and_keeps_all_outcomes():
    mapping = sql(PROJECT_MAP)
    assert mapping.count("ST_COVERS(") == 1
    assert (
        "ST_POINT(project.longitude, project.latitude, source_geometry_srid)" in mapping
    )
    assert "boundary.boundary_status = 'VALID_BOUNDARY'" in mapping
    assert "spatial_candidate_count = 1" in mapping
    assert "spatial_candidate_count > 1" in mapping
    assert "'AMBIGUOUS'" in mapping
    assert "'UNMAPPED'" in mapping
    assert "conflict_flag" in mapping
    assert "MATCHED_WITH_CONFLICT" in mapping


def test_matching_precedence_and_inactive_pending_config_safety():
    mapping = sql(PROJECT_MAP)
    decision = mapping.split("decision AS (", 1)[1].split("classified AS (", 1)[0]
    assert decision.index(
        "reported_region_standardized = 'CENTRAL OFFICE'"
    ) < decision.index("manual_reporting_area_key IS NOT NULL")
    assert decision.index("manual_reporting_area_key IS NOT NULL") < decision.index(
        "alias_candidate_count = 1"
    )
    assert decision.index("alias_candidate_count = 1") < decision.index(
        "spatial_candidate_count = 1"
    )
    assert "approval_status = 'APPROVED' AND alias.is_active" in mapping
    assert "approval_status = 'APPROVED' AND manual.is_active" in mapping
    assert "PENDING" not in mapping


def test_config_checks_prevent_ambiguity_invalid_targets_and_generic_aliases():
    mapping = sql(PROJECT_MAP)
    assert "COUNT(DISTINCT alias_version) <= 1" in mapping
    assert "COUNT(DISTINCT mapping_version) <= 1" in mapping
    assert "canonical_psgc_code = area.psgc_reporting_area_code" in mapping
    assert "reporting_area_type <> 'PROVINCE'" in mapping
    assert "reporting_area_type <> 'INDEPENDENT_CITY'" in mapping
    assert "reporting_area_type <> 'NCR'" in mapping
    assert "('UNKNOWN', 'N/A', 'NA', 'NONE', '-')" in mapping
    assert (
        "one approved source province value maps to multiple reporting areas" in mapping
    )


def test_project_map_is_deterministic_and_preserves_project_and_budget_grain():
    mapping = sql(PROJECT_MAP)
    for lineage in [
        "project_source_snapshot_id",
        "project_run_id",
        "project_ingest_run_id",
        "psgc_version",
        "psgc_run_id",
        "boundary_version",
        "boundary_run_id",
        "mapping_config_version",
        "mapping_rule_version",
    ]:
        assert lineage in mapping
    assert "selected.mapping_run_id AS run_id" in mapping
    assert "PROJECT_PROVINCE_REPORTING_AREA_MAP" in mapping
    assert "CAST(classified.project_key AS STRING), selected.mapping_run_id" in mapping
    assert "COUNT(*) = COUNT(DISTINCT project_key)" in mapping
    assert "SUM(project.reported_budget_pesos) <=>" in mapping
    assert "project_province_map_key <> XXHASH64" in mapping


def test_population_uses_only_accepted_primary_barangays_and_reconciles():
    population = sql(POPULATION)
    assert "row_disposition = 'ACCEPTED_PRIMARY'" in population
    assert "matched_place_type = 'BARANGAY'" in population
    assert "population_count > 0" in population
    assert "SUM(population_count)" in population
    assert "UNRESOLVED_ACCEPTED_POPULATION" in population
    assert "excluded_population_count" in population
    assert "MISSING_PRIMARY_POPULATION" in population
    assert "COALESCE(population.population_count, 0)" not in population


def test_gold_schema_adds_reporting_area_without_removing_region():
    project = sql(GOLD_PROJECT)
    assert "region_key BIGINT NOT NULL" in project
    assert "reporting_area_key BIGINT NOT NULL" in project
    assert (
        "INNER JOIN `02-silver`.silver_project_province_map AS province_map" in project
    )
    assert (
        "LEFT JOIN `03-gold`.dim_province_reporting_area AS reporting_area" in project
    )
    assert "COUNT(*) = (SELECT COUNT(*) FROM `02-silver`.silver_project)" in project
    assert "SUM(reported_budget_pesos) <=>" in project
    assert "selected.province_map_run_id" in project


def test_six_views_read_province_only_from_the_governed_gold_key():
    analytics = sql(ANALYTICS)
    # d-56 keeps one view per insight. the first province views are retired, not rebuilt
    for view in [
        "analytics_reporting_area_investment",
        "analytics_reporting_area_category",
        "analytics_reporting_area_delivery_status",
        "analytics_reporting_area_population_equity",
        "analytics_reporting_area_project_size_concentration",
    ]:
        assert f"CREATE OR REPLACE VIEW `05-analytics`.{view}" not in analytics
        assert f"DROP VIEW IF EXISTS `05-analytics`.{view};" in analytics
    assert analytics.count("CREATE OR REPLACE VIEW `05-analytics`.") == 6
    assert "reporting_area_key AS geography_key" in analytics
    assert "FROM `03-gold`.fact_province_reporting_area_population" in analytics
    assert "location" not in analytics.lower()
    assert not (
        ROOT / "notebooks/04_validation/10a_validation_provincial_analytics.ipynb"
    ).exists()


def test_validators_persist_evidence_before_stop_gates():
    for path, results in [
        (SILVER_VALIDATION, "silver_dq_results"),
        (GOLD_VALIDATION, "gold_dq_results"),
        (ANALYTICS_VALIDATION, "analytics_dq_results"),
    ]:
        validation = sql(path)
        merge_position = validation.index(f"MERGE INTO `04-validation`.{results}")
        stop_position = validation.index("SELECT ASSERT_TRUE(", merge_position)
        assert merge_position < stop_position
        assert "WHEN MATCHED THEN UPDATE SET *" in validation
    assert "one final row per canonical project" in sql(SILVER_VALIDATION)
    assert "reported budget total equals canonical Silver projects" in sql(
        GOLD_VALIDATION
    )
    assert "Each level plus key 0 adds up to every current project and budget" in sql(
        ANALYTICS_VALIDATION
    )
    for added in [
        "contributing Table C rows are counted once",
        "every reporting area has one official parent region",
        "region minus reporting-area population equals unresolved population",
    ]:
        assert added in sql(SILVER_VALIDATION), added
    for added in [
        "PSGC reporting area code is unique per PSGC version",
        "parent region key exists in dim_region",
        "reporting area key 0 holds exactly the unresolved and non-geographic projects",
        "project region differs from the parent region of its reporting area",
        "region minus reporting-area population equals unresolved population",
    ]:
        assert added in sql(GOLD_VALIDATION), added


def test_acceptance_evidence_publishes_coverage_and_exact_rerun_identity():
    evidence = ACCEPTANCE_EVIDENCE.read_text(encoding="utf-8")
    for required in [
        "province_reporting_acceptance_evidence",
        "province_reporting_acceptance_runs",
        "province_reporting_acceptance_mapping_methods",
        "mapped_project_percentage",
        "mapped_budget_percentage",
        "mapping_method",
        "ncr_projects",
        "independent_city_projects",
        "barmm_projects",
        "accepted_population",
        "unresolved_accepted_population",
        "excluded_population",
        "mapping_identity_checksum",
        "exact_rerun_status",
        "RERUN_REQUIRED",
    ]:
        assert required in evidence
    assert "COUNT(DISTINCT layer) = 3" in evidence
    assert "COUNT_IF(action = 'stop' AND status = 'FAIL') = 0" in evidence
    assert "BIT_XOR(XXHASH64(CONCAT_WS(" in evidence
    assert "COUNT(*) < 2 THEN 'RERUN_REQUIRED'" in evidence
    assert "COUNT(DISTINCT project_map_run_id) = 1" in evidence
    assert "COUNT(DISTINCT mapping_identity_checksum) = 1" in evidence


def test_province_flood_exposure_is_not_fabricated():
    production_sql = "\n".join(sql(path) for path in NOTEBOOKS)
    assert "silver_province_flood_exposure" not in production_sql
    assert "fact_province_flood_exposure" not in production_sql
    assert "analytics_province_flood_control_exposure" not in production_sql


def test_runtime_fixes_from_the_october_16_databricks_run_stay_in_place():
    # spark sql does not read '' as an escaped quote inside a string literal
    for path in NOTEBOOKS:
        assert "''D-57" not in sql(path)
        assert "''REPORTING_AREA_COLUMNS_PRESENT''" not in sql(path)
    assert "COMMENT \\'D-57 province reporting area key.\\'" in sql(GOLD_PROJECT)
    # ambiguous columns are qualified after the joins that repeat them
    assert "COALESCE(all_areas.psgc_version, source_snapshot_id)" in sql(AREA)
    assert "all_areas.psgc_run_id," in sql(AREA)
    assert "COUNT(*) = COUNT(DISTINCT map.project_key)" in sql(PROJECT_MAP)
    # the merged boundary keeps the srid of the gold table
    assert "ST_SETSRID(boundary_geometry, 4326) AS boundary_geometry" in sql(GOLD_AREA)


def test_gold_province_flag_checks_save_flag_not_fail():
    gold = sql(GOLD_VALIDATION)
    assert "WHEN checks.action = 'stop' AND checks.failed_rows > 0 THEN 'FAIL'" in gold
    assert "WHEN checks.action = 'flag' AND checks.failed_rows > 0 THEN 'FLAG'" in gold
    assert "CASE WHEN checks.failed_rows > 0 THEN 'FAIL' ELSE 'PASS' END" not in gold
