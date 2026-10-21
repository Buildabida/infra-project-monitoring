# Dashboard

The capstone dashboard has five visible pages: Overview, three business-question
pages, and Read Me. The [dashboard specification](dashboard_spec.md) lists every
page, dataset group, check value, and rule that each dataset follows.

The canonical export is
[`buildabida_infrastructure_project_monitoring.lvdash.json`](buildabida_infrastructure_project_monitoring.lvdash.json).
It is based on the latest live export supplied on October 21, 2026. It reads
only the Analytics views and the two Gold boundary tables. The exact live file
and the changes made to enforce that serving contract are retained in the
[dev-bundle evidence](../docs/evidence/dev-bundle-2026-10-21/README.md#dashboard-export).

- Refresh the dashboard only after `04_validation/10_validation_analytics` and the [end-to-end quality gate](../notebooks/06_data_quality/README.md) pass. The `business_dashboard` task of the [pipeline job](../resources/buildabida_full_pipeline.job.yml) waits for both.
- The job refreshes the dashboard by its ID, `dashboard_id` in [`databricks.yml`](../databricks.yml). If you import the dashboard into another workspace, pass the new ID with `--var`.
- After you change the dashboard, export it again (**File**, then **Export**) and replace the file here, so the repo has the latest version. Replace any long dash in the text with a colon, because `tests/test_pipeline_job_and_dashboard.py` checks for plain text.
- Keep the export in step with the spec. If they disagree, fix one of them before you merge.
- Keep ordinary design-review screenshots in the team Drive. Put screenshots
  in the repository only when they are required runtime or acceptance evidence
  and have an evidence page that explains them.
