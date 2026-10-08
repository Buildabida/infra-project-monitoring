# Silver Project Foundation

This milestone implements the DPWH project foundation layer.

It creates a row-preserving project component table and a project-level consolidation table.

These tables support implemented geographic matching and source reconciliation,
plus future delivery analysis, portfolio analytics, and Gold project facts.

This milestone does not implement:

- flood-control reconciliation
- project-region assignment within this foundation milestone. It is implemented
  by the follow-up Table 13 milestone
- flood-risk analysis
- Gold dimensions
- Gold facts
- population-adjusted metrics

## Source authority

DPWH Projects remains the authoritative source for:

- Contract IDs
- project descriptions
- project status
- project progress
- reported project budget
- source dates
- contractor information
- project coordinates

The production path remains:

```text
DPWH API
    ↓
Bronze
    ↓
Silver
```

Local files may support profiling and schema review, but the production notebooks do not depend on developer-specific file paths.

## Implementation status

| Item | Status |
| --- | --- |
| Five Silver configuration tables | Implemented |
| `silver_psgc_place` | Implemented |
| `silver_population_place_reconciliation` | Implemented |
| `silver_region_population` | Implemented |
| `silver_dpwh_project_component` | Implemented. Runtime-validated in Databricks for the selected DPWH snapshot. |
| `silver_project` | Implemented. Runtime-validated in Databricks for the selected DPWH snapshot. |
| Silver project validation | Implemented. All STOP checks passed in Databricks. See [runtime evidence](#runtime-evidence). |
| Flood-control component and source-match outputs | Implemented in the follow-up source-reconciliation milestone. Databricks execution required. |
| `silver_project_region_map` and its validator | Implemented in the follow-up project-region milestone. Databricks execution required. |
| `silver_project_flood_map` and its validator | Implemented in the follow-up project-flood milestone. Runtime-validated in Databricks for the selected snapshots. |
| Gold dimensions and facts | Planned |

## Dependency order

Run the notebooks in this order:

1. `02_silver/00_config_mappings.ipynb`
2. `04_validation/02_validation_silver_config.ipynb`
3. `02_silver/04_silver_dpwh_project_component.ipynb`
4. `02_silver/05_silver_project.ipynb`
5. `04_validation/04_validation_silver_projects.ipynb`

When project or geography inputs changed and the foundation validator passes,
continue with:

1. `02_silver/08_silver_project_region_map.ipynb`
2. `04_validation/06_validation_silver_project_region_map.ipynb`
3. `02_silver/10_silver_project_flood_map.ipynb`
4. `04_validation/08_validation_silver_project_flood_map.ipynb`

Do not run a dependent notebook after a blocking failure.

## Bronze safety gate

Before Silver reads DPWH projects, it validates the latest terminal Bronze load.

The selected load must have:

- `SUCCESS` or `SKIPPED_IDEMPOTENT`
- a nonblank snapshot identifier
- positive loaded rows

The validator also confirms that the latest blocking Bronze validation contains no `FAIL` or `ERROR` results.

The gate reads audit evidence and validation outputs rather than rescanning source systems.

## `silver_dpwh_project_component`

Purpose: preserve every selected Bronze DPWH source row while safely parsing supported project fields and retaining source lineage.

Grain: one DPWH source record per selected source snapshot.

Primary key: `component_key`.

Source-row identity:

- `_source_snapshot_id`
- `source_row_hash`, a SHA-256 of every Bronze business field that Silver reads
- `source_row_ordinal`, which numbers rows that are identical on all of those fields

Bronze has no DPWH source row number. Identical rows are interchangeable, so the ordinal is the same on every run. `component_key` hashes the snapshot, the row hash, and the ordinal. It needs no random ID and no file order.

The component table preserves source evidence before project-level consolidation.

Repeated Contract IDs remain visible. The table does not use undocumented deduplication, `DISTINCT`, `dropDuplicates`, or arbitrary row-selection logic.

### Supported parsing

The component table preserves raw values and creates parsed values where possible.

Fields include:

- project description
- category
- status
- reported budget
- physical progress
- start date
- completion date
- latitude
- longitude

Safe parsing uses `TRY_CAST`.

Invalid values remain visible and are not automatically corrected.

### Coordinate handling

The component table creates:

- `VALID_PAIR`
- `MISSING_PAIR`
- `PARTIAL_PAIR`
- `UNPARSEABLE`

Coordinate status is diagnostic only.

The table does not assign PSGC geography or perform spatial matching.

### Quality statuses

Each parsed field has a status, so a reader can tell why a value is `NULL` or suspect. Values stay as parsed. Silver flags them but does not change them.

| Column | Values |
| --- | --- |
| `budget_quality_status` | `VALID`, `MISSING`, `UNPARSEABLE`, `NEGATIVE` |
| `progress_quality_status` | `VALID`, `MISSING`, `UNPARSEABLE`, `OUT_OF_RANGE` |
| `infra_year_quality_status` | `VALID`, `MISSING`, `UNPARSEABLE` |

The progress range is 0 to 100, from the required analytical validation in [Data model](data-model.md#required-analytical-validation-planned). It is declared once in the notebook's parameter view.

`infra_year` keeps the raw string. `infra_year_parsed` adds the integer, so Gold does not need to cast it.

### Governed mapping join

Category and status rules join on the key values in [Silver configuration mappings](silver_config_mappings.md#key-values-for-dpwh-rules). Before this change, the category join ignored `source_system` and `source_infra_type`, and the status join used `'DPWH'`, which approved rules never use. Both mapping tables were empty, so no output changed, but the first approved rule would have either copied rows or never matched.

`category_mapping_state` and `status_mapping_state` are `MAPPED` or `UNMAPPED`. An unmapped row keeps its raw value and a `NULL` standardized value.

### Component lineage

The table retains:

- `_source_snapshot_id`
- `_ingest_run_id`
- `_source_modified_at`
- `run_id`, a SHA-256 of the snapshot and the rule version
- `transformation_rule_version`, now `silver_dpwh_component_v2`

These fields preserve traceability back to the selected Bronze snapshot.

## `silver_project`

Purpose: create one canonical project-level record suitable for downstream matching, portfolio analysis, delivery analysis, and future Gold project facts.

Grain: one project per Contract ID.

Natural key:

- `project_key`

The project table is built only from `silver_dpwh_project_component`.

It does not reread and independently clean Bronze data.

### Project consolidation

Component-level evidence is evaluated before a canonical value is published.

Resolution rules are:

| Distinct values | Outcome |
| --- | --- |
| 0 | Missing |
| 1 | Resolved |
| More than 1 | Conflict |

Conflicting values remain visible rather than being silently resolved.

### Budget double-count protection

Repeated component rows must not inflate project investment values.

The table supports:

- resolved single budgets
- resolved repeated identical budgets
- conflicting budgets
- missing or invalid budgets

Multiple distinct budgets do not automatically become a summed project total.

### Same expression for count and value

Each attribute's distinct count and published value use the same expression. Before this change, `reported_region`, `contractor`, and `source_of_funds` counted untrimmed values but published trimmed ones. A value that differed only by spaces showed a count of 2 and still resolved.

Columns added for downstream use:

- `reported_region_resolution_status`, so Table 13 can tell a missing region from conflicting ones
- `infra_year_parsed` and `infra_year_resolution_status`
- `progress_quality_status` and `budget_quality_status`, carried from the component that holds the resolved value
- `category_mapping_state`
- `source_system` and `component_run_id`

No column was removed or renamed. `project_key` uses the same recipe, so keys do not change.

### Delivery-rule fields

The project table currently supports:

- `zero_progress_flag`

The project table intentionally leaves:

- `stalled_flag`
- `long_running_flag`

unresolved until their required governed inputs are available.

The implementation does not use the current date to derive long-running status.

### Project lineage

The table retains:

- source snapshot identity
- source ingest identity
- deterministic project key
- deterministic run identity
- transformation rule version, now `silver_project_v2`
- the component run it was built from

The rule version changed, so `run_id` changed. Tables 13 and 15 check that they were built from the current project run. Rerun them and their validators after this notebook.

## Idempotency and cost

Stable identities use deterministic hashes and preserved lineage.

The implementation does not use:

- random UUID values
- streaming
- Python UDFs
- spatial functions
- cache or repartition operations
- unnecessary source scans

Tables are rebuilt using:

```sql
CREATE OR REPLACE TABLE
```

to avoid duplicate logical rows.

## Validation

`04_validation_silver_projects.ipynb` validates:

- Bronze-to-component row preservation
- component-to-project accounting
- project uniqueness
- budget resolution
- lineage completeness
- source-quality findings

The validator covers all seven data-quality attributes. Each check shows its failed rows and its denominator. The full list is in [Data-quality checks](validation.md#silver-project-validation).

### Stop checks

Stop conditions include:

- empty component table
- Bronze-to-component and component-to-project row accounting
- duplicate component keys, Contract IDs, or project keys
- blank Contract IDs
- quality or mapping states outside the controlled values
- quality statuses that disagree with their values
- budgets that break the no-double-count rule
- zero-progress flags that disagree with progress
- mapped rows without a mapping version
- missing or non-reproducible keys, run IDs, and lineage
- more than one snapshot or run, or a snapshot that differs from the latest Bronze load

### Flag checks

Flag conditions include:

- unmapped categories and statuses
- coordinate exceptions
- repeated identical source rows, kept and counted
- unparseable or negative budgets
- unparseable or out-of-range progress
- unparseable infrastructure years and dates
- conflicting project attributes

Flag findings remain visible for review.

## Runtime evidence

The first Databricks run of the hardened foundation used these inputs:

| Input | Value |
| --- | --- |
| DPWH snapshot | `metadata-6321c7aa6f2a14e12f4c` |
| Bronze load status | `SKIPPED_IDEMPOTENT`, 265,661 rows loaded |
| Approved category and status rules | 0 and 0 |
| Component rule version | `silver_dpwh_component_v2` |
| Component run ID | `915af77484fcdb363d8a74146ab3e4ae8ed1d827c508241d0bd618e8ec0172cd` |
| Project rule version | `silver_project_v2` |
| Project run ID | `add5661e4e762ac48a270a437356933bc499a130186cc1f664561364face3449` |

The validator wrote 29 checks to `04-validation.silver_dq_results`. All 19
STOP checks passed. Of the 10 FLAG checks, 9 reported findings and 1 found
none.

### Row accounting

| Measure | Rows |
| --- | ---: |
| Bronze DPWH rows | 265,661 |
| Component rows | 265,661 |
| Distinct Contract IDs | 265,656 |
| Project rows | 265,656 |
| Component rows accounted for by projects | 265,661 |

- Two component rows are identical to an earlier row on every Silver field. They stay in the table and are counted.
- Two projects have at least one conflicting attribute.
- No project has conflicting budgets. 87 projects have no usable budget.
- The resolved reported budget across projects is PHP 6,535,616,688,962.02. It is a reported budget, not a payment.

### Component findings

The denominator is 265,661 component rows.

| Finding | Rows |
| --- | ---: |
| No approved category rule | 265,661 |
| No approved status rule | 265,661 |
| Missing, partial, or unparseable coordinate pair | 50,523 |
| Missing budget | 79 |
| Unparseable budget | 10 |
| Negative budget | 0 |
| Missing progress | 79 |
| Unparseable progress | 5 |
| Progress outside 0 to 100 | 17 |
| Missing infrastructure year | 94 |
| Unparseable infrastructure year | 11 |
| Unparseable start or completion date | 16 |

The missing counts are derived from the coverage query. They equal each
field's non-`VALID` rows minus its unparseable, negative, or out-of-range rows.

At the project level, 16 projects resolve to progress outside 0 to 100, and
255 projects have no single reported region.

The 50,523 coordinate exceptions include missing, partial, and unparseable
pairs. D-28 records 50,522 rows without coordinate pairs. This run does not
split the 50,523 by type, so the difference of one row is not yet explained.

## Known limitations

- No category or status rule is approved yet, so every row is `UNMAPPED`. The join is ready for approved rules.
- Project-region assignment is implemented separately. See
  [Silver project-to-region mapping](silver_project_region_mapping.md).
- Flood-control reconciliation is implemented separately. See [Silver source reconciliation](silver_source_reconciliation.md).
- Long-running classification remains unresolved in Silver.
- Stalled classification remains unresolved. It needs an approved status mapping.
- The implementing office is not published. No DPWH Bronze field for it has been confirmed in this repo.
- Tables 13 and 15 were rerun on this project run. Both validators passed every STOP check. See [Table 13 runtime evidence](silver_project_region_mapping.md#runtime-evidence) and [Table 15 rerun evidence](silver_project_flood_mapping.md#rerun-on-project-rule-version-2).

## Open questions for the team

1. **Unmapped labels.** The team notes say unmapped values use `Unknown`. Silver publishes `NULL` with `category_mapping_state = 'UNMAPPED'`. Decide which one Silver publishes, then record it in [decisions](decisions.md).
2. **Long-running rule location.** Draft decision D-32 is on an open Gold branch and computes the flag in Gold. The team notes list it as a Silver rule. Decide where it lives. If it lives in Silver, `silver_project` needs the snapshot date from `01-bronze.load_log`.
3. **Implementing office.** Confirm whether DPWH Bronze has a district office field such as `deo`. If it does, add it to the component and project tables.

## Gold handoff

`silver_dpwh_project_component` supports project reconciliation.

`silver_project` supports:

- implemented `silver_project_source_match`
- implemented `silver_project_region_map`
- implemented `silver_project_flood_map`
- future `dim_project`
- future `fact_project_snapshot`

Gold should not need to repeat:

- safe parsing
- project accounting
- repeated Contract-ID handling
- budget protection
- project conflict detection
- project lineage
