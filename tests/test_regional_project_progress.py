import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW_NOTEBOOK = ROOT / "notebooks/05_analytics/02_regional_project_progress.ipynb"
VALIDATION_NOTEBOOK = (
    ROOT / "notebooks/04_validation/11_validation_regional_project_progress.ipynb"
)
DECISIONS = ROOT / "docs/decisions.md"


def notebook(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source(path, cell_type):
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook(path)["cells"]
        if cell["cell_type"] == cell_type
    )


def sql(path):
    return source(path, "code")


def squash(value):
    return " ".join(value.split())


def assert_sql_notebook(path):
    data = notebook(path)
    assert data["nbformat"] == 4
    assert data["nbformat_minor"] >= 5
    metadata = data["metadata"]["application/vnd.databricks.v1+notebook"]
    assert metadata["language"] == "sql"
    assert metadata["notebookName"] == path.stem
    ids = [cell["id"] for cell in data["cells"]]
    assert len(ids) == len(set(ids))
    assert data["cells"][0]["cell_type"] == "markdown"
    for index, cell in enumerate(data["cells"]):
        if cell["cell_type"] == "code":
            assert "".join(cell["source"]).startswith("%sql\n")
            assert cell["outputs"] == []
            assert data["cells"][index - 1]["cell_type"] == "markdown"


def test_notebooks_are_valid_databricks_sql_notebooks():
    assert_sql_notebook(VIEW_NOTEBOOK)
    assert_sql_notebook(VALIDATION_NOTEBOOK)


def test_view_is_a_single_low_cost_analytics_contract():
    code = sql(VIEW_NOTEBOOK)
    assert code.count("CREATE OR REPLACE VIEW `05-analytics`.") == 1
    assert "`05-analytics`.analytics_region_project_progress" in code
    schemas = set(re.findall(r"`(\d\d-[a-z]+)`\.", code))
    assert schemas == {"03-gold", "05-analytics"}
    for forbidden in [
        "CREATE TABLE",
        "MERGE INTO",
        "INSERT INTO",
        "%python",
        "ST_DISTANCE",
        "LEVENSHTEIN",
    ]:
        assert forbidden not in code


def test_view_uses_real_gold_snapshots_not_infrastructure_year():
    code = squash(sql(VIEW_NOTEBOOK))
    assert "FROM `03-gold`.fact_project_snapshot" in code
    assert "WHERE fact.is_current_snapshot = TRUE" in code
    assert "WHERE is_current_snapshot = 0 QUALIFY ROW_NUMBER() OVER" in code
    assert (
        "ORDER BY snapshot_date_key DESC, source_load_ts DESC, source_snapshot_id DESC"
        in code
    )
    assert "infra_year" not in code


def test_transition_join_preserves_one_project_and_is_order_independent():
    code = squash(sql(VIEW_NOTEBOOK))
    assert (
        "FULL OUTER JOIN previous_projects AS previous ON current.project_key = previous.project_key"
        in code
    )
    assert (
        "GROUP BY COALESCE(current.psgc_region_code, previous.psgc_region_code)" in code
    )
    assert (
        "COUNT_IF(current.project_key IS NOT NULL AND previous.project_key IS NULL)"
        in code
    )
    assert (
        "COUNT_IF(current.project_key IS NULL AND previous.project_key IS NOT NULL)"
        in code
    )
    assert "project_key" in code
    assert "source_row_number" not in code


def test_no_prior_snapshot_is_null_not_zero():
    code = squash(sql(VIEW_NOTEBOOK))
    assert "THEN 'NO_PRIOR_SNAPSHOT'" in code
    for field in [
        "previous_project_count",
        "project_count_change",
        "status_changed_count",
        "moved_to_finished_count",
        "progress_increased_count",
        "new_project_count",
    ]:
        assert field in code
    assert code.count("WHEN context.previous_source_snapshot_id IS NOT NULL") >= 10
    assert "COALESCE(previous.project_count, 0) AS previous_project_count" not in code


def test_status_contract_is_explicit_and_does_not_claim_delay():
    text = source(VIEW_NOTEBOOK, "markdown") + sql(VIEW_NOTEBOOK)
    for status in ["FINISHED", "ACTIVE", "INACTIVE"]:
        assert status in text
    assert "ACTIVE includes For Procurement" in text
    assert "does not necessarily mean construction is under way" in text
    assert "delayed" not in text.lower()


def test_validation_persists_before_the_final_stop_gate():
    code = sql(VALIDATION_NOTEBOOK)
    assert "regional-project-progress-validation-v1" in code
    assert code.count("dq.pipeline_run_id = context.current_fact_run_id") >= 2
    assert "dq.source_snapshot_id = context.current_source_snapshot_id" in code
    assert "dq.table_name = 'analytics_regional_investment'" in code
    assert "MERGE INTO `04-validation`.analytics_dq_results AS target" in code
    merge = code.index("MERGE INTO `04-validation`.analytics_dq_results AS target")
    final_stop = code.rindex("SELECT ASSERT_TRUE(")
    assert merge < final_stop
    assert "WHEN MATCHED THEN UPDATE SET *" in code
    assert "WHEN NOT MATCHED THEN INSERT *" in code
    assert "CURRENT_TIMESTAMP() AS run_ts" in code


def test_validation_covers_grain_lineage_totals_and_no_prior_behavior():
    code = sql(VALIDATION_NOTEBOOK)
    for check_name in [
        "One row per official region",
        "One row per stable PSGC region code",
        "Every current official region stays visible",
        "Current regional measures rebuild from Gold",
        "Current mapped project total reconciles to Gold",
        "Current mapped reported budget reconciles to Gold",
        "Current snapshot lineage is exact",
        "No-prior workspace cannot publish historical zeros",
        "Previous snapshot lineage is exact when available",
        "Transition counts stay within project bounds",
    ]:
        assert check_name in code
    assert "A previous snapshot is available for comparison" in code
    assert "Projects with lower reported physical progress need review" in code


def test_d55_is_proposed_not_fabricated_as_approved():
    text = DECISIONS.read_text(encoding="utf-8")
    approved, proposed = text.split("## Proposed decisions awaiting team approval", 1)
    assert "| D-55 |" not in approved
    assert "| D-55 |" in proposed
    assert "Team approval is still required before merge" in proposed
