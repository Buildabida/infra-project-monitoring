# Tests

Small automated tests protect reusable behavior in `src`. Test files follow
`test_<what>.py` naming so CI and reviewers can map them to the shared module.

## `test_bronze.py`

These tests protect the low-cost Bronze contract without requiring Spark:

- deterministic metadata-based snapshot IDs;
- duplicate and Delta-incompatible header handling;
- explicit widget boolean parsing;
- required source-header aliases;
- exact current-table artifact matching; and
- the rule that a historical snapshot is not the current selected snapshot.

## `test_xlsx.py`

`src/xlsx.py` is retained for reproducibility of the earlier workbook-migration logic,
not for the current R2 CSV loaders. Its tests check exact text preservation, empty cells,
numbers, saved formula results, and complete row classification.

## Boundary between tests and data quality

Unit tests verify deterministic helper behavior. Bronze validation evaluates selected
Delta snapshots and records its results in `04-validation.dq_results`. Keeping these
responsibilities separate makes local tests fast while preserving source-aware checks in
the data platform.
