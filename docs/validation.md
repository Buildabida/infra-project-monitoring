# Data-quality checks

This document covers the implemented Bronze, Silver configuration, and Silver geography
and population validators. Checks for the remaining Silver outputs and Gold remain planned.

## Bronze validation

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
| `total_rows` | Denominator used to calculate the finding percentage |
| `percentage` | Finding size as a percentage of `total_rows` |
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

The final validator rerun completed on October 6, 2026. Run
`f0c48af3-b629-482f-a192-99d9cd00ab15` exported 126 checks.
The results were 106 `PASS` and 20 non-blocking `FLAG` rows.
No check produced `FAIL` or `ERROR`, and all 96 `stop` checks passed.

The MGB check found no value outside the accepted severity codes or documented
missing representations. The executed cross-tabulation found 16 `No rating`
rows and 1,822 blank ratings in the selected 63,684-row snapshot.

Validation treats `No rating`, null, and blank values as missing or unrated.
This interpretation applies only while evaluating checks. It does not assign
a susceptibility severity and does not change the raw Bronze value.

Of the 1,822 blank ratings, 1,815 also have blank geometry. The other seven
blank ratings have geometry. All 16 `No rating` rows have geometry. This
reconciles the 1,815 geometry findings with the rating-distribution difference.

The historical missing-rating reference contains the 16 `No rating` rows and
seven blank rows with geometry. The selected R2 snapshot contains another
1,815 records with both fields blank. The difference remains a non-blocking
source-quality flag for Silver handling. Bronze rows remain unchanged.

## Summary

Validation protects the Bronze preservation boundary.
It measures and reports findings, while Silver owns business changes.
Grouped expressions keep the checks efficient.
Audit and table reconciliation prevent a stale table from representing a failed batch.

## Silver configuration validation

`notebooks/04_validation/02_validation_silver_config.ipynb` validates the five
configuration tables in `02-silver`.

The validator runs after `notebooks/02_silver/00_config_mappings.ipynb`.
It does not modify Bronze or mapping decisions.

Structural `stop` checks cover:

- required table presence
- natural-key uniqueness
- controlled approval states
- required mapping and source versions
- audit evidence for approved rows
- valid category source fields
- exclusion of the unsupported `Delayed` status
- controlled MGB levels and ranks
- valid PSGC targets for approved geographic rules

Coverage `flag` checks report unmapped or pending Bronze values.
They cover project categories, project statuses, and MGB susceptibility codes.

An empty manual geographic mapping table is valid.
The validator records a flag so reviewers can confirm that no exception was approved.

Results append to `04-validation.silver_config_dq_results`.
This table includes `layer`, `mapping_version`, and `run_id` fields.

The existing Bronze writer uses a fixed result structure.
A separate result table preserves backward compatibility during this milestone.

See [Silver configuration mappings](silver_config_mappings.md) for the approval workflow
and table contracts.

## Silver geography and population validation

`notebooks/04_validation/03_validation_silver_geography_population.ipynb` validates:

- `02-silver.silver_psgc_place`
- `02-silver.silver_population_place_reconciliation`
- `02-silver.silver_region_population`

Run it only after the three transformation notebooks finish in dependency order.
The validator does not change source rows or mapping decisions.

It applies the seven relevant quality attributes:

- Consistency: PSGC hierarchy, match contracts, region membership, and total reconciliation
- Accuracy: official PSGC geography, Table C authority, and approved alias targets
- Completeness: source-row accounting, match coverage, and official-region coverage
- Auditability: run IDs, snapshot IDs, ingest IDs, source-row identity, and rule versions
- Validity: population parsing, reference date, place types, statuses, and dispositions
- Uniqueness: each documented table grain
- Timeliness: compatible Table C, PSGC, alias, and transformation versions

Blocking checks fail when row accounting, keys, lineage, accepted population grain,
official region coverage, or population totals are unsafe. Findings such as ambiguous
matches, unmatched rows, non-positive population, and hierarchy exceptions remain flags.

The exact Table C accounting rule is:

```text
current Table C rows
= accepted primary
+ matched non-primary level
+ ambiguous
+ unmatched
+ invalid population
+ source exception
```

The region total must equal the sum of positive `ACCEPTED_PRIMARY` matched barangay rows.
It must not include province, city, municipality, or region subtotals.

Results are merged into `04-validation.silver_dq_results` before the stop gate runs.
The deterministic key prevents duplicate evidence on an exact rerun.
The existing Bronze and Silver configuration result tables remain unchanged.

See [Silver geography and population](silver_geography_population.md) for table contracts
and known limitations. Runtime validation outcomes require Databricks execution.

### Reconciliation lineage rule

Table C source lineage is required for every row in
`silver_population_place_reconciliation`.

PSGC target lineage is required only when `match_status` is
`MATCHED_EXACT_CONTEXT` or `MATCHED_ALIAS`.

Rows with `UNMATCHED`, `AMBIGUOUS`, or `INVALID_SOURCE` status may legitimately
have null `psgc_source_snapshot_id` and `psgc_source_ingest_run_id` because no
single PSGC target was accepted.

These unresolved rows remain visible for review and must not receive fabricated
PSGC lineage.

The lineage STOP check therefore validates:

- Table C source lineage for every reconciliation row
- PSGC target lineage only for successfully matched rows

## Future validation documents

Keep layer-specific checks separate as the pipeline grows:

```text
docs/validation/
├── README.md
├── bronze.md
├── silver.md
└── gold.md
```

Split this document only when the remaining Silver or Gold validators are implemented.
Update existing links in the same pull request.
