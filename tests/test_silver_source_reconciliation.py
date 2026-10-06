import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "notebooks/02_silver/06_silver_flood_control_component.ipynb"
MATCH = ROOT / "notebooks/02_silver/07_silver_project_source_match.ipynb"
VALIDATION = (
    ROOT / "notebooks/04_validation/05_validation_silver_source_reconciliation.ipynb"
)
NOTEBOOKS = (COMPONENT, MATCH, VALIDATION)


def load_notebook(path):
    return json.loads(path.read_text(encoding="utf-8"))


def notebook_text(path):
    return "\n".join(
        "".join(cell.get("source", [])) for cell in load_notebook(path)["cells"]
    )


def notebook_code(path):
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in load_notebook(path)["cells"]
        if cell["cell_type"] == "code"
    )


def all_code():
    return "\n".join(notebook_code(path) for path in NOTEBOOKS)


def test_required_notebooks_are_valid_nbformat_json():
    for path in NOTEBOOKS:
        notebook = load_notebook(path)
        assert notebook["nbformat"] == 4
        assert notebook["cells"]
        assert notebook["metadata"]["language_info"]["name"] == "sql"


def test_component_table_is_created():
    assert (
        "CREATE OR REPLACE TABLE `02-silver`.silver_flood_control_component"
        in notebook_code(COMPONENT)
    )


def test_match_table_is_created():
    assert (
        "CREATE OR REPLACE TABLE `02-silver`.silver_project_source_match"
        in notebook_code(MATCH)
    )


def test_no_bronze_writes():
    forbidden = re.compile(
        r"(?:CREATE\s+(?:OR\s+REPLACE\s+)?TABLE|INSERT\s+INTO|MERGE\s+INTO|"
        r"UPDATE|DELETE\s+FROM)\s+`01-bronze`",
        re.IGNORECASE,
    )
    assert not forbidden.search(all_code())


def test_no_gold_writes():
    assert "`03-gold`" not in all_code()


def test_component_reads_only_flood_control_bronze():
    sql = notebook_code(COMPONENT).lower()
    assert "`01-bronze`.flood_control_projects" in sql
    for source in ("dpwh_projects", "psgc", "census_2024_table_c", "boundaries"):
        assert f"`01-bronze`.{source}" not in sql


def test_match_reads_component_and_project_not_dpwh_bronze():
    sql = notebook_code(MATCH)
    assert "`02-silver`.silver_flood_control_component" in sql
    assert "`02-silver`.silver_project" in sql
    assert "`01-bronze`.dpwh_projects" not in sql


def test_no_psgc_reads():
    assert "`01-bronze`.psgc" not in all_code().lower()


def test_no_census_reads():
    assert "census_2024_table_c" not in all_code().lower()


def test_no_boundary_reads():
    assert "`01-bronze`.boundaries" not in all_code().lower()


def test_no_mgb_reads():
    assert "flood_susceptibility" not in all_code().lower()


def test_no_spatial_functions():
    sql = all_code().upper()
    for function in ("ST_INTERSECTS", "ST_CONTAINS", "ST_WITHIN", "ST_DISTANCE"):
        assert function not in sql


def test_no_pandas():
    assert "PANDAS" not in all_code().upper()


def test_no_python_or_spark_udf():
    sql = all_code().upper()
    assert "UDF(" not in sql
    assert "PANDAS_UDF" not in sql


def test_no_random_uuid_business_keys():
    assert "UUID()" not in all_code().upper()


def test_no_drop_table():
    assert "DROP TABLE" not in all_code().upper()


def test_no_generic_distinct_row_removal():
    component_sql = notebook_code(COMPONENT).upper()
    assert "SELECT DISTINCT *" not in component_sql
    assert "DROPduplicates" not in component_sql


def test_no_row_number_contract_deduplication():
    match_sql = notebook_code(MATCH).upper()
    assert "ROW_NUMBER" not in match_sql


def test_no_fuzzy_matching():
    sql = notebook_code(MATCH).upper()
    for operation in ("LEVENSHTEIN", "JARO", "SOUNDEX", "FUZZY"):
        assert operation not in sql


def test_no_description_based_matching():
    sql = notebook_code(MATCH).lower()
    assert "component_description_raw =" not in sql
    assert "description =" not in sql


def test_no_geography_based_source_matching():
    sql = notebook_code(MATCH).lower()
    for field in ("reported_region_raw =", "latitude_parsed =", "longitude_parsed ="):
        assert field not in sql


def test_exact_contract_id_method_is_explicit():
    sql = notebook_code(MATCH)
    assert "EXACT_CONTRACT_ID" in sql
    assert "MATCHED_EXACT_CONTRACT_ID" in sql


def test_contract_normalization_is_trim_and_upper_only():
    sql = notebook_code(MATCH).upper()
    assert "UPPER(TRIM(CONTRACT_ID))" in sql
    assert "REGEXP_REPLACE" not in sql
    assert "TRANSLATE(" not in sql
    assert "REPLACE(CONTRACT_ID" not in sql


def test_repeated_contract_ids_remain_in_component_table():
    sql = notebook_code(COMPONENT).upper()
    assert "OBJECT_ID" in sql
    assert "CREATE OR REPLACE TABLE" in sql
    assert "GROUP BY CONTRACT_ID" not in sql


def test_bronze_to_component_count_reconciliation_exists():
    sql = notebook_code(COMPONENT)
    assert "Bronze-to-Silver row preservation failed" in sql
    assert re.search(
        r"COUNT\(\*\)\s+FROM\s+`01-bronze`\.flood_control_projects",
        sql,
        re.IGNORECASE,
    )


def test_component_to_match_accounting_exists():
    sql = notebook_code(VALIDATION)
    assert "matched_table_component_accounting" in sql
    assert "invalid_source_contract_ids" in sql
    assert "Component accounting includes matched groups and invalid IDs" in sql


def test_source_match_status_coverage_is_enforced():
    sql = notebook_code(VALIDATION)

    assert "Match statuses reconcile to all usable source Contract IDs" in sql

    assert re.search(
        r"matched_groups\s*\+\s*unmatched_groups\s*\+\s*ambiguous_groups"
        r"\s*=\s*usable_source_contract_groups",
        sql,
    )

    assert "'stop'" in sql


def test_target_candidate_uniqueness_is_validated():
    sql = notebook_code(MATCH)
    assert "target_candidate_count" in sql
    assert "AMBIGUOUS_TARGET" in sql
    assert "CASE WHEN COUNT(*) = 1 THEN MAX(project_key)" in sql


def test_no_blind_sum_of_flood_contract_cost():
    sql = notebook_code(MATCH).upper()
    assert "SUM(SOURCE_CONTRACT_COST_PESOS)" not in sql
    assert "COUNT(DISTINCT CASE" in sql


def test_flood_cost_is_not_added_to_dpwh_budget():
    sql = all_code().lower()
    assert "reported_budget_pesos +" not in sql
    assert "+ reported_budget_pesos" not in sql


def test_silver_project_is_not_mutated():
    sql = all_code().upper()
    forbidden = re.compile(
        r"(?:CREATE\s+(?:OR\s+REPLACE\s+)?TABLE|INSERT\s+INTO|MERGE\s+INTO|"
        r"UPDATE|DELETE\s+FROM)\s+`02-SILVER`\.SILVER_PROJECT\b"
    )
    assert not forbidden.search(sql)


def test_match_coverage_has_denominators():
    sql = notebook_code(VALIDATION)
    assert "SUM(COUNT(*)) OVER ()" in sql
    assert "group_percentage" in sql
    assert (
        "usable normalized source Contract ID groups as the denominator"
        in notebook_text(VALIDATION)
    )


def test_deterministic_rule_and_run_versions_exist():
    sql = notebook_code(COMPONENT) + notebook_code(MATCH)
    assert "silver_flood_control_component_v1" in sql
    assert "silver_project_source_match_v1" in sql
    assert "SHA2(" in sql
 

def test_validation_run_id_includes_match_run_id():
    sql = notebook_code(VALIDATION)

    context_start = sql.index(
        "CREATE OR REPLACE TEMPORARY VIEW silver_source_reconciliation_context"
    )
    checks_start = sql.index(
        "CREATE OR REPLACE TEMPORARY VIEW silver_source_reconciliation_checks"
    )

    context_sql = sql[context_start:checks_start]

    assert "COALESCE(match.match_run_id, '')" in context_sql
    assert "silver_source_reconciliation_validation_v2" in context_sql


def test_source_and_target_lineage_are_retained():
    sql = notebook_code(MATCH)
    for field in (
        "source_snapshot_id",
        "source_component_run_id",
        "matched_project_source_snapshot_id",
        "matched_project_source_ingest_run_id",
        "target_project_run_id",
    ):
        assert field in sql


def test_all_seven_data_quality_attributes_have_checks():
    sql = notebook_code(VALIDATION)
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


def test_validation_is_persisted_before_blocking_gate():
    sql = notebook_code(VALIDATION)
    assert sql.index("MERGE INTO `04-validation`.silver_dq_results") < sql.index(
        "blocking Silver source reconciliation checks failed"
    )


def test_markdown_precedes_each_major_sql_section():
    for path in NOTEBOOKS:
        notebook = load_notebook(path)
        code_indexes = [
            index
            for index, cell in enumerate(notebook["cells"])
            if cell["cell_type"] == "code"
        ]
        assert code_indexes
        assert all(
            index > 0 and notebook["cells"][index - 1]["cell_type"] == "markdown"
            for index in code_indexes
        )


def test_notebooks_end_with_explanatory_summaries():
    for path in NOTEBOOKS:
        final_cell = load_notebook(path)["cells"][-1]
        assert final_cell["cell_type"] == "markdown"
        text = "".join(final_cell["source"])
        assert "# Summary" in text
        assert "Requires Databricks execution." in text


def test_invalid_contract_ids_are_not_silently_dropped():
    component_sql = notebook_code(COMPONENT)
    validation_sql = notebook_code(VALIDATION)
    assert "source_contract_id_normalized" in component_sql
    assert "invalid_source_contract_ids" in validation_sql
    assert "Rows stay in the component table" in validation_sql


def test_match_status_contract_is_complete():
    sql = notebook_code(MATCH)
    for status in ("MATCHED_EXACT_CONTRACT_ID", "UNMATCHED", "AMBIGUOUS_TARGET"):
        assert status in sql


def test_source_cost_conflicts_remain_unresolved():
    sql = notebook_code(MATCH)
    assert "source_cost_resolution_status" in sql
    assert "ELSE 'CONFLICT'" in sql
    assert "ELSE NULL" in sql


def test_decision_d04_is_not_claimed_as_resolved():
    match_text = notebook_text(MATCH)
    docs = ROOT / "docs/silver_source_reconciliation.md"
    assert "D-04 remains open" in match_text
    if docs.exists():
        assert "D-04 remains open" in docs.read_text(encoding="utf-8")
