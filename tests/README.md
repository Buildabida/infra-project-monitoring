# Tests

Small automated tests protect reusable behavior in `src`. Test files use the
`test_<what>.py` naming pattern. This helps CI and reviewers map each test to its
shared module.

## `test_bronze.py`

These tests protect the low-cost Bronze contract without requiring Spark:

- deterministic metadata-based snapshot IDs
- duplicate and Delta-incompatible header handling
- explicit widget boolean parsing
- required source-field alias groups
- separate MGB rating and geometry requirements
- exact current-table artifact matching
- rejection of historical snapshots as the current selected snapshot
- strict quoted-record parsing and wrong-width rejection
- canonical snapshot identity after a rejected conflict

## `test_xlsx.py`

`src/xlsx.py` preserves the earlier workbook-migration logic for reproducibility.
It is not part of the current R2 CSV loaders. Its tests cover exact text preservation,
empty cells, numbers, saved formula results, and complete row classification.

## Boundary between tests and data quality

Unit tests verify deterministic helper behavior. Layer validators evaluate Delta
tables and record results in `04-validation.dq_results`.

Bronze, Silver, and Gold each own checks that match their responsibilities. Bronze
checks source preservation and ingestion safety. Silver checks cleaning and matching.
Gold checks analytical grain, measures, keys, and reporting readiness.

Keeping these responsibilities separate makes local tests fast. It also preserves
source-aware and layer-aware checks in the data platform.
