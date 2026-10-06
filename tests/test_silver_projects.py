from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_project_component_notebook_exists():
    assert (
        ROOT / "notebooks" / "02_silver" / "04_silver_dpwh_project_component.ipynb"
    ).exists()


def test_project_notebook_exists():
    assert (ROOT / "notebooks" / "02_silver" / "05_silver_project.ipynb").exists()


def test_project_validation_notebook_exists():
    assert (
        ROOT / "notebooks" / "04_validation" / "04_validation_silver_projects.ipynb"
    ).exists()


def test_component_notebook_uses_try_cast():
    content = _read("notebooks/02_silver/04_silver_dpwh_project_component.ipynb")

    assert "TRY_CAST" in content


def test_project_contains_budget_resolution_status():
    content = _read("notebooks/02_silver/05_silver_project.ipynb")

    assert "budget_resolution_status" in content


def test_project_contains_component_count():
    content = _read("notebooks/02_silver/05_silver_project.ipynb")

    assert "component_count" in content


def test_project_uses_left_join():
    content = _read("notebooks/02_silver/05_silver_project.ipynb")

    assert "LEFT JOIN" in content.upper()


def test_no_drop_table_in_component_notebook():
    content = _read("notebooks/02_silver/04_silver_dpwh_project_component.ipynb")

    assert "DROP TABLE" not in content.upper()


def test_no_drop_table_in_project_notebook():
    content = _read("notebooks/02_silver/05_silver_project.ipynb")

    assert "DROP TABLE" not in content.upper()


def test_validation_contains_assert_true():
    content = _read("notebooks/04_validation/04_validation_silver_projects.ipynb")

    assert "ASSERT_TRUE" in content


def test_validation_contains_lineage_checks():
    content = _read("notebooks/04_validation/04_validation_silver_projects.ipynb")

    assert "_source_snapshot_id" in content
