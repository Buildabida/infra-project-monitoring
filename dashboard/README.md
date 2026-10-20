# Dashboard

The capstone dashboard has four tabs: an overview, then one tab per analytics question, plus a Read Me page. The [dashboard specification](dashboard_spec.md) lists every tab, dataset, and check value, and the rules every dataset follows.

The exported dashboard is [`buildabida_infrastructure_project_monitoring.lvdash.json`](buildabida_infrastructure_project_monitoring.lvdash.json), from October 20, 2026. It reads only the six Analytics views and the two Gold boundary tables.

- Refresh the dashboard only after `04_validation/10_validation_analytics` and the [end-to-end quality gate](../notebooks/06_data_quality/README.md) pass. The `business_dashboard` task of the [pipeline job](../resources/buildabida_full_pipeline.job.yml) waits for both.
- The job refreshes the dashboard by its ID, `dashboard_id` in [`databricks.yml`](../databricks.yml). If you import the dashboard into another workspace, pass the new ID with `--var`.
- After you change the dashboard, export it again (**File**, then **Export**) and replace the file here, so the repo has the latest version. Replace any long dash in the text with a colon, because `tests/test_pipeline_job_and_dashboard.py` checks for plain text.
- Keep the export in step with the spec. If they disagree, fix one of them before you merge.
- Put screenshots in our Drive folder, not here.
