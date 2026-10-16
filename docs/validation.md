# Data-quality checks

This document covers the implemented Bronze, Silver configuration, and Silver geography
and population validators. It also covers the Silver project, source-reconciliation,
project-region, regional flood-exposure, and project-flood mapping validators, the
Gold validator, and the analytics validator.

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

`notebooks/04_validation/02_validation_silver_config.ipynb` validates the six
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
- exactly one active approved DPWH taxonomy version
- no duplicate active approved DPWH category rule at the complete mapping grain
- complete approved DPWH sectors and flood markers
- exclusion of the unsupported `Delayed` status
- controlled MGB levels and ranks
- valid PSGC targets for approved geographic rules
- a PSGC version on each approved DPWH region alias that equals the Bronze
  `psgc.source_release` of its target code (#114)
- exact source-file and sheet scope, controlled `BARANGAY` role, and no active
  approved fan-out for Table C row-role exceptions (#113)

Coverage `flag` checks report unmapped or pending Bronze values.
They cover atomic DPWH `componentCategories`, project statuses, and MGB
susceptibility codes.

Empty manual geographic mapping and Table C row-role exception tables are valid.
The validator records a flag so reviewers can confirm that no exception was approved.

Results merge into `04-validation.silver_config_dq_results` with a deterministic
run ID derived from the selected source snapshots, config versions, and result
set. An exact rerun updates the same logical evidence rows.
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

Validation version `silver-geography-population-validation-v4` adds these checks:

- `One reconciliation run ID reproduces from its lineage` is a STOP (#112). Every row
  must carry the run ID that the Table C snapshot, the selected PSGC snapshot, the alias
  version, and the rule version reproduce.
- `Each PSGC barangay is accepted at most once` is now a STOP, not a FLAG (#114). A
  barangay accepted twice counts its population twice in the region total.
- `Every active approved alias produced an accepted match` is a FLAG (#114). It counts
  aliases that resolved no sheet and matched no row. The validator cannot see the
  notebook's candidate views, so an alias whose only candidate stayed `AMBIGUOUS` also
  counts as unused.
- `Rows under an unresolved heading-like row remain visible` is a FLAG (#113). It counts
  rows that failed closed because they follow an unresolved heading-like row.
- `Unresolved heading-like rows cannot produce a trusted match or locality` is a STOP
  (#113). It prevents an unresolved uppercase heading from entering a barangay match.
- `Rows after unresolved headings cannot inherit a trusted locality` is a STOP (#113).
  It protects later rows until a new resolved heading establishes context.
- `Unresolved heading-like rows remain visible` and `Every active approved row-role
  exception was used` are FLAG checks (#113). The latter keeps reviewed exceptions
  observable rather than silently accumulating.

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
`MATCHED_EXACT_CONTEXT`, `MATCHED_ALIAS`, or `MATCHED_NORMALIZED_CONTEXT`.

Rows with `UNMATCHED`, `AMBIGUOUS`, or `INVALID_SOURCE` status may legitimately
have null `psgc_source_snapshot_id` and `psgc_source_ingest_run_id` because no
single PSGC target was accepted.

`run_id` does not read the row's own PSGC lineage. It hashes the selected PSGC
snapshot, so these rows share the run ID of the matched rows (#112).

These unresolved rows remain visible for review and must not receive fabricated
PSGC lineage.

The lineage STOP check therefore validates:

- Table C source lineage for every reconciliation row
- PSGC target lineage only for successfully matched rows

## Silver project validation

`notebooks/04_validation/04_validation_silver_projects.ipynb` validates:

- `02-silver.silver_dpwh_project_component`
- `02-silver.silver_project`

Run the validator only after both project transformation notebooks finish successfully:

1. `notebooks/02_silver/04_silver_dpwh_project_component.ipynb`
2. `notebooks/02_silver/05_silver_project.ipynb`
3. `notebooks/04_validation/04_validation_silver_projects.ipynb`

The validator reports findings without modifying Bronze rows, Silver project rows, or governed mapping decisions.

### Data-quality attributes

The project validator applies the relevant FTW data-quality attributes:

- Consistency: project attributes and sorted category sets follow deterministic resolution rules, and budget-resolution states agree with the underlying distinct-value counts.
- Accuracy: parsed and canonical values remain source-supported, while unresolved values are not presented as accepted results.
- Completeness: Bronze rows, component rows, project rows, missing values, invalid parses, and unresolved attributes remain visible.
- Auditability: component and project outputs retain source-snapshot and Bronze-ingest lineage.
- Validity: reported budgets, physical progress, dates, coordinates, controlled statuses, and resolution states are checked.
- Uniqueness: component and project records are validated at their documented grains.
- Timeliness: outputs remain tied to the selected Bronze snapshot and transformation-rule version.

### Blocking checks

Blocking `stop` checks protect:

- a non-empty component table
- exact Bronze-to-component row reconciliation
- exact component-to-project accounting
- unique component keys, Contract IDs, and project keys
- present Contract IDs
- quality and mapping states that use the controlled values
- quality statuses that agree with their parsed values
- budget double-count protection
- component and project category arrays that agree with their classification state
- one project taxonomy version
- project reported budgets that reconcile to the component resolution rule
- zero-progress flags that agree with resolved progress
- implementing office and contractor values that follow the missing, resolved, or conflict rule
- coordinates that publish as one complete pair, equal to a pair recounted from the components
- a standardized status, status group, and mapping version only for a resolved and mapped raw status
- a mapping version on every mapped row
- populated, reproducible keys, run IDs, and lineage
- one component snapshot that equals the latest Bronze DPWH load
- projects built from the current component run

A blocking failure means the project foundation is unsafe for downstream use.

### Review flags

Non-blocking `flag` checks report, each with its denominator:

- missing or unparseable `componentCategories`
- unapproved category tokens and statuses with no approved rule
- missing, partial, or unparseable coordinate pairs
- projects whose components report more than one valid coordinate pair
- repeated identical source rows, kept and counted
- unparseable budgets
- negative budgets
- unparseable progress
- progress outside 0 to 100
- unparseable infrastructure years
- unparseable start or completion dates
- projects with at least one conflicting attribute

These findings remain visible for review. The validator does not automatically correct, replace, or delete the affected source evidence.

Every check uses one status rule: no failed rows is `PASS`, a failed `stop`
check is `FAIL`, and a failed `flag` check is `FLAG`. The validator reports
mapped and unmapped project and budget coverage, single-sector and multi-sector
counts, missing categories, and DPWH flood-related projects. A second grouped
component scan independently reconstructs the no-double-count project-budget
control total. The same scan recounts each project's coordinate pair from the
rows that hold both values, and the project scan compares it with the published
pair.

### Row reconciliation

The component-table accounting rule is:

```text
Bronze DPWH rows
=
Silver DPWH component rows
```

The expected difference is zero.

The project-table accounting rule is:

```text
Silver DPWH component rows
=
SUM(silver_project.component_count)
```

The expected difference is zero.

The project table must also contain no duplicate project identity at its documented Contract ID grain.

### Budget protection

The validator confirms that project budgets are not created by blindly summing repeated component values.

The supported outcomes are:

- one valid source-supported budget
- one repeated identical budget retained once
- missing or invalid budget
- multiple conflicting budgets retained as unresolved

Projects with multiple distinct component budget values must not publish an unsupported canonical project total.

The published resolved project-budget total must equal the control total built
independently from component evidence. Mapped and unmapped resolved budgets must
also sum to that same total.

### Validation evidence

Project validation executes after both project Silver tables are published.

The validator persists project validation results to
`04-validation.silver_dq_results` before enforcing the blocking gate.

This preserves validation evidence even when a blocking check fails and keeps
the project validator consistent with the geography/population and source-reconciliation
validation contracts.

The validation run identity uses the Silver project run, the component run, and
the validation-rule version `silver_project_validation_v6`. Exact reruns update the same logical evidence
instead of creating duplicate validation records.

Source-quality findings remain visible as review evidence rather than being silently cleaned.

The v4 Databricks run wrote 39 checks. All 24 STOP checks passed. Its results
are in [runtime evidence](silver_project_cleaning.md#runtime-evidence).

## Silver source-reconciliation validation

`notebooks/04_validation/05_validation_silver_source_reconciliation.ipynb`
validates:

- `02-silver.silver_flood_control_component`
- `02-silver.silver_project_source_match`

Run it only after the project foundation validator passes and both source-
reconciliation transformations finish:

1. `notebooks/02_silver/06_silver_flood_control_component.ipynb`
2. `notebooks/02_silver/07_silver_project_source_match.ipynb`
3. `notebooks/04_validation/05_validation_silver_source_reconciliation.ipynb`

The validator persists results to `04-validation.silver_dq_results` before its
blocking gate. Runtime outcomes require Databricks execution.

### Source-reconciliation quality attributes

- Consistency: component accounting and source-cost states follow documented rules.
- Accuracy: matched Contract IDs agree after `TRIM` and `UPPER` only.
- Completeness: invalid IDs, repeats, unmatched groups, and ambiguous targets remain visible.
- Auditability: source component, source snapshot, target project, and match-run lineage remain available.
- Validity: source feature IDs, costs, statuses, and assignments follow their contracts.
- Uniqueness: component and match keys are unique at their documented grains.
- Timeliness: each output contains one selected snapshot and deterministic Silver run.

### Source-reconciliation stop checks

Blocking checks protect:

- accepted and nonempty upstream tables
- exact Bronze-to-component row preservation
- unique component and match keys
- one selected snapshot and run
- complete component-to-match accounting, including invalid Contract IDs
- one result per usable normalized source Contract ID
- exact-match assignment correctness
- unresolved conflicting costs
- mandatory source and target lineage
- a `target_project_run_id` equal to the current `silver_project` run (#114)

### Source-reconciliation review flags

Nonblocking findings report:

- invalid source Contract IDs
- repeated source Contract IDs
- unparseable or negative Contract Cost
- coordinate exceptions
- unmatched Contract IDs
- ambiguous target candidates
- multiple distinct Contract Cost values

The validator does not modify source evidence, assign arbitrary targets, add flood
Contract Cost to DPWH budget, or resolve D-04.

### Source-reconciliation accounting

The component rule is:

```text
selected Bronze flood-control rows
= Silver flood-control component rows
```

The match rule is:

```text
Silver flood-control component rows
= source components represented by match rows
+ component rows with invalid source Contract IDs
```

Both expected differences are zero.

See [Silver source reconciliation](silver_source_reconciliation.md) for the complete
table, matching, lineage, and cost contracts.

## Silver project-region mapping validation

`notebooks/04_validation/06_validation_silver_project_region_map.ipynb`
validates `02-silver.silver_project_region_map` after Table 13 is rebuilt.

Use this order for the final two steps:

1. `notebooks/02_silver/08_silver_project_region_map.ipynb`
2. `notebooks/04_validation/06_validation_silver_project_region_map.ipynb`

The validator persists results to `04-validation.silver_dq_results` before
enforcing its blocking gate. Its validation run ID is deterministic for the
mapping run and validation-rule version.

### Project-region data-quality attributes

- Consistency: status accounting, mapping precedence, conflict states, and
  boundary-version differences follow their contracts.
- Accuracy: accepted codes resolve to the selected official PSGC region set.
  name-versus-coordinate disagreements stay visible.
- Completeness: every canonical project has one result, and coverage uses the
  complete project denominator.
- Auditability: project, PSGC, boundary, configuration, rule, run, and load
  lineage remain available.
- Validity: methods, statuses, quality values, Central Office behavior, and
  selected region geometry use controlled rules.
- Uniqueness: the documented mapping grain and deterministic primary key are
  unique.
- Timeliness: exactly one deterministic mapping run represents the selected
  upstream versions.

### Project-region stop checks

Blocking checks protect:

- exact `silver_project` to map-row preservation
- unique `source_system`, usable `contract_id`, and `run_id` grain
- unique and reproducible mapping keys
- reproducible mapping run identity
- controlled methods, statuses, and quality
- documented mapping precedence
- official PSGC target validity
- matched and unresolved target consistency
- Central Office non-geographic behavior
- name-versus-coordinate conflict state
- parseable selected region geometry
- selected region boundary-code uniqueness
- applied manual-override decision evidence
- mandatory source and transformation lineage
- coordinate statuses limited to `VALID_PAIR`, `MISSING_PAIR`, `PARTIAL_PAIR`,
  and `OUT_OF_RANGE` (#114)
- a `project_run_id` and `psgc_run_id` equal to the current `silver_project` and
  PSGC region runs (#114)

### Project-region review flags

Nonblocking checks retain:

- geographic match coverage with the full project denominator
- missing reported regions
- exact-name, approved-alias, and unresolved text coverage
- missing, partial, or out-of-range coordinates. Before #114 this flag looked
  for `OUTSIDE_SCREENING_RANGE`, which Table 13 never emits.
- usable-point, one-region, no-boundary, and multiple-region spatial coverage
- empty approved alias or manual-exception configurations
- boundary coverage and PSGC-version mismatch
- unresolved boundary PSGC codes
- boundary source-lineage duplicates
- matched name-versus-coordinate conflicts
- Central Office records with ignored manual-override evidence
- ambiguous and unmatched projects
- optional DPWH and boundary publisher-version gaps

The validator does not create aliases, select among ambiguous candidates, assign
Central Office to a normal region, or convert source limitations into accepted
data.

See [Silver project-to-region mapping](silver_project_region_mapping.md) for the
complete Table 13 grain, precedence, lineage, cost, and Gold handoff contracts.
The first documented Databricks run passed all 18 STOP checks. Its results are
in [runtime evidence](silver_project_region_mapping.md#runtime-evidence).

## Silver MGB flood-area validation

`notebooks/04_validation/06a_validation_silver_mgb_flood_area.ipynb`
validates `02-silver.silver_mgb_flood_area` after
`notebooks/02_silver/08a_silver_mgb_flood_area.ipynb` builds or keeps it.
Tables 14 and 15 stop when this evidence is missing or has a blocking failure.

The validator compares the table with the selected Bronze snapshot on
`object_id` in one full outer join. It reads Bronze lineage and codes only,
never `geometry_json`. It rebuilds every usable geometry from WKB.

The validator persists results to `04-validation.silver_dq_results` before
enforcing its blocking gate. The validation run ID is deterministic for the
parse run and validation-rule version, so an exact rerun updates the same
evidence.

### MGB flood-area data-quality attributes

- Consistency: every published row has a Bronze row, and raw codes equal Bronze.
- Accuracy: usable and repaired geometry rebuilds as a valid, nonempty polygon
  and lies inside the degree screen. Every `REPAIRED_GEOMETRY` row stays within
  the D-43 area tolerance of the MGB `Shape__Area` (STOP).
- Completeness: every Bronze row is published, and the row count equals the
  audited `rows_loaded`.
- Auditability: one deterministic run, complete lineage, and one Bronze ingest run.
- Validity: deterministic keys, governed vocabularies, WKB presence that matches
  the status, and SRID 4326 for usable and repaired geometry.
- Uniqueness: one row per `object_id`, snapshot, and parse rule version.
- Timeliness: the newest MGB load and its Bronze validation are safe, and the
  table holds the latest validated snapshot.

FLAG checks keep unusable geometry, blank codes, geometry outside the degree
screen, and differences from the 63,684-row reference visible. See
[Silver MGB flood areas](silver_mgb_flood_area.md) for the table contract.

On 2026-10-11, `06a` passed all 18 of its STOP checks on parse rule v2, with
297 polygons repaired under D-43 and none outside the area tolerance.
Validators 07 and 08 passed all 37 of their STOP checks each after reading this
table, both before and after the repair. Their results are in
[Silver regional flood exposure](silver_region_flood_exposure.md#geometry-parsing)
and [Silver project flood mapping](silver_project_flood_mapping.md#rerun-after-the-bronze-reload-and-one-time-parsing-issue-92).

## Silver regional flood exposure validation

`notebooks/04_validation/07_validation_silver_region_flood_exposure.ipynb`
validates `02-silver.silver_region_flood_exposure` after Table 14 is rebuilt.

Use this order for the final steps:

1. `notebooks/02_silver/08a_silver_mgb_flood_area.ipynb`
2. `notebooks/04_validation/06a_validation_silver_mgb_flood_area.ipynb`
3. `notebooks/02_silver/09_silver_region_flood_exposure.ipynb`
4. `notebooks/04_validation/07_validation_silver_region_flood_exposure.ipynb`

The validator persists results to `04-validation.silver_dq_results` before
enforcing its blocking gate. The gate reads the persisted rows. The validation
run ID is deterministic for the exposure run and validation-rule version, so an
exact rerun updates the same evidence.

The validator recomputes evidence independently. It reads the published MGB
snapshot from the validated `silver_mgb_flood_area`, rebuilds the expected
region × level grid from current inputs, reparses the selected region
boundaries, and recalculates region areas.

### Regional flood exposure data-quality attributes

- Consistency: CONFIG and PSGC validation are safe, the approved mapping is
  one-to-one, and statuses agree. Boundary statuses reproduce from the source.
  Each region has one denominator. Additivity matches measured overlap.
- Accuracy: levels come only from approved mapping. Area uses the approved
  equal-area CRS, is square kilometres rather than square degrees, matches an
  independent recalculation, and stays inside its region.
- Completeness: every MGB row is accounted for, and every official region and
  approved level has one row. Unmapped rows, unusable geometry, and no-data
  regions stay visible.
- Auditability: mandatory lineage is present, and keys and run IDs reproduce.
  Optional version gaps and geometry parse paths are reported.
- Validity: statuses are controlled, missing geography is `NULL`, and real zero
  is zero. Areas and shares stay in range.
- Uniqueness: keys and the region, level, and run grain are unique.
- Timeliness: the table uses the newest validated MGB and boundary snapshots,
  the current PSGC run, and the current mapping version in one run.

### Regional flood exposure stop checks

Blocking checks protect:

- safe newest MGB and boundary loads and Bronze validation
- safe Silver CONFIG and selected PSGC validation
- published snapshots, PSGC run, and mapping version that are current
- a parsed `silver_mgb_flood_area` with the latest MGB snapshot and the
  `_ingest_run_id` of the current Bronze MGB rows
- one deterministic run
- MGB source-row accounting against the audited row count
- one-to-one approved mapping and approved-only published levels
- the complete dynamic region × level grid
- unique keys and grain, reproducible keys and run ID
- controlled and mutually consistent statuses
- boundary statuses that reproduce from the boundary snapshot
- `NULL` for missing geography and real zero for safe regions without exposure
- positive region area, non-negative susceptible area, and a share from 0 to 100
- the approved equal-area CRS and square-kilometre units
- independent region-area recalculation and clipping inside each region
- dissolve that never increases area
- additivity status that matches measured cross-level overlap
- one denominator and identical region-level values across levels
- source polygon and fragment count contract. `source_polygon_count` counts
  distinct `object_id` values apart from the fragments, so the check can fail
  (#114).
- expected source SRID for usable MGB geometry, read from the stored
  `geometry_srid` (#114)
- mandatory lineage

### Regional flood exposure review flags

Nonblocking checks retain:

- unmapped, blank, and `No rating` MGB rows with per-bucket counts
- mapped rows excluded for unusable geometry
- blank, unparseable, empty, unsupported, and invalid MGB geometry
- usable MGB geometry outside the coarse degree-unit screen
- mapped usable rows without a safe region intersection
- regions without a safe, unambiguous, valid boundary
- unresolved region boundary codes and boundary lineage duplicates
- boundary and PSGC version mismatch
- province-level territory differences between the boundary and current PSGC.
  The validator and notebook 09 use the same null-safe predicate (#114).
- within-level overlap removed by dissolve and cross-level overlap
- any approval of blank or `No rating` codes
- optional MGB publisher and boundary version gaps
- differences from historical Bronze reference counts. The blank-geometry
  reference is 0 since #115.

The validator does not invent an unknown level, repair geometry, deduplicate
boundaries, fabricate a region polygon, or turn missing geography into zero.

See [Silver regional flood exposure](silver_region_flood_exposure.md) for the
complete Table 14 grain, CRS, overlap, lineage, cost, and Gold handoff contracts.
Runtime outcomes require Databricks execution.

## Silver project flood mapping validation

`notebooks/04_validation/08_validation_silver_project_flood_map.ipynb`
validates `02-silver.silver_project_flood_map` after Table 15 is rebuilt.

Use this order for the final steps:

1. `notebooks/02_silver/08a_silver_mgb_flood_area.ipynb` and
   `notebooks/04_validation/06a_validation_silver_mgb_flood_area.ipynb`, when
   they have not run for the current MGB snapshot
2. `notebooks/02_silver/10_silver_project_flood_map.ipynb`
3. `notebooks/04_validation/08_validation_silver_project_flood_map.ipynb`

The validator persists results to `04-validation.silver_dq_results` before
enforcing its blocking gate. The gate reads the persisted rows. The validation
run ID is deterministic for the project-flood run and validation-rule version,
so an exact rerun updates the same evidence.

The validator recomputes evidence independently. It declares the Table 13
coordinate screen itself and recomputes every project's coordinate status. It
reads MGB from the validated `silver_mgb_flood_area` and recomputes source accounting.
It also rebuilds every project's MGB candidates with a different grid size and
compares them with the published evidence row by row.

### Project flood mapping data-quality attributes

- Consistency: CONFIG validation is safe, and one project run, MGB snapshot,
  mapping version, and rule version are published. The approved mapping is
  one-to-one, and published levels and ranks match it. Statuses account for
  every row, and the coordinate screen matches Table 13.
- Accuracy: published candidates equal the independent recomputation. Matched
  points really intersect an approved usable polygon. Multiple distinct levels
  are never collapsed by severity, and same-level overlap stays matched. Only
  approved levels drive a classification.
- Completeness: every canonical project appears exactly once, and MGB rows
  reconcile to the audited load. Coverage is reported against all projects and
  against usable coordinates.
- Auditability: mandatory lineage is present, and keys and run IDs reproduce.
  Publisher versions come only from `load_log`. Version gaps and parse paths are
  reported.
- Validity: values are controlled, and candidate counts agree with candidate
  levels. Matched rows have one level, and unresolved reasons follow the
  coordinate contract. Only safe coordinates take part in matching.
- Uniqueness: keys, the source system, Contract ID, and run grain, and project
  keys are unique.
- Timeliness: the table uses the newest validated MGB and DPWH snapshots, the
  current accepted project run, and the current mapping version in one run.

### Project flood mapping stop checks

Blocking checks protect:

- safe newest MGB and DPWH loads and Bronze validation
- safe Silver CONFIG and selected project validation
- published MGB snapshot, project snapshot, project run, and mapping version
  that are current
- a parsed `silver_mgb_flood_area` with the latest MGB snapshot and the
  `_ingest_run_id` of the current Bronze MGB rows
- one deterministic run and one published version set
- MGB source-row accounting against the audited row count
- one-to-one approved mapping and approved-only levels and ranks
- every canonical project present exactly once
- unique keys, grain, and project keys, and reproducible keys and run ID
- controlled statuses, methods, qualities, and reasons
- consistent `MATCHED`, `AMBIGUOUS`, `UNMATCHED`, and `INVALID_SOURCE` rows
- candidate evidence equal to the independent spatial recomputation
- no severity collapse across distinct levels
- same-level overlap that stays matched with its polygon count
- the Table 13 coordinate contract and safe coordinates only
- expected source SRID for usable MGB geometry, read from the stored
  `geometry_srid` (#114)
- publisher versions taken only from `load_log`
- mandatory lineage

### Project flood mapping review flags

Nonblocking checks retain:

- classification coverage against all projects and against usable coordinates
- projects without usable coordinates, by coordinate status
- usable points without an approved MGB intersection
- projects across multiple approved levels
- projects inside several same-level polygons
- unmapped, blank, and `No rating` MGB rows with per-bucket counts
- mapped rows excluded for unusable geometry
- blank, unparseable, empty, unsupported, and invalid MGB geometry
- any approval of blank or `No rating` codes
- optional MGB and DPWH publisher-version gaps
- MGB geometry parse paths
- differences from historical Bronze reference counts. The blank-geometry
  reference is 0 since #115.

The validator never picks a level for an ambiguous project or invents an unknown
level. It does not repair geometry or treat a missing match as low or zero risk.

See [Silver project flood mapping](silver_project_flood_mapping.md) for the
complete Table 15 grain, coordinate, MGB, spatial, lineage, cost, and Gold
handoff contracts. The first Databricks run passed every STOP check. Its results
are in [runtime evidence](silver_project_flood_mapping.md#runtime-evidence).

## Gold validation

`notebooks/04_validation/09_validation_gold.ipynb` checks the six Gold
dimensions and three Gold facts. It covers issues #60 to #64. It only reads Gold
and Silver, and it never changes them.

Run it after the last Gold fact:

1. `notebooks/03_gold/00_gold_dim_date.ipynb` to
   `notebooks/03_gold/07_gold_fact_project_snapshot.ipynb`, in the
   [Gold build order](gold_model.md#build-order)
2. `notebooks/04_validation/09_validation_gold.ipynb`

The validator saves its results to `04-validation.gold_dq_results` before its
STOP gate runs (D-47). The table has the same columns as `silver_dq_results`,
with `layer = 'gold'`. The gate reads the saved rows.

The validation run ID comes from the run IDs of the three Gold facts and the
rule version `gold-validation-v2`. So an exact rerun updates the same evidence
instead of adding copies.

The expected values live in the validator, not in the Gold notebooks, so Gold
never checks itself. They are the key `0` match rules, the five flood levels,
and the area CRS `EPSG:6933`. The 2024 census total of 112,727,776 people comes
from issue #61.

### Gold stop checks

- **Project fact (#60):** at most one current row per project. Progress is 0
  to 100 or empty. Budget is zero or more, or empty. Every row has a source
  snapshot, and every key finds its dimension row.
- **Population (#61):** primary population is filled and above zero. Each
  official region has exactly one primary source in each year. No population
  row uses region key `0`, so per-person ratios leave it out. The check records
  the denominator of those ratios.
- **Flood (#62):** flood area is zero or more, and its share of the region area
  is 0 to 100. Areas use the equal-area CRS `EPSG:6933`, and the check names the
  CRS it found. Levels are Unknown, Low, Moderate, High and Very High. Each
  source system and version has one severity rank per level.
- **Grain and keys (#63):** every fact and dimension passes its uniqueness rule
  from the [data model](data-model.md#required-analytical-validation). The
  date, region, flood and status dimensions each have one key `0` row. Key `0`
  appears only in the documented cases. Central Office uses region key `0` with
  the `NON_GEOGRAPHIC` match status.
- **Lineage (#63):** lineage columns are filled in every table that has them.
  `dim_date` is built from a date range, so it has none.
- **Totals (#64):** Gold rows, budgets, population and flood areas equal Silver.
  Project counts and budgets also match Silver region by region. Current
  project rows must use the DPWH snapshot that Silver holds now. The details
  record the Gold and Silver runs and the snapshot.

Two more STOP checks come from the review of #60. Every
`silver_project_flood_map` row needs an MGB load time, because a count of
distinct load times skips empty ones. Also, every current Gold project row must
still be in Silver.

The population and flood facts have no current flag, and their `MERGE` never
deletes. A new PSGC version, MGB snapshot, or boundary version would leave the
old rows in place. The row checks stop the run when Gold has more rows than
Silver, so old rows can't double a total unnoticed.

### Gold review flags

FLAG checks keep known data limits visible with their counts:

- projects without a region, by match status
- projects without a flood level, by match status and coordinate status
- projects without a status
- progress that Silver did not mark `VALID`
- projects without a long-running flag because they have no start date, or their
  completion date is before the start date (D-49)
- region and level pairs with no area data
- official regions without a boundary, and boundary shapes marked not valid
- active statuses that look like numbers or map points, from DPWH rows split
  by a line break
- the gap between the Gold population and the 2024 census total, with the
  unmatched Table C rows behind it

Every check names the columns it tested in `details`.

### Gold checks that wait for the marts

Issue #61 also asks that a mart that uses region key `0` in a ratio fails.
The analytics validator now runs this check on `analytics_population_equity`.
See [analytics validation](#analytics-validation).

### Gold validation runtime evidence

On October 12, 2026, `09_validation_gold.ipynb` ran twice in the team workspace
on serverless compute. It ran from commit `dc2c516` of branch
`validation/issues-60-64-gold-checks`, with rule version `gold-validation-v2`.
Both runs wrote the same 75 checks under one validation run ID, so the second
run updated the rows instead of adding copies. All 65 STOP checks passed.

The FLAG checks found:

| Check | Rows | Out of |
| --- | ---: | ---: |
| Projects without a region (key `0`): 306 Central Office, 266 unmatched | 572 | 265,656 |
| Projects without a flood level (key `0`): 250 ambiguous, 50,518 with no map point, 102,178 unmatched | 152,946 | 265,656 |
| Projects without a status (key `0`) | 76 | 265,656 |
| Progress not published because Silver did not mark it `VALID` | 98 | 265,656 |
| Long-running flag is empty because there is no start date | 20,039 | 265,656 |
| Region and level pairs with no area data | 20 | 72 |
| Official regions without a boundary | 1 | 18 |
| Active statuses that are shifted numbers: `0.00` and `121.0181138` | 2 | 18 |
| Table C rows behind the 4,789-person gap to the 2024 census total | 2 | 43,750 |

The other FLAG check found nothing.

An earlier run that day, from commit `6770773`, used rule version
`gold-validation-v1` and 76 checks. It found the same FLAG counts. After the
review of #123, 3 STOP checks also fail on empty values. The FLAG for an empty
population count is now part of a STOP check. So the rule version changed.

On October 12, 2026, `09_validation_gold.ipynb` ran again after the changes for
issues #116 and #119, from commit `ff7cacc` of branch
`feature/issues-116-117-118-119-120-121`. It wrote 75 checks. All 65 STOP checks
passed. 9 FLAG checks had findings, and 1 found nothing. The long-running FLAG
now counts 20,045 projects: 20,039 without a start date and 6 with a completion
before the start (D-49).

On October 13, 2026, `09_validation_gold.ipynb` ran again after the Silver audit
fixes for issues #109 to #115, from commit `dbd1824` of branch
`fix/issue-109-stale-mgb-gate`. It wrote 75 checks under validation run ID
`eb6145ab…`. All 65 STOP checks passed. 9 FLAG checks had findings, and 1 found
nothing. Every FLAG count equals the run above. The rows are in
[`issue-109-115-gold-validation-2026-10-13.csv`](evidence/silver/issue-109-115-gold-validation-2026-10-13.csv).

## Analytics validation

`notebooks/04_validation/10_validation_analytics.ipynb` checks the six Analytics
views in `05-analytics` that the dashboard and Genie read (D-56, proposed),
including the D-57 province reporting area in views 1, 2, 4, 5, and 6. It
only reads Gold, the views, `information_schema.views`, and the validation
results. It writes only `04-validation.analytics_dq_results`.

Run it after the views:

1. `notebooks/04_validation/09_validation_gold.ipynb`, which must pass
2. `notebooks/04_validation/09a_validation_gold_province_reporting.ipynb`, which must pass
3. `notebooks/05_analytics/01_business_questions.ipynb`
4. `notebooks/04_validation/10_validation_analytics.ipynb`

The validator reads current Gold once, then rebuilds every view with its own
SQL and compares it row by row. The expected values live in the validator, not
in the analytics notebook, so a view never checks itself. The shared rules, such
as the flood point class and the status reason, are written in a different form
from the views on purpose.

The six views and their grains are in the
[Analytics views guide](../notebooks/05_analytics/README.md).

### Analytics gates

Three gates run before any check. Each stops the run with an error and saves no
evidence:

- **One current snapshot:** current `fact_project_snapshot` rows must hold
  exactly one DPWH snapshot, with no empty snapshot ID. The analytics notebook
  runs the same gate before it builds the views.
- **Gold passed:** the latest Gold validation that checked the current project,
  population, and exposure facts together has no failed STOP check. A later
  partial run, such as the province validator, cannot hide it.
- **Province Gold passed:** the latest `09a_validation_gold_province_reporting`
  run of the current project fact exists, covers the reporting-area dimension
  and population fact, and has no failed STOP check (D-57).

### Analytics stop checks

There are 84 STOP checks. A failed one is `FAIL`, and the gate stops the run.

| Group | What the checks prove |
| --- | --- |
| Layer contract | `05-analytics` holds all six D-56 views, and no retired or unexpected view. `analytics_region_project_progress` does not exist. |
| Grain and keys | One row per documented grain in each view, no `NULL` key, and every expected row present with no extra row. View 1 has exactly the `REGION` and `REPORTING_AREA` levels. |
| Measures | Every count, budget, average, share, rank, running share, gap, ratio, per-capita value, area, flag, date, and review indicator equals a separate rebuild from Gold. |
| `NULL` handling | Budgets compare with `<=>`, so a `NULL` that turned into `0` breaks. Unavailable progress, dates, population, and area stay `NULL`. A region with no mapped project keeps `NULL` flood figures. |
| Project reconciliation | Each level of view 1 plus its key `0` and unknown keys adds up to every current project and budget. Region totals are rebuilt from `region_key`, never from reporting areas. Views 4 and 5 hold every current project once. Every link of view 6 adds up to every current project and budget. At most one current Gold row exists per project. |
| Population | View 2 population equals the newest Gold primary reporting-area population, and its total adds up to it. Per-person ratios leave key `0` out (#61). Views 5 and 6 read the same population. |
| Accounting | Flood classes cover every project outside key `0`. Flood-control, other, and uncategorized add up to each row. Region-linked and reporting-area-linked projects equal Gold. Matched and unmatched rows of every link add up to Gold. |
| Hierarchy | The region and province hierarchy status of view 5 and view 6 follows the two Gold keys. A conflict is reported, never forced. |
| Shares | Every share and percentage is between 0 and 100. Cohort, region, equity, flood-control, and link shares add up to 100 within 0.01. |
| Coverage and key `0` | Only `REPORTED` regions are ranked or compared. BARMM is never ranked. No regional view has a key `0` row. |
| Interpretation | A `For Procurement` project never raises a progress indicator (D-46). Area appears only on MGB level rows. |
| Lineage | Every view carries the current DPWH snapshot ID, view 3 also the MGB snapshot ID, and views 1 and 4 the snapshot date (D-29). |
| Rerun | A rerun on the same Gold data gives the same failed and total rows for every saved check. |

### Analytics review flags

There are 28 FLAG checks. They keep known source limits visible with their
counts:

- projects left out on region key `0` and on reporting area key `0`, by match status
- projects with no `infra_year`, and projects with no reported budget
- regions with no or limited DPWH coverage, regions outside the equity
  comparison, and regions without a primary population
- flood-control projects not placed in one MGB level, ambiguous points, and
  regions whose levels overlap or have no evaluated exposure
- projects with at least one review indicator, unresolved statuses, projects
  without a long-running flag, and zero-progress flags that disagree with the
  published progress
- projects without a mappable point, mappable projects on key `0`, and projects
  whose region differs from the parent region of their reporting area
- the unlinked projects of each integration link, and region and province
  conflicts

A FLAG check that finds nothing is `PASS`. Every check names the columns it
tested in `details`.

### Analytics evidence and reruns

The validator saves its results to `04-validation.analytics_dq_results` with
`MERGE`, before its STOP gate runs (D-52). The table has the same columns as
`gold_dq_results`, with `layer = 'analytics'`. The gate reads the saved rows, so
a failed check stays visible after the run stops.

The validation run ID is a SHA-256 hash of the run IDs of `fact_project_snapshot`,
`dim_region`, `fact_region_population`, `fact_region_flood_exposure`,
`dim_province_reporting_area`, and `fact_province_reporting_area_population`, and
the rule version `analytics-validation-v4`. The rule version moved to v3 with the
six-view contract and to v4 with the province reporting area. D-57 adds the two
province runs to the D-52 recipe, so new province data gives a new ID. Earlier
evidence stays as it was. The `MERGE` key is the validation run ID, the table,
and the check name. A rerun on the same Gold data updates the same rows, and the
rerun check proves the results did not change.

### Analytics validation runtime evidence

The six-view contract first ran on Databricks on October 16, 2026, in job run
`1077732256280159`. Validation run
`2b0558751cb722b38b61b16d97a4f974318b36a939232af669defc59d555e933` saved 112
checks: 84 STOP checks passed, 26 FLAG checks reported findings, and 2 FLAG
checks passed. `05-analytics` held exactly the six views, and every rebuild from
Gold matched its view with no break. The rerun check compared no saved rows,
because it was the first run of that validation run ID. Run the validator once
more on the same Gold data to prove rerun stability. See the
[six Analytics views evidence](evidence/six-analytics-views/README.md).

The earlier runs validated the retired designs and stay as history only:

- the October 12, 2026 run of the six D-50 views under v1, in the
  [analytics evidence](evidence/analytics-views/README.md)
- the run of all eleven views under v2, in the
  [exploratory analytics evidence](evidence/exploratory-analytics-views/README.md)
- the October 15, 2026 run of the five retired `analytics_reporting_area_*`
  views, in the [province-reporting evidence](evidence/province-reporting/README.md).
  Its Silver and Gold province results stay valid for the snapshot they name.
- the October 15, 2026 run of the withdrawn D-55 view, in the
  [regional progress evidence](evidence/regional-project-progress/README.md)

### Known gap: dimension runs in the Gold gate

The Gold gate checks that the latest Gold validation of the current project fact
passed and covers the current population and exposure facts. It does not check
that the same validation covered the current `dim_project`,
`dim_project_status`, `dim_flood_susceptibility`, and `dim_date` runs, and the
validation run ID does not include them (D-52). If one of them were rebuilt
after `09_validation_gold` and before this validator, the gate would not notice.
The documented run order, `09_validation_gold` then the views then this
validator, avoids the gap. A fix that adds the dimension runs to the gate is a
separate follow-up. It needs its own review against D-52.

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

## Province reporting-area validation

`03b_validation_silver_province_reporting` persists checks for the reporting-area
reference, selected boundary status, accepted-primary population, and final
project map. STOP checks cover one row per project, unique deterministic keys,
valid targets, complete lineage, config ambiguity, accepted population,
canonical project count, and reported-budget reconciliation. FLAG checks retain
missing coordinates, zero and multiple candidates, conflicts, unresolved areas,
NCR, independent-city, and BARMM findings.

Rule version `silver-province-reporting-validation-v2` adds five STOP checks for
the population contract (D-57): each contributing Table C row is counted once,
every reporting area has one official parent region, the reporting-area total
equals the region total, no region has more reporting-area population than its
own total, and region minus reporting-area population equals the population left
on key `0`. Two FLAG checks report that unresolved and excluded population in
people, and one counts the regions that hold unresolved population.

`09a_validation_gold_province_reporting` then checks dimension and fact keys,
one Unknown, parent regions, reporting-area orphans, unchanged current project
grain, unchanged reported budget, population reconciliation, one current
snapshot, and lineage. Rule version `gold-province-reporting-validation-v2` adds
STOP checks for a unique PSGC code per version, a parent region that exists in
`dim_region`, the same three population reconciliations against
`fact_region_population`, and key `0` holding exactly the unresolved and
non-geographic projects. Two FLAG checks count projects whose region differs
from the parent region of their reporting area, and projects with a region but
no reporting area. A FLAG check with findings is saved as `FLAG`, the same as in
`03b`. The October 16, 2026 run saved these two rows as `FAIL` with action `flag`
before that fix. They were findings, not failures, and did not block the run.

`10_validation_analytics` validates the province content of the six Analytics
views (D-56). See [analytics validation](#analytics-validation). The first
province validator, `10a_validation_provincial_analytics`, checked the five
retired `analytics_reporting_area_*` views and is removed.

All three validators `MERGE` evidence before their STOP gate. Their local tests
prove contract text and ordering only. All three ran on Databricks on October 16,
2026, with no failed STOP check. See the
[six Analytics views evidence](evidence/six-analytics-views/README.md).

### Province-reporting acceptance publication

`11_publish_acceptance_evidence.sql` consolidates the latest D-57 rows from
`silver_dq_results`, `gold_dq_results`, and `analytics_dq_results`. It publishes
current mapped and unmapped project and budget coverage, mapping-method totals,
NCR, independent-city, and BARMM totals, population coverage and exclusions,
selected PSGC, boundary, configuration, and rule versions, and boundary
availability.

Each execution appends one compact record to
`province_reporting_acceptance_runs`. The record includes the deterministic
project-map run ID and a commutative checksum over the complete mapping output.
Run the publisher once, rerun the Silver project map and its validator with
unchanged inputs, and run the publisher again. `exact_rerun_status = 'PASS'`
requires the two latest captures for the source snapshot to retain both the map
run ID and mapping checksum. The first capture reports `RERUN_REQUIRED` rather
than inventing rerun evidence.

The October 15, 2026 execution recorded 43 passed checks and retained five
non-blocking Silver coverage flags. Two captures retained one project-map run
ID and one mapping checksum. The complete identities, coverage, budgets,
special-area totals, population values, boundaries, and limitations are in the
[province-reporting runtime evidence](evidence/province-reporting/README.md).

The October 16, 2026 execution published 159 checks under the v2 province rules
and `analytics-validation-v4`: Silver 23, Gold 24, and Analytics 112, with no
failed STOP check. The exact-rerun comparison passed against the October 15
capture with the same project-map run ID and mapping checksum. See the
[six Analytics views evidence](evidence/six-analytics-views/README.md).
