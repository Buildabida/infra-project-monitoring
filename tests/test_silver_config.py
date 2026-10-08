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


def test_status_config_does_not_seed_delayed_or_derived_rules():
    sql = notebook_text(CONFIG_NOTEBOOK)
    assert "MERGE INTO `02-silver`.config_project_status_mapping" not in sql
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
    assert sql.count("MERGE INTO `02-silver`.") == 1
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
