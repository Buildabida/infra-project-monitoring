# Docs

Start here to find any doc about our pipeline. We draft in the team Google Doc first, then keep the final version here.

| If you need to | Read |
| --- | --- |
| Set up Databricks and run the first notebooks | [Quickstart](../README.md#quickstart) |
| Know what each table holds and its key | [Data model](data-model.md) |
| Know what Bronze and implemented Silver checks do | [Data-quality checks](validation.md) |
| Review Silver mapping tables and approval rules | [Silver configuration mappings](silver_config_mappings.md) |
| Review PSGC, Table C reconciliation, and region population | [Silver geography and population](silver_geography_population.md) |
| Review DPWH component preservation, project consolidation, budget protection, and project validation | silver_project_cleaning.md |
| Know why we chose something | [Decisions](decisions.md) |
| Write docs, SQL or Python the way we do | [Style guide](style-guide.md) |
| Make a change, write an issue or open a pull request | [How we work](../CONTRIBUTING.md) |
| Set up VS Code and run your first notebook | [Set up VS Code](vscode-setup.md) |
| See what each notebook folder does | [Notebooks guide](../notebooks/README.md) |
| Understand Bronze purpose, step-by-step mechanics, snapshots, provenance, cost and recovery | [Bronze R2 architecture](bronze_r2_architecture.md) |
| Review optional cleanup after migration | [Bronze cleanup plan](bronze_cleanup_plan.md) |

The current source contracts and provenance limits are in the
[Bronze R2 provenance table](bronze_r2_architecture.md#six-sources-and-provenance).
Add separate source cards only when the team has approved stronger source evidence.

## Keep our docs clean

- Keep each fact in one place. Link to it instead of copying it.
- Update the docs in the same pull request as the code.
- If a doc and the code disagree, fix one of them before you merge.
- Don't rewrite an old decision. Add a new decision that replaces it.
- Keep old proof. Add new proof with its own date instead of changing an old result.
- When documenting evidence, name the artifact, snapshot ID, check, and result so another
  engineer can trace the claim.
