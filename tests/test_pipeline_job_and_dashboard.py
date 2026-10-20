import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "resources/buildabida_full_pipeline.job.yml"
DASHBOARD = ROOT / "dashboard/buildabida_infrastructure_project_monitoring.lvdash.json"
BUNDLE = ROOT / "databricks.yml"

SIX_VIEWS = {
    "analytics_investment_distribution",
    "analytics_population_equity",
    "analytics_flood_alignment",
    "analytics_implementation_monitoring",
    "analytics_infrastructure_network",
    "analytics_integration_coverage",
}
BOUNDARY_TABLES = {"dim_region_boundary", "dim_province_reporting_area_boundary"}
# the mentor review asked for one overview and one tab per analytics question,
# plus the Read Me page
TABS = [
    "Overview",
    "AQ1: Where is the money going?",
    "AQ2: What are we building?",
    "AQ3: Who are we leaving behind?",
    "Read Me",
]


def job_tasks():
    # the ci installs only pytest, so read the task list without a yaml parser
    tasks = []
    for block in re.split(r"\n        - task_key: ", JOB.read_text(encoding="utf-8"))[
        1:
    ]:
        key = block.split("\n", 1)[0].strip()
        depends = re.findall(r"\n            - task_key: (\w+)", block)
        path = re.search(r"notebook_path: (\S+)", block)
        tasks.append((key, depends, path.group(1) if path else None))
    return tasks


def test_job_tasks_are_unique_and_depend_only_on_earlier_tasks():
    tasks = job_tasks()
    keys = [key for key, _, _ in tasks]
    assert len(tasks) == 50
    assert len(keys) == len(set(keys))
    for index, (key, depends, _) in enumerate(tasks):
        for dependency in depends:
            assert dependency in keys[:index], (key, dependency)


def test_job_notebook_paths_exist_in_the_repo():
    # the bundle deploys the notebooks it points at, so no manual workspace sync
    for key, _, path in job_tasks():
        if path is None:
            assert key == "business_dashboard"
            continue
        assert path.startswith("../notebooks/"), key
        assert (JOB.parent / path).resolve().is_file(), (key, path)


def test_job_runs_every_gate_before_the_layer_that_needs_it():
    depends = {key: set(dependencies) for key, dependencies, _ in job_tasks()}
    assert (
        "silver_validation_province_reporting" in depends["gold_fact_project_snapshot"]
    )
    assert "gold_dim_province_reporting_area" in depends["gold_fact_project_snapshot"]
    assert "gold_validation" in depends["gold_validation_province_reporting"]
    assert depends["analytics"] == {
        "gold_validation",
        "gold_validation_province_reporting",
    }
    assert depends["analytics_validation"] == {"analytics"}
    assert depends["publish_acceptance_evidence"] == {"analytics_validation"}
    assert depends["end_to_end_quality_gate"] == {"publish_acceptance_evidence"}
    # the dashboard needs the gate and must never bypass it
    assert depends["business_dashboard"] == {
        "analytics_validation",
        "publish_acceptance_evidence",
        "end_to_end_quality_gate",
    }


def test_quality_gate_runs_after_any_failure_and_records_the_job_run():
    text = JOB.read_text(encoding="utf-8")
    task = "\n        - task_key: "
    gate = text.split(f"{task}end_to_end_quality_gate", 1)[1].split(task)[0]
    assert "run_if: ALL_DONE" in gate
    assert 'job_run_id: "{{job.run_id}}"' in gate
    dashboard = text.split("- task_key: business_dashboard", 1)[1]
    # the dashboard keeps the default ALL_SUCCESS, so a failed gate blocks it
    assert "run_if" not in dashboard


def test_job_alerts_on_failure_and_runs_one_at_a_time():
    text = JOB.read_text(encoding="utf-8")
    assert "max_concurrent_runs: 1" in text
    assert re.search(r"timeout_seconds: \d+", text)
    assert "on_failure:\n          - ${var.alert_email}" in text
    # no personal address or environment id is hardcoded in the job
    assert "@" not in text.replace("${var.alert_email}", "")
    assert "warehouse_id: ${var.warehouse_id}" in text
    assert "dashboard_id: ${var.dashboard_id}" in text


def test_bundle_includes_the_job_with_separate_dev_and_prod_targets():
    text = BUNDLE.read_text(encoding="utf-8")
    assert "include:\n  - resources/*.yml" in text
    dev = text.split("\n  dev:\n", 1)[1].split("\n  prod:\n", 1)[0]
    prod = text.split("\n  prod:\n", 1)[1]
    # development mode prefixes the job name and deploys under the user's home
    assert "mode: development" in dev
    assert "root_path" not in dev
    assert "mode: production" in prod
    assert "root_path: /Workspace/Shared/" in prod
    for name in ("warehouse_id", "dashboard_id", "alert_email"):
        assert f"\n  {name}:\n" in text, name


def dashboard():
    return json.loads(DASHBOARD.read_text(encoding="utf-8"))


def test_dashboard_has_the_overview_and_three_question_tabs_in_order():
    pages = [
        page["displayName"]
        for page in dashboard()["pages"]
        if page.get("pageType") == "PAGE_TYPE_CANVAS"
    ]
    assert pages == TABS


def test_dashboard_reads_only_the_six_views_and_gold_boundaries():
    for dataset in dashboard()["datasets"]:
        # a sql dataset keeps queryLines; a dashboard metric view keeps config.source
        sql = "".join(dataset.get("queryLines", [])) + dataset.get("config", {}).get(
            "source", ""
        )
        tables = set(re.findall(r"`buildabida-capstone`\.`([\w-]+)`\.(\w+)", sql))
        assert tables, dataset["name"]
        for schema, table in tables:
            if schema == "05-analytics":
                assert table in SIX_VIEWS, (dataset["name"], table)
            else:
                assert schema == "03-gold", (dataset["name"], schema)
                assert table in BOUNDARY_TABLES, (dataset["name"], table)


def test_dashboard_uses_one_theme_and_plain_text():
    text = DASHBOARD.read_text(encoding="utf-8")
    theme = dashboard()["uiSettings"]["theme"]
    assert theme["widgetBorderColor"]["light"]
    assert theme["visualizationColors"]
    assert "—" not in text
