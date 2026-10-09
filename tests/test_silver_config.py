import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_NOTEBOOK = REPO_ROOT / "notebooks/02_silver/00_config_mappings.ipynb"
VALIDATION_NOTEBOOK = (
    REPO_ROOT / "notebooks/04_validation/02_validation_silver_config.ipynb"
)

CONFIG_TABLES = {
    "config_place_name_alias": {
        "source_system",
        "raw_place_name",
        "raw_region_name",
        "raw_province_name",
        "raw_city_municipality_name",
        "place_type",
        "canonical_psgc_code",
        "alias_version",
        "approval_status",
        "is_active",
    },
    "config_project_category_mapping": {
        "source_system",
        "raw_category",
        "source_infra_type",
        "standardized_sector",
        "is_flood_related",
        "taxonomy_version",
        "approval_status",
        "is_active",
    },
    "config_project_status_mapping": {
        "source_system",
        "source_status",
        "standardized_status",
        "status_mapping_version",
        "approval_status",
        "is_active",
    },
    "config_mgb_susceptibility_mapping": {
        "source_system",
        "raw_susceptibility_code",
        "standardized_level",
        "severity_rank",
        "source_version",
        "mapping_version",
        "approval_status",
        "is_active",
    },
    "config_manual_geographic_match": {
        "source_system",
        "record_type",
        "source_record_id",
        "canonical_psgc_code",
        "override_reason",
        "mapping_version",
        "approval_status",
        "is_active",
    },
}


def load_notebook(path):
    return json.loads(path.read_text(encoding="utf-8"))


def notebook_text(path):
    notebook = load_notebook(path)
    return "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])


def code_cells(path):
    notebook = load_notebook(path)
    return [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    ]


def create_table_block(sql, table_name):
    pattern = (
        rf"CREATE TABLE IF NOT EXISTS `02-silver`\.{table_name}\s*\((.*?)\)\s*"
        r"USING DELTA"
    )
    match = re.search(pattern, sql, flags=re.DOTALL | re.IGNORECASE)
    assert match, f"Missing CREATE TABLE block for {table_name}"
    return match.group(1).lower()


def test_notebooks_are_valid_nbformat_json():
    for path in (CONFIG_NOTEBOOK, VALIDATION_NOTEBOOK):
        notebook = load_notebook(path)
        assert notebook["nbformat"] == 4
        assert notebook["cells"]
        assert all(
            cell["cell_type"] in {"markdown", "code"} for cell in notebook["cells"]
        )


def test_five_config_tables_and_required_columns_are_declared():
    sql = notebook_text(CONFIG_NOTEBOOK)

    for table_name, required_columns in CONFIG_TABLES.items():
        block = create_table_block(sql, table_name)
        for column in required_columns:
            assert re.search(rf"\b{column}\b", block), (
                f"{table_name} is missing {column}"
            )


def test_natural_key_validation_exists_for_every_table():
    sql = notebook_text(VALIDATION_NOTEBOOK).lower()
    expected_groups = (
        "source_system, raw_place_name, raw_region_name",
        "source_system, raw_category, source_infra_type, taxonomy_version",
        "source_system, source_status, status_mapping_version",
        "source_system, raw_susceptibility_code, source_version, mapping_version",
        "source_system, record_type, source_record_id, mapping_version",
    )

    for group in expected_groups:
        assert group in sql


def test_approval_states_and_versions_are_validated():
    sql = notebook_text(VALIDATION_NOTEBOOK)
    for status in ("APPROVED", "PENDING_REVIEW", "DEPRECATED"):
        assert status in sql

    for version_column in (
        "alias_version",
        "taxonomy_version",
        "status_mapping_version",
        "mapping_version",
        "source_version",
    ):
        assert version_column in sql


def test_only_verified_mgb_rules_are_seeded_with_expected_ranks():
    seed_cell = next(
        cell
        for cell in code_cells(CONFIG_NOTEBOOK)
        if "config_mgb_susceptibility_mapping AS target" in cell
    )
    expected = {
        "LF": ("Low", 1),
        "MF": ("Moderate", 2),
        "HF": ("High", 3),
        "VHF": ("Very High", 4),
    }

    for code, (level, rank) in expected.items():
        pattern = rf"'{code}',\s*'{level}',\s*{rank}\b"
        assert re.search(pattern, seed_cell)

    assert "No rating" not in seed_cell
    assert "PENDING_REVIEW" not in seed_cell


def test_only_approved_dpwh_status_rules_are_seeded():
    seed_cell = next(
        cell
        for cell in code_cells(CONFIG_NOTEBOOK)
        if "config_project_status_mapping AS target" in cell
    )
    expected = {
        "Completed": ("Completed", "FINISHED"),
        "On-Going": ("Ongoing", "ACTIVE"),
        "For Procurement": ("Ongoing", "ACTIVE"),
        "Not Yet Started": ("Inactive", "INACTIVE"),
        "Terminated": ("Inactive", "INACTIVE"),
    }

    assert len(re.findall(r"\('dpwh_projects',", seed_cell)) == len(expected)
    for source_status, (standardized, group) in expected.items():
        pattern = (
            rf"\('dpwh_projects',\s*'{source_status}',\s*'{standardized}',"
            rf"\s*'{group}'\)"
        )
        assert re.search(pattern, seed_cell), source_status

    assert "'dpwh-status-2026-10-v1' AS status_mapping_version" in seed_cell
    assert "'APPROVED' AS approval_status" in seed_cell
    assert "TRUE AS is_active" in seed_cell
    assert "'DPWH'" not in seed_cell
    assert "PENDING_REVIEW" not in seed_cell


def test_dpwh_region_aliases_are_approved_and_use_the_config_key():
    seed_cell = next(
        cell
        for cell in code_cells(CONFIG_NOTEBOOK)
        if "config_place_name_alias AS target" in cell
    )

    assert "'dpwh_projects' AS source_system" in seed_cell
    assert "'REGION' AS place_type" in seed_cell
    assert "'dpwh-region-aliases-2026-10-v1' AS alias_version" in seed_cell
    assert "'APPROVED' AS approval_status" in seed_cell
    assert "'Buildabida' AS approved_by" in seed_cell
    assert "TIMESTAMP '2026-10-09 00:00:00' AS approved_at" in seed_cell
    assert "PENDING_REVIEW" not in seed_cell
    assert len(re.findall(r"\('[^']+', '\d{10}', '[^']+'\)", seed_cell)) == 17
    assert "('Region IV-B', '1700000000', 'MIMAROPA Region')" in seed_cell
    assert "'MIMAROPA Region', '1700000000'" not in seed_cell
    assert "Poblacion" not in seed_cell


def test_place_alias_coverage_matches_region_place_type_case_insensitively():
    coverage_cell = next(
        cell for cell in code_cells(CONFIG_NOTEBOOK) if "raw_place_alias AS (" in cell
    )

    assert "'dpwh_projects' AS source_system" in coverage_cell
    assert "UPPER(TRIM(mapping.place_type)) = 'REGION'" in coverage_cell


def test_status_config_does_not_seed_delayed_or_derived_rules():
    sql = notebook_text(CONFIG_NOTEBOOK)
    assert not re.search(r"'(Delayed|Stalled|Long-running)'", sql, flags=re.IGNORECASE)
    assert not re.search(
        r"VALUES\s*\([^)]*'Delayed'", sql, flags=re.DOTALL | re.IGNORECASE
    )


def test_manual_override_table_is_allowed_to_start_empty():
    sql = notebook_text(CONFIG_NOTEBOOK)
    assert "MERGE INTO `02-silver`.config_manual_geographic_match" not in sql
    assert "INSERT INTO `02-silver`.config_manual_geographic_match" not in sql
    assert "An empty table is allowed" in notebook_text(VALIDATION_NOTEBOOK)


def test_rerun_path_does_not_blindly_append_config_rows():
    sql = notebook_text(CONFIG_NOTEBOOK)
    assert sql.count("MERGE WITH SCHEMA EVOLUTION INTO `02-silver`.") == 1
    assert sql.count("MERGE INTO `02-silver`.") == 3
    assert "CREATE TABLE IF NOT EXISTS" in sql
    assert "INSERT INTO `02-silver`.config_" not in sql


def test_dpwh_component_category_taxonomy_is_seeded_and_versioned():
    sql = notebook_text(CONFIG_NOTEBOOK)
    expected_categories = {
        "Bridges",
        "Buildings and Facilities",
        "Consultancy",
        "Flood Control and Drainage",
        "Roads",
        "Septage and Sewerage Plants",
        "Water Provision and Storage",
    }

    assert "dpwh-component-categories-2026-10-v1" in sql
    for category in expected_categories:
        assert f"'{category}'" in sql

    assert re.search(
        r"'Flood Control and Drainage',\s*'Flood Control and Drainage',\s*"
        r"'Flood Control and Drainage',\s*TRUE",
        sql,
    )
    assert "Exact normalized componentCategories token" in sql


def test_project_category_coverage_uses_only_active_approved_rules():
    coverage_cell = next(
        cell
        for cell in code_cells(CONFIG_NOTEBOOK)
        if "raw_dpwh_component_category AS (" in cell
    )

    assert "mapping.approval_status = 'APPROVED'" in coverage_cell
    assert "mapping.is_active = TRUE" in coverage_cell


def test_config_validator_protects_dpwh_taxonomy_selection_and_fanout():
    sql = notebook_text(VALIDATION_NOTEBOOK)
    assert "exactly one active approved DPWH taxonomy version" in sql
    assert "DPWH category rules cannot fan out one source classification" in sql
    assert "approved DPWH category targets and flood markers are complete" in sql


def test_notebooks_never_write_bronze_or_gold_or_run_spatial_logic():
    sql = notebook_text(CONFIG_NOTEBOOK) + "\n" + notebook_text(VALIDATION_NOTEBOOK)
    write_pattern = re.compile(
        r"(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE\s+INTO|"
        r"CREATE\s+(?:OR\s+REPLACE\s+)?TABLE)\s+`01-bronze`",
        flags=re.IGNORECASE,
    )
    assert not write_pattern.search(sql)
    assert "`03-gold`" not in sql

    for spatial_operation in ("ST_Intersects", "ST_Contains", "ST_Within"):
        assert spatial_operation not in sql


def test_major_sql_sections_have_explanatory_markdown():
    for path in (CONFIG_NOTEBOOK, VALIDATION_NOTEBOOK):
        cells = load_notebook(path)["cells"]
        for index, cell in enumerate(cells):
            source = "".join(cell.get("source", []))
            if cell["cell_type"] == "code" and (
                "CREATE TABLE" in source or "CREATE OR REPLACE TEMPORARY VIEW" in source
            ):
                assert index > 0
                assert cells[index - 1]["cell_type"] == "markdown"
