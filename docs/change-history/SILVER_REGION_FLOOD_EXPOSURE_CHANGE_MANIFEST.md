# Silver regional flood exposure change manifest

## Added

| File | Purpose |
| --- | --- |
| `notebooks/02_silver/09_silver_region_flood_exposure.ipynb` | Clip approved MGB polygons to safe official region boundaries once, dissolve overlap, and publish equal-area regional exposure |
| `notebooks/04_validation/07_validation_silver_region_flood_exposure.ipynb` | Recompute evidence independently and persist all seven DQ attributes before enforcing the Table 14 gate |
| `tests/test_silver_region_flood_exposure.py` | Protect dependencies, mapping governance, grid, identity, CRS, spatial cost, zero versus no data, overlap, lineage, validation, and scope |
| `docs/silver_region_flood_exposure.md` | Document purpose, sources, grain, CRS, boundary strategy, overlap rules, accounting, lineage, validation, limits, and Gold handoff |
| `SILVER_REGION_FLOOD_EXPOSURE_REVIEW_SUMMARY.md` | Record baseline, verified contracts, design review, runtime boundary, and handoff |
| `SILVER_REGION_FLOOD_EXPOSURE_CHANGE_MANIFEST.md` | List files and milestone scope |

## Updated

| File | Change |
| --- | --- |
| `README.md` | Mark regional flood exposure implemented and link its contract |
| `docs/README.md` | Add regional flood-exposure navigation |
| `docs/data-model.md` | Mark Table 14 implemented, document its grain, key, and columns, and name it as the Gold fact source |
| `docs/validation.md` | Add Table 14 DQ attributes, STOP and FLAG behavior, persistence, and run order |
| `docs/silver_config_mappings.md` | Replace the outdated planned status for implemented project and flood Silver outputs |
| `notebooks/README.md` | Add Table 14 and its validator to the sequence and document dependency-aware execution |

## Unchanged by design

- Bronze ingestion logic and Bronze business values
- Silver Tables 1 through 13
- `docs/decisions.md`, because no team decision was recorded in this milestone
- `tests/README.md`, because it lists only `src` helper tests
- project-flood mapping (Table 15)
- Gold facts and dimensions
- dashboard and Genie assets

## Verification

Local verification covered notebook JSON, SQL parsing, Python tests, and
documentation checks. The review summary lists each command and result.

Databricks execution was not available in this environment. No runtime
exposure, coverage, or validation total is claimed.
