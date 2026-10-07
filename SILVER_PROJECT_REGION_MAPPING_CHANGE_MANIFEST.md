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

## Verification boundary

Static repository tests and linters are executed locally. Unity Catalog table
creation requires Databricks execution. Spatial coverage and validation
outcomes also require Databricks, so no runtime result total is claimed.

The final local suite contains 164 passing tests. Ruff, SQLFluff, Markdown
layout, offline local links, and Vale complete without errors or warnings.
