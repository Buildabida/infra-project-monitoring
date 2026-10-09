import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SILVER_DIR = REPO_ROOT / "notebooks/02_silver"
VALIDATION_NOTEBOOK = (
    REPO_ROOT
    / "notebooks/04_validation/03_validation_silver_geography_population.ipynb"
)
NOTEBOOKS = (
    SILVER_DIR / "01_silver_psgc_place.ipynb",
    SILVER_DIR / "02_silver_population_place_reconciliation.ipynb",
    SILVER_DIR / "03_silver_region_population.ipynb",
)
ALL_NOTEBOOKS = NOTEBOOKS + (VALIDATION_NOTEBOOK,)


def load_notebook(path):
    return json.loads(path.read_text(encoding="utf-8"))


def notebook_text(path):
    notebook = load_notebook(path)
    return "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])


def notebook_code(path):
    notebook = load_notebook(path)
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )


def all_sql():
    return "\n".join(notebook_text(path) for path in ALL_NOTEBOOKS)


def test_required_notebooks_are_valid_nbformat_documents():
    for path in ALL_NOTEBOOKS:
        notebook = load_notebook(path)
        assert notebook["nbformat"] == 4
        assert notebook["cells"]
        assert notebook["metadata"]["language_info"]["name"] == "sql"


def test_three_required_silver_tables_are_created():
    expected = (
        "silver_psgc_place",
        "silver_population_place_reconciliation",
        "silver_region_population",
    )
    sql = all_sql()
    for table in expected:
        assert f"CREATE OR REPLACE TABLE `02-silver`.{table}" in sql


def test_bronze_and_gold_are_never_written():
    sql = all_sql()
    forbidden_write = re.compile(
        r"(?:CREATE\s+(?:OR\s+REPLACE\s+)?TABLE|INSERT\s+INTO|"
        r"MERGE\s+INTO|UPDATE|DELETE\s+FROM)\s+`(?:01-bronze|03-gold)`",
        flags=re.IGNORECASE,
    )
    assert not forbidden_write.search(sql)


def test_matching_is_contextual_and_never_fuzzy():
    sql = notebook_code(NOTEBOOKS[1])
    assert "locality_context_code = place.city_municipality_code" in sql
    assert "sheet_psgc_code = place.psgc_code" in sql
    assert "candidate_count" in sql
    for forbidden in ("LEVENSHTEIN", "JARO", "FUZZY", "SOUNDEX"):
        assert forbidden not in sql.upper()


def test_alias_matching_requires_active_approved_context():
    sql = notebook_text(NOTEBOOKS[1])
    assert "config_place_name_alias" in sql
    assert "alias.approval_status = 'APPROVED'" in sql
    assert "alias.is_active = TRUE" in sql
    assert "alias.alias_version = parameters.alias_version" in sql
    assert "TRIM(alias.raw_region_name) <> ''" in sql
    assert "TRIM(alias.raw_province_name) <> ''" in sql
    assert "TRIM(alias.raw_city_municipality_name) <> ''" in sql


def test_table_c_raw_population_and_safe_parse_are_retained():
    sql = notebook_text(NOTEBOOKS[1])
    assert "population AS population_raw" in sql
    assert "TRY_CAST(REPLACE(TRIM(population), ',', '') AS BIGINT)" in sql
    assert "population_raw" in sql
    assert "population_count" in sql


def test_source_row_lineage_is_retained_and_used_as_the_grain():
    sql = notebook_text(NOTEBOOKS[1])
    for column in ("source_file", "sheet_name", "source_row_number"):
        assert column in sql
    assert "source_row_identity" in sql
    assert "source_ingest_run_id" in sql
    assert "source_snapshot_id" in sql


def test_unresolved_and_invalid_rows_remain_visible():
    sql = notebook_text(NOTEBOOKS[1])
    for status in (
        "AMBIGUOUS",
        "UNMATCHED",
        "INVALID_POPULATION",
        "SOURCE_EXCEPTION",
    ):
        assert status in sql
    assert "CREATE OR REPLACE TABLE" in sql
    assert (
        "WHERE row_disposition = 'ACCEPTED_PRIMARY'"
        not in sql.split(
            "CREATE OR REPLACE TABLE `02-silver`.silver_population_place_reconciliation",
            maxsplit=1,
        )[1]
    )


def test_non_positive_population_is_not_replaced_or_hidden():
    sql = notebook_text(NOTEBOOKS[1])
    assert "population_count IS NULL OR population_count <= 0" in sql
    assert "THEN 'INVALID_POPULATION'" in sql
    assert not re.search(
        r"COALESCE\s*\(\s*population_count\s*,\s*0\s*\)",
        sql,
        flags=re.IGNORECASE,
    )


def test_psgc_population_is_diagnostic_only():
    reconciliation = notebook_text(NOTEBOOKS[1])
    region = notebook_text(NOTEBOOKS[2])
    assert "psgc_population_crosscheck" in reconciliation
    assert "population_difference" in reconciliation
    assert "SUM(population_count)" in region
    assert "SUM(psgc_population_crosscheck)" not in region


def test_exact_row_reconciliation_and_population_reconciliation_exist():
    region = notebook_text(NOTEBOOKS[2])
    validation = notebook_text(VALIDATION_NOTEBOOK)
    assert "silver_population_place_reconciliation)" in region
    assert "census_2024_table_c)" in region
    assert "row_disposition = 'ACCEPTED_PRIMARY'" in region
    assert "Regional population must reconcile exactly" in region
    assert "Every Table C row has one reconciliation result" in validation


def test_regional_population_uses_only_non_overlapping_barangay_grain():
    sql = notebook_text(NOTEBOOKS[2])
    assert "row_disposition = 'ACCEPTED_PRIMARY'" in sql
    assert "matched_place_type = 'BARANGAY'" in sql
    assert "population_count > 0" in sql
    assert "SUM(population_count)" in sql


def test_silver_and_bronze_run_identities_are_distinct():
    sql = all_sql()
    assert "source_ingest_run_id" in sql
    assert "AS run_id" in sql
    assert "source_ingest_run_id AS run_id" not in sql
    assert "UUID()" not in sql.upper()


def test_safe_delta_replacement_is_used_without_drop_table():
    sql = all_sql()
    assert sql.count("CREATE OR REPLACE TABLE `02-silver`.") == 3
    assert "DROP TABLE" not in sql.upper()
    assert "MERGE INTO `04-validation`.silver_dq_results" in sql


def test_no_generic_duplicate_removal_shortcut_hides_rows():
    silver_sql = "\n".join(notebook_text(path) for path in NOTEBOOKS)
    assert "dropDuplicates" not in silver_sql
    assert "ROW_NUMBER() = 1" not in silver_sql.upper()
    assert "SELECT DISTINCT *" not in silver_sql.upper()


def test_no_spatial_or_unrelated_large_source_processing_exists():
    sql = all_sql().upper()
    for operation in ("ST_INTERSECTS", "ST_CONTAINS", "ST_WITHIN"):
        assert operation not in sql
    for source in (
        "`01-BRONZE`.FLOOD_SUSCEPTIBILITY",
        "`01-BRONZE`.BOUNDARIES",
        "`01-BRONZE`.DPWH_PROJECTS",
        "`01-BRONZE`.FLOOD_CONTROL_PROJECTS",
    ):
        assert source not in sql


def test_validation_persists_all_seven_quality_attributes_before_gate():
    sql = notebook_text(VALIDATION_NOTEBOOK)
    for attribute in (
        "Consistency",
        "Accuracy",
        "Completeness",
        "Auditability",
        "Validity",
        "Uniqueness",
        "Timeliness",
    ):
        assert f"'{attribute}'" in sql
    assert sql.index("MERGE INTO `04-validation`.silver_dq_results") < sql.index(
        "blocking Silver geography and population checks failed"
    )


def test_each_notebook_ends_with_an_explanatory_summary():
    for path in ALL_NOTEBOOKS:
        markdown = [
            "".join(cell.get("source", []))
            for cell in load_notebook(path)["cells"]
            if cell["cell_type"] == "markdown"
        ]
        assert markdown
        assert markdown[-1].startswith("# Summary")
        assert "Requires Databricks execution" in markdown[-1]


def test_psgc_lineage_is_required_only_for_matched_reconciliation_rows():
    sql = notebook_text(VALIDATION_NOTEBOOK)

    assert (
        "match_status IN ('MATCHED_EXACT_CONTEXT', 'MATCHED_ALIAS', "
        "'MATCHED_NORMALIZED_CONTEXT')" in sql
    )
    assert "match_status <> 'UNMATCHED'" not in sql


def test_city_sheet_headings_include_districts_through_their_parent_place():
    sql = notebook_code(NOTEBOOKS[1])
    assert "AS locality_parent_code" in sql
    assert "CONCAT(SUBSTRING(place.psgc_code, 1, 5), '00000')" in sql
    assert "place.locality_parent_code = sheet.sheet_psgc_code" in sql
    assert "locality.place_type = 'SUBMUNICIPALITY'" in sql


def test_sheet_and_heading_aliases_require_context():
    sql = notebook_code(NOTEBOOKS[1])
    assert "alias.match_rule = 'TABLE_C_SHEET_NAME'" in sql
    assert "alias.match_rule = 'TABLE_C_LOCALITY_HEADING'" in sql
    assert "AND TRIM(alias.raw_region_name) <> ''" in sql
    assert (
        "(TRIM(alias.raw_region_name) <> '' OR TRIM(alias.raw_province_name) <> '')"
        in sql
    )
    assert (
        "target.place_type IN ('PROVINCE', 'CITY', 'MUNICIPALITY', 'UNASSIGNED')" in sql
    )
    assert (
        "COALESCE(alias.match_rule, '') NOT IN "
        "('TABLE_C_SHEET_NAME', 'TABLE_C_LOCALITY_HEADING')" in sql
    )


def test_normalization_key_is_deterministic_and_shared():
    sql = notebook_code(NOTEBOOKS[1])
    assert "CREATE OR REPLACE TEMPORARY VIEW place_name_match_key" in sql
    assert "[⁰¹²³⁴⁵⁶⁷⁸⁹]" in sql
    for rule in ("'$1SANTO'", "'$1SANTA'", "'$1SAINT'"):
        assert rule in sql
    assert "REPLACE(name_with_saint_words, '-', '')" in sql
    assert "SELECT place_name_standardized FROM `02-silver`.silver_psgc_place" in sql


def test_fallback_ranks_run_only_after_exact_and_alias_find_nothing():
    sql = notebook_code(NOTEBOOKS[1])
    assert "AS place_name_without_footnote" in sql
    assert r"'\\s*[0-9]+$'" in sql
    for method in (
        "'EXACT_CONTEXT'",
        "'APPROVED_ALIAS'",
        "'NORMALIZED_NAME_CONTEXT'",
        "'FOOTNOTE_REMOVED_CONTEXT'",
    ):
        assert method in sql
    assert "MIN(CASE WHEN match_rank <= 2 THEN match_rank END)" in sql
    assert "primary_rank IS NULL AND match_rank >= 3 AND NOT is_claimed_target" in sql
    assert "AS target_claim_count" in sql
    assert "'MATCHED_NORMALIZED_CONTEXT'" in sql
    assert "WHEN match_status = 'AMBIGUOUS' AND target_claim_count > 1" in sql


def test_all_caps_barangays_cannot_absorb_unresolved_subtotals():
    sql = notebook_code(NOTEBOOKS[1])
    assert "AS is_barangay_candidate_row" in sql
    assert "WHERE place_type <> 'BARANGAY'" in sql
    assert "higher_level_name.name_standardized IS NULL" in sql
    assert "source.is_barangay_candidate_row AND source.place_name_standardized" in sql


def test_validation_accepts_normalized_matches_and_flags_reused_barangays():
    sql = notebook_text(VALIDATION_NOTEBOOK)
    assert "'MATCHED_NORMALIZED_CONTEXT'" in sql
    assert "Normalized-rule match coverage" in sql
    assert "Each PSGC barangay is accepted at most once" in sql
