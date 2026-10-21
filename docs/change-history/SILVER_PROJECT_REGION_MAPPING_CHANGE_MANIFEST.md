# Silver project-region mapping change manifest

## Added

| File | Purpose |
| --- | --- |
| `notebooks/02_silver/08_silver_project_region_map.ipynb` | Publish one deterministic governed region-mapping result per canonical project |
| `notebooks/04_validation/06_validation_silver_project_region_map.ipynb` | Persist all seven DQ attributes before enforcing the Table 13 gate |
| `tests/test_silver_project_region_map.py` | Protect dependencies, grain, precedence, Central Office, spatial cost, identity, validation, and scope |
| `docs/silver_project_region_mapping.md` | Document business purpose, D-03 resolution, waterfall, boundaries, lineage, validation, cost, and Gold handoff |
| `SILVER_PROJECT_REGION_MAPPING_REVIEW_SUMMARY.md` | Record baseline, verified contracts, local profiling, design review, runtime boundary, and handoff |
| `SILVER_PROJECT_REGION_MAPPING_CHANGE_MANIFEST.md` | List files and milestone scope |

## Updated

| File | Change |
| --- | --- |
| `README.md` | Mark project-region mapping implemented and link its contract |
| `docs/README.md` | Add project-region mapping navigation |
| `docs/data-model.md` | Mark Table 13 implemented and document its actual grain and fields |
| `docs/validation.md` | Add Table 13 DQ attributes, STOP and FLAG behavior, persistence, and run order |
| `docs/decisions.md` | Add D-31 and move the preserved D-03 question to resolved |
| `docs/silver_project_cleaning.md` | Link the implemented follow-up and update dependency and Gold handoff status |
| `notebooks/README.md` | Add Table 13 and validator to the sequence and document exact dependency-aware execution |

## Unchanged by design

- Bronze ingestion logic and Bronze business values
- Existing Silver Tables 1 through 12
- D-04 and source-reconciliation behavior
- project-flood mapping and regional flood-exposure outputs
- Gold facts and dimensions
- dashboard and Genie assets

## Verification

The transformation and validation notebooks were executed successfully in
Databricks against the selected Unity Catalog tables.

Runtime validation confirmed:

- 265,656 canonical project rows
- 265,656 project-region mapping rows
- row-preservation difference of 0
- 18 blocking STOP checks passed
- 0 blocking failures

Validation evidence was persisted to
`04-validation.silver_dq_results`.

The final repository suite contains 164 passing tests. Ruff, SQLFluff,
Markdown layout, links, and Vale also pass.
