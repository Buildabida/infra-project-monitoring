# Docs

Start here to find any doc about our pipeline. We draft in the team Google Doc first, then keep the final version here.

| If you need to | Read |
| --- | --- |
| Set up Databricks and run the first notebooks | [Quickstart](../README.md#quickstart) |
| Know what each table holds and its key | [Data model](model/data-model.md) |
| Know what the Bronze, Silver, Gold, and Analytics checks do | [Data-quality checks](validation/validation.md) |
| Review Silver mapping tables and approval rules | [Silver configuration mappings](silver/silver_config_mappings.md) |
| Review PSGC, Table C reconciliation, and region population | [Silver geography and population](silver/silver_geography_population.md) |
| Review DPWH component preservation, project consolidation, budget protection, and project validation | [Silver project foundation](silver/silver_project_cleaning.md) |
| Review flood-list component preservation, exact Contract-ID matching, cost protection, and reconciliation validation | [Silver source reconciliation](silver/silver_source_reconciliation.md) |
| Review project-to-region precedence, Central Office handling, spatial fallback, conflicts, lineage, and validation | [Silver project-to-region mapping](silver/silver_project_region_mapping.md) |
| Review the approved D-57 reporting-area policy, implementation status, runtime checklist, and flood deferral | [Province reporting readiness and production status](silver/province_reporting_readiness.md) |
| Review project-to-reporting-area precedence, configuration, spatial rules, lineage, and validation | [Silver project-to-reporting-area mapping](silver/silver_project_province_mapping.md) |
| Review the completed D-57 Databricks acceptance and exact-rerun results | [Province-reporting runtime evidence](evidence/province-reporting/README.md) |
| Review the first Databricks run of the Analytics views and the v2 province validators | [Analytics evidence](evidence/analytics-2026-10-16/README.md) |
| Review the parsed MGB flood polygons (`silver_mgb_flood_area`), the Esri parser, the skip rule, and validation | [Silver MGB flood areas](silver/silver_mgb_flood_area.md) |
| Review regional MGB flood exposure, the equal-area CRS, zero versus no data, overlap, lineage, and validation | [Silver regional flood exposure](silver/silver_region_flood_exposure.md) |
| Review project-to-MGB flood classification (`silver_project_flood_map`), ambiguity without severity precedence, lineage, and validation | [Silver project flood mapping](silver/silver_project_flood_mapping.md) |
| Review Databricks evidence for Silver fixes | [Silver validation evidence](evidence/silver/README.md) |
| Know what each Analytics view answers, its grain, and its limits | [Analytics views](../notebooks/05_analytics/README.md) |
| Review the four-tab dashboard, its datasets, and its check values | [Dashboard specification](../dashboard/dashboard_spec.md) |
| Run the full pipeline as one Databricks job, and deploy it with the bundle | [Pipeline job](../resources/README.md) |
| Monitor a run, get failure emails, recover with Repair run, and set up GitHub | [Operations guide](guides/operations.md) |
| Know what the end-to-end quality gate checks and how to read its result | [Quality gate](../notebooks/06_data_quality/README.md) |
| Know what each Gold fact and dimension holds, its grain, and its keys | [Gold model](model/gold_model.md) |
| Test the README from a new workspace | [Clean-workspace test](guides/clean_workspace_test.md) |
| See how the pipeline handles a new source pull or changed columns | [Update resilience](guides/update_resilience.md) |
| Read old change manifests, review summaries, and handoffs | [Change history](change-history/README.md) and [handoffs](handoffs/README.md) |
| Know why we chose something | [Decisions](decisions.md) |
| Write docs, SQL or Python the way we do | [Style guide](style-guide.md) |
| Make a change, write an issue or open a pull request | [How we work](../CONTRIBUTING.md) |
| Set up VS Code and run your first notebook | [Set up VS Code](guides/vscode-setup.md) |
| See what each notebook folder does | [Notebooks guide](../notebooks/README.md) |
| Understand Bronze purpose, step-by-step mechanics, snapshots, provenance, cost and recovery | [Bronze R2 architecture](bronze/bronze_r2_architecture.md) |
| Review optional cleanup after migration | [Bronze cleanup plan](bronze/bronze_cleanup_plan.md) |

The current source contracts and provenance limits are in the
[Bronze R2 provenance table](bronze/bronze_r2_architecture.md#six-sources-and-provenance).
Add separate source cards only when the team has approved stronger source evidence.

## Keep our docs clean

- Keep each fact in one place. Link to it instead of copying it.
- Update the docs in the same pull request as the code.
- If a doc and the code disagree, fix one of them before you merge.
- Don't rewrite an old decision. Add a new decision that replaces it.
- Keep old proof. Add new proof with its own date instead of changing an old result.
- When documenting evidence, name the artifact, snapshot ID, check, and result so another
  engineer can trace the claim.
