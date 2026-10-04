# Data quality checks

`notebooks/04_validation/01_validation_bronze.py` validates all six authoritative
Bronze tables after the six loaders return `SUCCESS` or `SKIPPED_IDEMPOTENT`.

- **stop** produces `FAIL` and blocks downstream use when Bronze is unsafe.
- **flag** produces `FLAG` for a source issue, historical-reference mismatch, or
  provenance gap that Silver/review must handle.
- A check that cannot execute produces `ERROR` and blocks the run.

Validation reports problems; it never fixes or deletes rows. Each Bronze table is
aggregated once, including the 2 GB MGB extract, and is not cached.

## Why STOP and FLAG are separate

A source can be usable while still containing a documented imperfection. Treating every
imperfection as a failure would encourage cleaning in Bronze; ignoring every imperfection
would make unsafe tables look acceptable. STOP protects pipeline correctness. FLAG keeps
source limitations visible without changing raw rows.

## Validation flow

1. Resolve the latest audit state for every target from the small `load_log` table.
2. Confirm each required table and one selected snapshot exist.
3. Build common metadata, row-count, source-key, and audit expressions.
4. Add only source-specific checks supported by the documented source contract.
5. Evaluate each table's metrics in one grouped Spark aggregate.
6. Compare the table snapshot and row count with its latest safe audit event.
7. Append one result row per check to `04-validation.dq_results`.
8. Block downstream use when a STOP check fails or a check cannot be evaluated.

## Checks

Every table checks:

- table exists and has rows;
- all ingestion metadata is non-null;
- exactly one selected snapshot is present;
- the current row count and snapshot match the latest terminal `load_log` event;
- documented keys are non-null and unique only where source grain guarantees it;
- historical row-count references are flags, not filters.

Before a target overwrite, each loader requires every configured source-field group.
Each group accepts documented aliases without renaming the source column. This prevents
a readable CSV that has an identifier but has lost a business-critical field—such as
budget, place name, population, susceptibility, or geometry—from replacing the last
valid table.

Source-specific checks include:

- DPWH known status values, numeric/date casts, non-negative budget, progress range,
  coordinate completeness, and a Philippines bounding-box screen;
- flood-control source object identity, Contract ID nulls, and a flag that preserves
  repeated Contract IDs, plus cost and coordinate checks;
- PSGC code identity and population integer casting when present;
- Table C file/sheet/row lineage, known BARMM duplicate markers, population integer
  casting, and positive population checks;
- boundary identifier, administrative level, file/feature lineage, and geometry presence;
- MGB susceptibility categories, required non-empty geometry, and documented
  rating/count references.

The results append to `04-validation.dq_results` with `PASS`, `FLAG`, `FAIL`, or
`ERROR`. Known 45,611 Table C rows, 43,760 boundary shapes and 63,684 flood areas
remain non-blocking historical reference checks rather than processing rules.

## Result fields

| Field | Meaning |
| --- | --- |
| `run_id` | Identifier shared by the check rows in one validation attempt |
| `table_name` | Bronze table being evaluated |
| `column` | Column or table-level subject of the check |
| `data_quality_check` | Human-readable rule |
| `failed_rows` | Rows or units outside the rule |
| `total_rows` | Denominator or documented expected total |
| `percentage` | Relative size of the finding when meaningful |
| `status` | `PASS`, `FLAG`, `FAIL`, or `ERROR` |
| `action` | `stop` or `flag` |
| `details` | Concise context for reviewers |
| `snapshot_id` | Selected snapshot represented by the table |

## Summary

Validation preserves the Bronze boundary: it measures and reports, while Silver owns
business changes. Grouped expressions keep the checks efficient, and the audit/table
comparison prevents a stale table from representing a failed current batch.
