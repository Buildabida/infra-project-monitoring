# Silver geography and population

This milestone implements three Silver tables for official geography and authoritative
population. It does not implement project matching, flood mapping, Gold tables, or
population-based investment measures.

## Source authority

PSGC supplies official codes, names, geographic levels, hierarchy, region membership,
and publisher version when available.

PSA Census Table C supplies authoritative population. PSGC population is diagnostic
only. The pipeline never overwrites Table C population, averages the two sources, or
uses PSGC population because it is easier to join.

The production path remains R2 to Bronze to Silver. Local CSVs supported schema review,
but the notebooks do not depend on a developer file path.

## Implementation status

| Item | Status |
| --- | --- |
| Five Silver configuration tables | Implemented |
| `silver_psgc_place` | Implemented. Databricks execution is required. |
| `silver_population_place_reconciliation` | Implemented. Databricks execution is required. |
| `silver_region_population` | Implemented. Databricks execution is required. |
| Silver geography and population validation | Implemented. Databricks execution is required. |
| Project and flood Silver outputs | Implemented in later milestones. Databricks execution is required. |
| Gold facts and dimensions | Planned |

## Dependency order

Run the notebooks in this order:

1. `02_silver/00_config_mappings.ipynb`
2. `04_validation/02_validation_silver_config.ipynb`
3. `02_silver/01_silver_psgc_place.ipynb`
4. `02_silver/02_silver_population_place_reconciliation.ipynb`
5. `02_silver/03_silver_region_population.ipynb`
6. `04_validation/03_validation_silver_geography_population.ipynb`

Do not run a dependent notebook after a blocking failure.

## Bronze safety gate

Before Silver reads a selected source, it checks the newest terminal `load_log` event.
The status must be `SUCCESS` or `SKIPPED_IDEMPOTENT`. Snapshot identity must be present,
and loaded rows must be positive.

The latest Bronze validation for the selected snapshot must contain no `FAIL` or `ERROR`
with action `stop`. An older successful load cannot hide a newer failed or incomplete load.
The gate reads compact audit evidence and does not rescan R2.

## `silver_psgc_place`

Purpose: provide one reusable official PSGC place hierarchy.

Grain: one official PSGC place per selected PSGC version or source snapshot.

Natural key:

- `psgc_code`
- `psgc_version` when published, otherwise `source_snapshot_id`

The table retains raw and conservatively standardized place names. Standardization trims,
uses consistent case, and collapses repeated whitespace. It does not remove geographic
words or use fuzzy matching.

Region, province, and city or municipality values come from rows that exist in the same
selected PSGC snapshot. Code prefixes locate candidate ancestors, but missing verified
ancestors remain null. Blank or unknown geographic levels remain visible with an exception
status.

Repeated names are expected. Names such as `Poblacion` are never treated as globally
unique. Code, place type, and hierarchy provide identity.

## `silver_population_place_reconciliation`

Purpose: explain the outcome for every current Table C source row.

Grain: one Table C source-row reconciliation result per deterministic Silver run.

Natural key:

- `source_file`
- `sheet_name`
- `source_row_number`
- `run_id`

The current Bronze contract contains 43,750 Table C rows. Historical documentation also
records 45,611 source rows, 1,861 copied BARMM rows, and 43,750 analysis rows. Those older
counts are reference evidence, not a new filtering rule. Silver does not remove another
1,861 rows.

### Matching waterfall

1. Resolve the sheet to one verified PSGC province or independent city.
2. Resolve uppercase locality headings within that verified sheet context.
3. Match ordinary rows to barangays under the verified current locality.
4. If unresolved, use one active `APPROVED` alias from the selected alias version.
5. Keep multiple candidates as `AMBIGUOUS`.
6. Keep zero candidates as `UNMATCHED`.

An approved alias must include geographic context. Blank context fields do not authorize a
global name-only match. The configuration table may remain empty. The pipeline still runs,
and unresolved rows remain visible.

Fuzzy similarity cannot assign an accepted PSGC code. It may support a later review queue,
but it is outside this milestone.

### Population handling

`population_raw` is preserved. `population_count` uses a safe numeric conversion. A parse
failure remains invalid and never becomes zero.

Non-positive values keep their original value and receive `INVALID_POPULATION`. Current
Bronze evidence reports 12 such rows. This count is a review reference, not transformation
logic.

Each source row receives one final disposition:

- `ACCEPTED_PRIMARY`
- `MATCHED_NON_PRIMARY_LEVEL`
- `AMBIGUOUS`
- `UNMATCHED`
- `INVALID_POPULATION`
- `SOURCE_EXCEPTION`

Disposition counts must equal current Table C rows exactly.

For matched rows at an equivalent level, PSGC population is carried as a cross-check.
Differences and percentages remain diagnostic. A difference does not replace Table C or
block the pipeline by itself.

## `silver_region_population`

Purpose: create the authoritative region-level input for the future Gold population fact.

Grain: one official PSGC region per reference year, source, and selected source snapshots.

Natural key:

- `psgc_region_code`
- `reference_year`
- `source_name`
- `source_snapshot_id`
- `psgc_source_snapshot_id`

The population reference date is July 1, 2024. It is centralized in the population
reconciliation setup and never derived from the current date.

Only positive `ACCEPTED_PRIMARY` barangay rows contribute. Province, city, municipality,
and region subtotals do not join the aggregate. This avoids double or triple counting.
Region membership comes from the matched PSGC hierarchy, not a second text match.

The selected PSGC snapshot determines the official region set. No region count is hardcoded.
A missing official-region population remains null, which is different from a population of
zero. NCR remains its own region. BARMM population remains present when Table C supports it.

Unresolved Table C rows do not enter a fake region `0`. Gold reserves key `0` for unknown,
unmapped, or non-geographic dimension members later.

## Lineage and versions

The tables distinguish these concepts:

- `run_id`: deterministic Silver processing identity
- `source_ingest_run_id`: upstream Table C or PSGC Bronze ingestion identity
- `source_snapshot_id`: selected Table C or PSGC source snapshot
- `psgc_version`: publisher PSGC version when available
- `alias_version`: selected place-alias rules, or `NO_APPROVED_ALIAS`
- `transformation_rule_version`: version of the Silver transformation contract

The reconciliation table retains Table C source lineage for every source row.

Successfully matched rows also retain the matched PSGC snapshot and ingest run.
PSGC target lineage is required only when `match_status` is
`MATCHED_EXACT_CONTEXT` or `MATCHED_ALIAS`.

Rows with `UNMATCHED`, `AMBIGUOUS`, or `INVALID_SOURCE` status may legitimately
have null matched-target PSGC lineage because no single PSGC target was accepted.
These rows remain traceable through their Table C source lineage and Silver run
identity.

The regional table retains the lineage of the accepted matched inputs plus the
reconciliation run identity.

## Idempotency and cost

Stable identities use source lineage and deterministic hashes. They do not use random row
keys. Exact reruns replace current-snapshot Silver tables atomically and do not append
duplicate logical rows.

The three source tables are small enough for straightforward SQL. They are not partitioned,
cached, optimized, streamed, collected into Python, or processed with Python UDFs. This
milestone does not read MGB, boundaries, DPWH projects, or flood-control projects.

## Validation

`03_validation_silver_geography_population.ipynb` writes results to
`04-validation.silver_dq_results`. It leaves the existing Bronze and CONFIG result tables
unchanged.

Stop checks protect:

- Bronze and Silver row reconciliation
- documented natural keys
- snapshot and run lineage
- controlled match statuses and row dispositions
- valid approved alias targets
- positive matched barangay inclusion
- official PSGC region coverage
- population input and regional total reconciliation

Flag checks report:

- unassigned PSGC levels or hierarchy exceptions
- repeated standardized place names
- exact and alias coverage
- ambiguous and unmatched Table C rows
- invalid or non-positive population
- missing official-region population

Every coverage check retains a numerator, denominator, and percentage when meaningful.
Results are stored before the validator enforces the stop gate.

## Known limitations

- Table C provides no reliable PSGC code, so matching depends on verified sheet and section
  context.
- Empty alias configuration is valid and may leave unresolved rows.
- Historical evidence says 43,748 of 43,750 rows matched PSGC population during an earlier
  review. The current snapshots determine the actual result.
- The historical national population reference of 112,727,776 applies only when the selected
  source is confirmed compatible. It is not transformation logic.
- Databricks must execute the notebooks before match coverage and validation outcomes can be
  claimed.

## Gold handoff

`silver_psgc_place` later supports `03-gold.dim_region`.
`silver_region_population` later supports `03-gold.fact_region_population`.

Gold will add surrogate keys and serving contracts. This milestone does not calculate budget
share, population share, budget per resident, or a budget-to-population ratio. Future results
must describe allocation differences and regional patterns, not fairness or sufficiency.
