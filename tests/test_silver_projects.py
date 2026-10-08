import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "notebooks/02_silver/04_silver_dpwh_project_component.ipynb"
PROJECT = ROOT / "notebooks/02_silver/05_silver_project.ipynb"
VALIDATION = ROOT / "notebooks/04_validation/04_validation_silver_projects.ipynb"
NOTEBOOKS = [COMPONENT, PROJECT, VALIDATION]

SEVEN_ATTRIBUTES = {
    "Completeness",
    "Uniqueness",
    "Validity",
    "Accuracy",
    "Consistency",
    "Auditability",
    "Timeliness",
}


def cells(path):
    return json.loads(path.read_text(encoding="utf-8"))["cells"]


def sql(path):
    return "\n".join(
        "".join(cell["source"]) for cell in cells(path) if cell["cell_type"] == "code"
    )


def markdown(path):
    return "\n".join(
        "".join(cell["source"])
        for cell in cells(path)
        if cell["cell_type"] == "markdown"
    )


def statement(path, start):
    """Return one SQL statement that begins with the given text."""
    text = sql(path)
    begin = text.index(start)
    return text[begin : text.index(";", begin)]


def test_01_notebooks_are_valid_nbformat():
    for path in NOTEBOOKS:
        notebook = json.loads(path.read_text(encoding="utf-8"))
        assert notebook["nbformat"] == 4
        assert notebook["nbformat_minor"] >= 5
        assert {cell["cell_type"] for cell in notebook["cells"]} <= {"markdown", "code"}


def test_02_every_code_cell_has_markdown_before_it():
    for path in NOTEBOOKS:
        notebook_cells = cells(path)
        for index, cell in enumerate(notebook_cells):
            if cell["cell_type"] == "code":
                assert index > 0, path.name
                assert notebook_cells[index - 1]["cell_type"] == "markdown", (
                    f"{path.name} cell {index}"
                )


def test_03_each_step_explains_what_why_protects_and_expected_result():
    for path in NOTEBOOKS:
        text = markdown(path)
        steps = re.findall(r"^## \d+\. ", text, flags=re.MULTILINE)
        assert steps, path.name
        for label in ["**What:**", "**Why:**", "**Protects:**", "**Expected result:**"]:
            assert text.count(label) == len(steps), f"{path.name} {label}"


def test_04_each_notebook_starts_with_purpose_and_ends_with_summary():
    for path in NOTEBOOKS:
        notebook_cells = cells(path)
        first = "".join(notebook_cells[0]["source"])
        assert "## Purpose" in first, path.name
        assert "## Not done here" in first, path.name
        assert "# Summary" in markdown(path), path.name


def test_05_component_reads_only_bronze_dpwh_audit_and_config():
    text = sql(COMPONENT)
    tables = set(re.findall(r"`(0\d-[a-z]+)`\.(\w+)", text))
    assert tables == {
        ("01-bronze", "load_log"),
        ("01-bronze", "dpwh_projects"),
        ("04-validation", "dq_results"),
        ("02-silver", "config_project_category_mapping"),
        ("02-silver", "config_project_status_mapping"),
        ("02-silver", "silver_dpwh_project_component"),
    }


def test_06_component_mappings_use_the_config_validator_key():
    text = sql(COMPONENT)
    assert "'dpwh_projects' AS mapping_source_system" in text
    assert "'' AS mapping_source_infra_type" in text
    assert "mapping.source_system = parameters.mapping_source_system" in text
    assert "mapping.source_infra_type = parameters.mapping_source_infra_type" in text
    assert text.count("mapping.approval_status = 'APPROVED'") == 2
    assert text.count("mapping.is_active = TRUE") == 2


def test_07_component_mappings_cannot_multiply_rows():
    text = sql(COMPONENT)
    assert "COUNT(*) = COUNT(DISTINCT raw_category)" in text
    assert "COUNT(*) = COUNT(DISTINCT source_status)" in text
    assert "COALESCE(TRIM(component.category_raw), '') = category.raw_category" in text
    assert "COALESCE(TRIM(component.status_raw), '') = status.source_status" in text


def test_08_component_has_stable_source_row_identity():
    text = sql(COMPONENT)
    for column in ["component_key", "source_row_hash", "source_row_ordinal", "run_id"]:
        assert f"AS {column}" in text, column
    assert "PARTITION BY hashed_rows.source_row_hash" in text
    assert "'DPWH_COMPONENT'" in text


def test_09_component_publishes_quality_statuses():
    text = sql(COMPONENT)
    for column in [
        "budget_quality_status",
        "progress_quality_status",
        "infra_year_quality_status",
        "category_mapping_state",
        "status_mapping_state",
        "infra_year_parsed",
    ]:
        assert f"AS {column}" in text, column


def test_10_progress_range_is_declared_once():
    text = sql(COMPONENT)
    assert "CAST(0 AS DOUBLE) AS progress_min_pct" in text
    assert "CAST(100 AS DOUBLE) AS progress_max_pct" in text
    assert "parsed_rows.progress_min_pct" in text
    assert "parsed_rows.progress_max_pct" in text


def test_11_component_drops_and_dedups_nothing():
    text = sql(COMPONENT).upper()
    for forbidden in ["DROP TABLE", "DELETE FROM", "SELECT DISTINCT", "QUALIFY"]:
        assert forbidden not in text, forbidden
    build = statement(
        COMPONENT, "CREATE OR REPLACE TABLE `02-silver`.silver_dpwh_project_component"
    )
    assert "INNER JOIN" not in build
    assert build.count("LEFT JOIN") == 2
    assert "WHERE" not in build


def test_12_project_reads_only_the_component_table():
    text = sql(PROJECT)
    tables = set(re.findall(r"`(0\d-[a-z]+)`\.(\w+)", text))
    assert tables == {
        ("02-silver", "silver_dpwh_project_component"),
        ("02-silver", "silver_project"),
    }


def test_13_project_never_sums_budgets():
    build = statement(
        PROJECT, "CREATE OR REPLACE TEMPORARY VIEW project_budget_resolution"
    )
    assert "SUM(" not in build
    assert "'CONFLICT'" in build
    table = statement(PROJECT, "CREATE OR REPLACE TABLE `02-silver`.silver_project")
    assert "SUM(" not in table


def test_14_project_keeps_key_recipe_and_versions_its_rule():
    text = sql(PROJECT)
    assert "'dpwh' AS project_key_label" in text
    assert "'silver_project_v3' AS transformation_rule_version" in text
    assert "CONCAT_WS('|', parameters.project_key_label" in text


def test_15_project_counts_and_values_use_the_same_expression():
    text = sql(PROJECT)
    for column in ["reported_region", "contractor", "source_of_funds", "deo"]:
        expression = f"NULLIF(TRIM({column}), '')"
        assert f"COUNT(DISTINCT {expression})" in text, column
        assert f"MAX({expression})" in text, column


def test_16_project_keeps_every_downstream_column():
    table = statement(PROJECT, "CREATE OR REPLACE TABLE `02-silver`.silver_project")
    for column in [
        "contract_id",
        "project_key",
        "run_id",
        "source_snapshot_id",
        "source_ingest_run_id",
        "source_modified_at",
        "transformation_rule_version",
        "reported_region",
        "latitude_parsed",
        "longitude_parsed",
        "reported_budget_pesos",
        "budget_resolution_status",
        "physical_progress_pct",
        "zero_progress_flag",
        "status_raw",
        "infra_year",
        "category_raw",
        "standardized_sector",
        "taxonomy_version",
        "implementing_office",
        "implementing_office_resolution_status",
    ]:
        assert re.search(rf"\b{column}\b", table), column


def test_17_no_current_time_or_random_identity_in_rules():
    for path in [COMPONENT, PROJECT]:
        text = sql(path).upper()
        for forbidden in [
            "CURRENT_DATE",
            "CURRENT_TIMESTAMP",
            "NOW()",
            "UUID(",
            "RAND(",
            "MONOTONICALLY",
        ]:
            assert forbidden not in text, f"{path.name} {forbidden}"
    validation = sql(VALIDATION).upper()
    assert validation.count("CURRENT_TIMESTAMP()") == 1
    assert "UUID(" not in validation


def test_18_no_status_or_category_rule_written_in_silver_sql():
    for path in [COMPONENT, PROJECT]:
        text = sql(path)
        assert "'Delayed'" not in text
        assert not re.search(r"'[^']*'\s+AS\s+(standardized_\w+|status_group)\b", text)
    text = sql(COMPONENT)
    for column in [
        "category.standardized_sector",
        "category.standardized_category",
        "status.standardized_status",
        "status.status_group",
    ]:
        assert column in text, column


def test_19_validator_covers_all_seven_attributes():
    text = sql(VALIDATION)
    found = set(
        re.findall(
            r"'(Completeness|Uniqueness|Validity|Accuracy|Consistency|Auditability|Timeliness)'",
            text,
        )
    )
    assert found == SEVEN_ATTRIBUTES


def test_20_validator_scores_every_check_the_same_way():
    text = sql(VALIDATION)
    assert text.count("WHEN checks.failed_rows = 0 THEN 'PASS'") == 1
    actions = set(re.findall(r"'(stop|flag|warn|review|proceed)'", text))
    assert actions == {"stop", "flag"}


def test_21_validator_saves_evidence_before_the_gate():
    text = sql(VALIDATION)
    merge = text.index("MERGE INTO `04-validation`.silver_dq_results")
    gate = text.index("blocking Silver project checks failed")
    assert merge < gate


def test_22_validator_has_no_duplicate_code_cells():
    sources = [
        "".join(cell["source"])
        for cell in cells(VALIDATION)
        if cell["cell_type"] == "code"
    ]
    assert len(sources) == len(set(sources))


def test_23_validator_scans_each_table_once_for_metrics():
    metrics = statement(
        VALIDATION, "CREATE OR REPLACE TEMPORARY VIEW silver_project_validation_metrics"
    )
    assert metrics.count("FROM `02-silver`.silver_dpwh_project_component") == 1
    assert metrics.count("FROM `02-silver`.silver_project") == 1
    assert metrics.count("FROM `01-bronze`.dpwh_projects") == 1


def test_24_component_carries_deo_and_hashes_it():
    text = sql(COMPONENT)
    assert "'deo', bronze.deo" in text
    assert "identified_rows.deo," in text
    assert "'silver_dpwh_component_v3' AS transformation_rule_version" in text
    build = statement(
        COMPONENT, "CREATE OR REPLACE TABLE `02-silver`.silver_dpwh_project_component"
    )
    assert "component.deo," in build


def test_25_project_resolves_implementing_office_like_other_attributes():
    resolution = statement(
        PROJECT, "CREATE OR REPLACE TEMPORARY VIEW project_attribute_resolution"
    )
    expression = "COUNT(DISTINCT NULLIF(TRIM(deo), ''))"
    assert f"{expression} AS distinct_implementing_office_count" in resolution
    assert f"WHEN {expression} = 0 THEN 'MISSING'" in resolution
    assert f"WHEN {expression} = 1 THEN 'RESOLVED'" in resolution
    assert "END AS implementing_office_resolution_status" in resolution


def test_26_validator_checks_implementing_office_resolution():
    text = sql(VALIDATION)
    assert "implementing_office_resolution_status = 'CONFLICT'" in text
    assert "'Implementing office follows the resolution rule'" in text
    assert "'Missing or conflicting implementing offices remain visible'" in text
    assert "silver_project_validation_v2" not in text
