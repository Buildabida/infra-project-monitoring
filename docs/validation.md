# Bronze data-quality checks

This document covers the implemented Bronze validator only. Silver and Gold checks
remain planned and will receive separate documents when those layers are implemented.

`notebooks/04_validation/01_validation_bronze.py` validates all six authoritative Bronze tables.
Validation begins after every loader returns `SUCCESS` or `SKIPPED_IDEMPOTENT`.

- **stop** produces `FAIL` and blocks downstream use when Bronze is unsafe.
- **flag** produces `FLAG` for findings that require review or Silver handling.
  These include source issues, historical-reference differences, and provenance gaps.
- A check that cannot execute produces `ERROR` and blocks downstream use.

Validation reports problems.
It never fixes, filters, or deletes source rows.
Each Bronze table is aggregated once, including the 2 GB MGB extract.
The validation process does not cache source tables.

## Why STOP and FLAG are separate

A source can remain usable while containing a documented imperfection.
Treating every imperfection as a failure could encourage cleaning in Bronze.
Ignoring every imperfection could make an unsafe table appear acceptable.

STOP protects pipeline correctness.
FLAG keeps source limitations visible without changing raw rows.

## Validation flow

1. Resolve the latest audit state for every target from the small `load_log` table.
2. Confirm that each required table exists and contains one selected snapshot.
3. Build common metadata, row-count, source-key, and audit expressions.
4. Add source-specific checks supported by each documented source contract.
5. Evaluate each table's metrics in one grouped Spark aggregate.
6. Compare the table snapshot and row count with its latest safe audit event.
7. Append one result row per check to `04-validation.dq_results`.
8. Block downstream use when a STOP check fails or a check cannot be evaluated.

## Checks

Every table checks that:

- the table exists and contains rows
- required ingestion metadata is populated
- exactly one selected snapshot is present
- current row count and snapshot match the latest terminal `load_log` event
- documented keys follow the null and uniqueness rules supported by source grain
- historical row-count references remain flags instead of processing filters

Before overwriting a target, each loader requires every configured source-field group.
Each group accepts documented aliases without renaming the source column.

This protects the last valid table from a structurally incomplete CSV.
For example, the file may retain an identifier but lose a critical business field.
Critical fields include budget, place name, population, susceptibility, and geometry.

Source-specific checks include:

- DPWH status values, numeric and date casts, budget, progress, coordinates, and geographic bounds
- flood-control object identity, Contract ID nulls, repeated IDs, cost, and coordinates
- PSGC code identity and population integer casting when population is present
- Table C lineage, BARMM duplicate markers, population casting, and positive population
- boundary identifiers, administrative level, file and feature lineage, and geometry presence
- MGB susceptibility categories, geometry findings, and documented rating-count references

Results are appended to `04-validation.dq_results`.
Each result has `PASS`, `FLAG`, `FAIL`, or `ERROR` status.

Historical reference totals remain non-blocking checks:

- 45,611 Table C rows
- 43,760 boundary shapes
- 63,684 flood areas

These totals provide comparison evidence.
They are not filtering, deduplication, or transformation rules.

## Result fields

| Field | Meaning |
| --- | --- |
| `run_id` | Identifier shared by check rows from one validation attempt |
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

## Current interpretation note

The official MGB layer defines `VHF`, `HF`, `MF`, and `LF` as Very High, High,
Moderate, and Low susceptibility. Validation maps those codes only while evaluating
checks. Bronze continues preserving the original source values.

The October 4 evidence was produced by the earlier text-only comparison.
That historical evidence remains unchanged.

The updated validator ran on October 5, 2026. Run
`f530d193-5566-4bc4-abdb-3a88b65fa763` exported 126 checks.
The results were 105 `PASS` and 21 non-blocking `FLAG` rows.
No check produced `FAIL` or `ERROR`, and all 96 `stop` checks passed.

Only 16 of 63,684 MGB rows remained outside the accepted rating labels.
The earlier text-only comparison flagged 61,862 rows.
This decrease confirms that validation now recognizes the official codes.

Category-count differences and the blank-rating difference remain review flags.
Profile the 16 remaining values and confirm the blank count before closing the
broader category-distribution item. Do not change the raw Bronze values.

## Summary

Validation protects the Bronze preservation boundary.
It measures and reports findings, while Silver owns business changes.
Grouped expressions keep the checks efficient.
Audit and table reconciliation prevent a stale table from representing a failed batch.

## Future validation documents

Keep layer-specific checks separate as the pipeline grows:

```text
docs/validation/
├── README.md
├── bronze.md
├── silver.md
└── gold.md
```

Move this document to `docs/validation/bronze.md` only when the Silver or Gold
validation documents are added. Update existing links in the same pull request.
