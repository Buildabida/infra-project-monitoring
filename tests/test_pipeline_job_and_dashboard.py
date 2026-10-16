import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "resources/buildabida_full_pipeline.job.yml"
DASHBOARD = ROOT / "dashboard/buildabida_infrastructure_project_monitoring.lvdash.json"
WORKSPACE_PREFIX = "/Workspace/Shared/infra-project-monitoring/"

SIX_VIEWS = {
    "analytics_investment_distribution",
    "analytics_population_equity",
    "analytics_flood_alignment",
    "analytics_implementation_monitoring",
    "analytics_infrastructure_network",
    "analytics_integration_coverage",
}
BOUNDARY_TABLES = {"dim_region_boundary", "dim_province_reporting_area_boundary"}
TABS = [
    "Overview: What did we find?",
    "Where does the money go?",
    "Does the money match where people live?",
    "Are flood-control projects where the floods are?",
    "Which projects need a closer look?",
    "What patterns show when we map all projects?",
    "What can we see only after connecting the data?",
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
    assert len(tasks) == 49
    assert len(keys) == len(set(keys))
    for index, (key, depends, _) in enumerate(tasks):
        for dependency in depends:
            assert dependency in keys[:index], (key, dependency)


def test_job_notebook_paths_exist_in_the_repo():
    for key, _, path in job_tasks():
        if path is None:
            assert key == "business_dashboard"
            continue
        assert path.startswith(WORKSPACE_PREFIX), key
        relative = ROOT / path.removeprefix(WORKSPACE_PREFIX)
        found = [relative.with_suffix(suffix) for suffix in (".ipynb", ".py", ".sql")]
        assert any(candidate.exists() for candidate in found), (key, path)


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
    assert depends["business_dashboard"] == {"analytics_validation"}


def test_job_is_not_included_in_the_bundle():
    # deploying the bundle must not create a second copy of the workspace job
    assert "include" not in (ROOT / "databricks.yml").read_text(encoding="utf-8")


def dashboard():
    return json.loads(DASHBOARD.read_text(encoding="utf-8"))


def test_dashboard_has_the_seven_tabs_in_order():
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


def test_dashboard_uses_the_violet_theme_and_plain_text():
    text = DASHBOARD.read_text(encoding="utf-8")
    theme = dashboard()["uiSettings"]["theme"]
    assert theme["widgetBorderColor"]["light"] == "#C4B5FD"
    assert theme["visualizationColors"][0] == "#7C3AED"
    assert "—" not in text
