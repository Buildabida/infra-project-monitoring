# Review summary

## Existing Bronze design

The target branch implemented five source-specific loads. It downloaded API JSON and
GeoJSON or parsed manually uploaded XLSX files into a managed `landing` volume, hashed
every raw file, overwrote Bronze tables, and appended a legacy count/hash log. It also
created an authoritative-looking `population_2024` table from PSGC. Validation covered
the five-source design and orchestration treated every `SKIPPED` result as blocking.

## Important issues found

- Setup recreated the deleted `00-source.landing` volume and did not validate the R2 volume.
- Source paths and mechanics followed the old API/XLSX/GeoJSON architecture, not the six current R2 CSVs.
- There was no flood-susceptibility loader or validation.
- Reruns generated new raw folders and did not implement source-snapshot idempotency.
- The log had no snapshot, status, timing, failure or concise recovery fields.
- Full-file SHA-256 was mandatory, including for manually uploaded files.
- `population_2024` was still an authoritative required Bronze table.
- Documentation called earlier raw formats and current execution paths the same thing,
  which could misstate current CSV provenance.

## Revised architecture

The existing `cloudflare-r2` volume is source storage. Six thin notebooks call one
shared CSV loader. Bronze holds the selected/current snapshot; R2 keeps raw history.
All business fields remain strings and all source rows are preserved. Technical
metadata, snapshot checks, atomic Delta overwrite, status-event logging and explicit
failure re-raising are shared in `src/bronze.py`. Validation runs only after this
orchestration attempt returns `SUCCESS` or `SKIPPED_IDEMPOTENT` for all six sources.

## Files changed

- `README.md`: changed the high-level source and quickstart description from landing/five sources to R2/six sources.
- `src/config.py`: centralized the volume, six files/tables, source order, provenance,
  grain, aliases and documented reference values.
- `src/bronze.py`: replaced download/hash/Excel audit helpers with one snapshot-aware CSV loader and status log.
- `notebooks/00_setup/00_setup_workspace.sql`: removed landing creation and added read-only external-volume validation.
- `notebooks/00_setup/01_check_sources.py`: changed network checks to six cheap R2 metadata/header checks.
- `notebooks/01_bronze/01_bronze_dpwh_projects.py`: thin R2 loader; no Bronze cleaning.
- `notebooks/01_bronze/02_bronze_flood_control.py`: thin R2 loader that preserves repeated Contract IDs.
- `notebooks/01_bronze/03_bronze_psgc.py`: thin R2 loader; no generic population table.
- `notebooks/01_bronze/05_bronze_boundaries.py`: thin R2 loader; no spatial work.
- `notebooks/04_validation/01_validation_bronze.py`: six-table grouped STOP/FLAG validation and audit reconciliation.
- `notebooks/run_all.py`: six loaders, safe idempotent skips and validation gating.
- `notebooks/README.md`, `docs/data-model.md`, `docs/validation.md`,
  `docs/decisions.md`, `docs/README.md`: revised operational and design documentation.

## Files added

- `notebooks/01_bronze/04_bronze_census_table_c.py`
- `notebooks/01_bronze/06_bronze_flood_susceptibility.py`
- `docs/bronze_r2_architecture.md`
- `docs/bronze_cleanup_plan.md`
- `IMPLEMENTATION_NOTES.md`
- `tests/test_bronze.py`
- `CHANGE_MANIFEST.md`
- `REVIEW_SUMMARY.md`

## Files removed or renamed

- `notebooks/01_bronze/06_bronze_census_table_c.py` was replaced by
  `04_bronze_census_table_c.py` so all six source notebooks have an understandable run order.

No source data, table, schema or volume was deleted.

## Source-specific decisions

- DPWH projects: preserve project fields; validate known key/status/type aliases when present.
- Flood control: preserve every row; repeated Contract IDs are a FLAG, never a deduplication rule.
- PSGC: keep geographic reference values; do not create `population_2024`.
- Table C: authoritative population; keep BARMM copies; flag absent workbook/sheet/row provenance.
- Boundaries: preserve geometry; flag absent seven-file feature lineage; do not spatially map projects.
- MGB: ingest the approved trimmed extract; do not claim it is the complete service response or assign places.

## Low-compute decisions

- `inferSchema=false`; business columns remain strings.
- No pandas, `toPandas`, large-source driver collection, `coalesce(1)`, repartition,
  spatial join, analytical aggregation or full-file checksum.
- Snapshot identity hashes only a short metadata string.
- Normal ingestion scans the source once; one post-write Delta count verifies the commit.
- Validation aggregates each table once and never caches the 2 GB source.
- Sorting/driver retrieval is limited to one small `load_log` row.

## Idempotency and snapshot design

The caller may provide `snapshot_id` and `source_version`. Otherwise the ID is derived
from source name/version, path, size and nanosecond modification time. Exact completed
metadata returns `SKIPPED_IDEMPOTENT`. The same ID with changed metadata fails. A
different ID replaces the current table atomically. `force_reload=true` rebuilds only
an identical selected snapshot; it does not permit reusing an ID for changed bytes.

## Resilience design

Before a write, the loader verifies the file, size, nonempty body, readable/unique
header, reserved-column safety and snapshot consistency. It uses CSV `FAILFAST` and a
Delta atomic overwrite. It compares an observed source-row count with the committed
Bronze count, records `SUCCESS`, and records/re-raises `FAILED` when possible. The
previous Delta version remains visible if Spark fails before commit.

## Validation checks

All six tables check existence, nonempty data, one snapshot, non-null ingestion
metadata, documented source keys, latest load status, row-count reconciliation and
snapshot reconciliation. Available business fields receive `TRY_CAST` checks. DPWH
status values, repeated flood-control Contract IDs, Table C BARMM/provenance behavior,
boundary geometry/provenance and MGB rating/reference counts have source-specific
checks. Historical row totals are FLAG checks, not transformations.

## Static checks actually run

- Python syntax compile for every `.py`: **PASS**.
- `git diff --check`: **PASS**.
- Pure helper smoke checks for metadata inspection, deterministic/version-sensitive
  snapshot IDs, header mapping, booleans, six-source config and empty-source rejection: **PASS**.
- Targeted searches: **PASS** for no executable landing dependency, no authoritative
  `population_2024` table, six run-all loaders, MGB validation, centralized volume path,
  no pandas/large collect/single-file coalesce/repartition/full-file hash, and no
  automatic DROP/DELETE/TRUNCATE.
- `pytest`: **NOT RUN** because pytest is not installed locally (`No module named pytest`).
- Ruff: **NOT RUN** because the `ruff` executable is not installed.
- SQLFluff: **NOT RUN** because the `sqlfluff` executable is not installed.

No packages were installed and no Databricks execution was claimed.

## Databricks run order

1. `notebooks/00_setup/00_setup_workspace.sql`
2. `notebooks/00_setup/01_check_sources.py` for a preflight view
3. `notebooks/01_bronze/01_bronze_dpwh_projects.py`
4. `notebooks/01_bronze/02_bronze_flood_control.py`
5. `notebooks/01_bronze/03_bronze_psgc.py`
6. `notebooks/01_bronze/04_bronze_census_table_c.py`
7. `notebooks/01_bronze/05_bronze_boundaries.py`
8. `notebooks/01_bronze/06_bronze_flood_susceptibility.py`
9. `notebooks/04_validation/01_validation_bronze.py`

Steps 1 and 3–9 are orchestrated by `notebooks/run_all.py`; step 2 is an optional
read-only preflight.

## Still requires Databricks

- Confirm actual CSV headers, encodings/delimiters, file metadata and row counts.
- Confirm the configured volume-root paths; use the `source_path` widget only if the
  workspace stores a controlled snapshot in a subdirectory.
- Exercise legacy-to-new `load_log` and `dq_results` schema evolution.
- Confirm serverless support for the PySpark `Observation` used during writes.
- Review all FLAG results, especially historical Table C/boundary/MGB counts and
  missing source-provenance fields.
- Test one exact rerun, one forced identical rerun and one deliberate snapshot conflict.

## Rollback strategy

This local refactor has not changed Databricks. If a Databricks trial is rejected,
stop before cleanup, restore the prior code revision, and use Delta history to identify
the previous table version. After verifying the target version, a workspace owner may
manually use Delta `RESTORE TABLE ... TO VERSION AS OF ...` for an affected Bronze
table. Do not drop R2 files or audit tables. The optional cleanup plan remains unexecuted.

## Proposed PR

**Title:** `[BRONZE] Refactor six-source ingestion for Cloudflare R2 snapshots`

**Description:**

> Refactors Source and Bronze ingestion to read the six approved CSV snapshots from
> the existing Cloudflare R2 volume. Adds metadata-based snapshot idempotency, atomic
> current-snapshot writes, explicit load statuses, MGB flood-susceptibility ingestion,
> grouped six-table validation, provenance documentation and a manual-only cleanup
> plan. Removes executable dependencies on the deleted landing volume and removes
> `population_2024` from the authoritative Bronze interface. Local syntax, diff and
> helper smoke checks pass; Databricks execution and current-file row counts remain
> required before merge. No tables or raw files are deleted automatically.
