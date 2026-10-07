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
| `silver_dpwh_project_component` | Implemented. Databricks execution required. |
| `silver_project` | Implemented. Databricks execution required. |
| Silver project validation | Implemented. Databricks execution required. |
| Flood-control component and source-match outputs | Implemented in the follow-up source-reconciliation milestone. Databricks execution required. |
| `silver_project_region_map` and its validator | Implemented in the follow-up project-region milestone. Databricks execution required. |
| `silver_project_flood_map` and its validator | Implemented in the follow-up project-flood milestone. Databricks execution required. |
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

Natural key:

- Contract ID
- Bronze source lineage

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

### Component lineage

The table retains:

- `_source_snapshot_id`
- `_ingest_run_id`
- `_source_modified_at`

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
- transformation rule version

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

### Stop checks

Stop conditions include:

- empty source tables
- row-accounting failures
- project-grain duplication
- lineage failures
- invalid project accounting

### Flag checks

Flag conditions include:

- invalid budgets
- invalid dates
- invalid progress
- unparseable coordinates
- unusual status values
- conflicting project attributes
- unresolved project budgets

Flag findings remain visible for review.

## Known limitations

- Approved category mappings are not yet published into the component output.
- Approved status mappings are not yet published into the component output.
- Project-region assignment is implemented separately. See
  [Silver project-to-region mapping](silver_project_region_mapping.md).
- Flood-control reconciliation is implemented separately. See [Silver source reconciliation](silver_source_reconciliation.md).
- Long-running classification remains unresolved.
- Stalled classification remains unresolved.
- Databricks execution is required before validation outcomes can be claimed.

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
