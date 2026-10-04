# Data quality checks

`notebooks/04_validation/01_validation_bronze.py` validates all six authoritative
Bronze tables after the six loaders return `SUCCESS` or `SKIPPED_IDEMPOTENT`.

- **stop** produces `FAIL` and blocks downstream use when Bronze is unsafe.
- **flag** produces `FLAG` for a source issue, historical-reference mismatch, or
  provenance gap that Silver/review must handle.
- A check that cannot execute produces `ERROR` and blocks the run.

Validation reports problems; it never fixes or deletes rows. Each Bronze table is
aggregated once, including the 2 GB MGB extract, and is not cached.

## Checks

Every table checks:

- table exists and has rows;
- all ingestion metadata is non-null;
- exactly one selected snapshot is present;
- the current row count and snapshot match the latest terminal `load_log` event;
- documented keys are non-null and unique only where source grain guarantees it;
- historical row-count references are flags, not filters.

Before a target overwrite, each loader also requires at least one documented
identifying/header alias for that source. This keeps a readable but structurally
wrong CSV from replacing the last valid table.

Source-specific checks include:

- DPWH known status values and `TRY_CAST` checks for available numeric/date fields;
- flood-control source object identity, Contract ID nulls, and a flag that preserves
  repeated Contract IDs;
- PSGC code identity and population integer casting when present;
- Table C file/sheet/row lineage when present, known BARMM duplicate markers, and
  population integer casting;
- boundary geometry presence and seven-file feature lineage when present;
- MGB susceptibility categories and the documented rating/count references.

The results append to `04-validation.dq_results` with `PASS`, `FLAG`, `FAIL`, or
`ERROR`. Known 45,611 Table C rows, 43,760 boundary shapes and 63,684 flood areas
remain reference checks until the current R2 files are executed and verified.
