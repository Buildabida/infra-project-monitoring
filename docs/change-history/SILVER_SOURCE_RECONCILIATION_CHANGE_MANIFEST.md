# Silver source reconciliation change manifest

## Added

| File | Purpose |
| --- | --- |
| `notebooks/02_silver/06_silver_flood_control_component.ipynb` | Publish one typed, lineage-preserving component per selected Bronze flood source feature |
| `notebooks/02_silver/07_silver_project_source_match.ipynb` | Record exact Contract-ID matches, unmatched groups, and ambiguous targets without mutating projects |
| `notebooks/04_validation/05_validation_silver_source_reconciliation.ipynb` | Persist all seven DQ attributes before enforcing the source-reconciliation gate |
| `tests/test_silver_source_reconciliation.py` | Protect source boundaries, grain, exact matching, cost safety, lineage, and notebook structure |
| `docs/silver_source_reconciliation.md` | Document business purpose, contracts, rules, validation, limits, and handoff |
| `SILVER_SOURCE_RECONCILIATION_REVIEW_SUMMARY.md` | Record baseline, design review, source verification, and runtime handoff |
| `SILVER_SOURCE_RECONCILIATION_CHANGE_MANIFEST.md` | List files and scope in this milestone |

## Updated

| File | Change |
| --- | --- |
| `README.md` | Mark source reconciliation implemented and link its documentation |
| `docs/README.md` | Add navigation to project-foundation and source-reconciliation contracts |
| `docs/data-model.md` | Separate raw component evidence from project-source match evidence |
| `docs/validation.md` | Add source-reconciliation quality attributes, STOP and FLAG rules, and accounting equations |
| `docs/silver_project_cleaning.md` | Link the implemented follow-up milestone and update the handoff status |
| `notebooks/README.md` | Add execution order, implemented outputs, and future notebook numbering |

## Unchanged by design

- Bronze ingestion and Bronze tables
- Existing Silver Tables 1 through 10
- `silver_project` data and schema
- `docs/decisions.md`. D-04 remains open, and D-19 remains in force.
- Tables 13 through 15
- Gold models
- dashboard and Genie assets

## Verification boundary

Static repository checks are run locally. Unity Catalog tables and runtime match
coverage require Databricks execution, so no executed row counts or acceptance result
is claimed in this package.
