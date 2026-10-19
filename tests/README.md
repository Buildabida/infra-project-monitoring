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
- one record per text line, a first line that is the header, and one header line (#106)
- file, parser, and table row counts that must agree, with restore or drop on a mismatch (#107)
- canonical snapshot identity after a rejected conflict, and no claim from a failed attempt (#107)
- acceptance-evidence check names that match the Bronze validator (#108)

## `test_xlsx.py`

`src/xlsx.py` preserves the earlier workbook-migration logic for reproducibility.
It is not part of the current R2 CSV loaders. Its tests cover exact text preservation,
empty cells, numbers, saved formula results, and complete row classification.

## Gold notebook tests

`test_gold_dimensions.py` and `test_gold_facts.py` read the Gold notebooks as text.
They never run SQL or touch Databricks. Each test strips SQL comments and squeezes
whitespace, then looks for whole statements, not single words. So a test fails when
a notebook drops one of these:

- any part of a key recipe, such as `COALESCE(psgc_version, source_snapshot_id)` in `region_key` (D-33)
- a key column in the STOP check that runs before each fact's `MERGE`
- a NULL-safe `<=>` in the region joins and the Silver total checks

These tests cannot prove that the SQL runs or that the data is right. The Gold
validator checks the tables after a run.

## `test_quality_gate.py`

Runs the real end-to-end gate notebook on local Spark with Delta, against small
synthetic tables, through `spark_harness.py`. The harness only renames the hyphenated
schemas, which open-source Spark rejects, and skips `USE CATALOG`. It covers every
validator passing, a failed STOP check, an `ERROR`, FLAG findings, missing evidence,
a missing table, evidence from another snapshot or an older fact run, stale evidence,
evaluating twice, recovery, and the count and budget reconciliation.

These tests need `pyspark` and `delta-spark`. Without them the scenario tests skip,
and the contract tests still run. CI runs them in the `Quality gate (Spark)` job:

```bash
python -m pip install -r tests/requirements-spark.txt
python -m pytest -q tests/test_quality_gate.py
```

## `test_pipeline_job_and_dashboard.py` and `test_repository_structure.py`

These check the job graph, the bundle targets, the failure email, the dashboard
dependencies, required files, notebook headers, CODEOWNERS paths, and that no
token or private key is committed.

## Boundary between tests and data quality

Unit tests verify deterministic helper behavior. Layer validators evaluate Delta
tables and record results in the `04-validation` results tables.

Bronze, Silver, and Gold each own checks that match their responsibilities. Bronze
checks source preservation and ingestion safety. Silver checks cleaning and matching.
Gold checks analytical grain, measures, keys, and reporting readiness.

Keeping these responsibilities separate makes local tests fast. It also preserves
source-aware and layer-aware checks in the data platform.
