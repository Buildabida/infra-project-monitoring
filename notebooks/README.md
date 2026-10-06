# Pipeline notebooks

These Databricks notebooks present the Bronze batch as a documented sequence of
small, reviewable steps. Narrative cells explain each decision. Code cells delegate
shared mechanics to `src/bronze.py` and source contracts to `src/config.py`.

Silver uses SQL cells in Databricks notebooks.
Governed mappings remain separate from geography and population transformations.

## Bronze principles

- **Raw preserving:** Source business values and legitimate duplicate rows remain.
- **Batch-based:** One bounded CSV artifact is selected for each source.
- **Idempotent:** A skip is safe only when the current table and artifact identity agree.
- **Parameterized:** Widgets select snapshot, version, and path behavior without duplicating constants.
- **Snapshot-aware:** Rows and `load_log` link Bronze to the R2 artifact.
- **Low cost:** Metadata and header checks precede Spark. Strings avoid schema inference.
  Large-source validation uses grouped calculations.
- **Resilient:** Malformed artifacts fail before replacement. Delta writes are atomic.
  Conflicts are audited, and failures remain visible.

## Documented sequence

| Step | Notebook | Responsibility |
| --- | --- | --- |
| 1 | `00_setup/00_setup_workspace` | Define missing schemas and verify the existing R2-backed volume without destructive setup. |
| 2 | `00_setup/01_check_sources` | Check all six files, metadata, CSV headers, and required field groups without full Spark scans. |
| 3 | `01_bronze/01_bronze_dpwh_projects` | Preserve DPWH project rows and raw business values. |
| 4 | `01_bronze/02_bronze_flood_control` | Preserve source features and legitimate repeated Contract IDs. |
| 5 | `01_bronze/03_bronze_psgc` | Preserve the geographic reference. Keep population as a cross-check only. |
| 6 | `01_bronze/04_bronze_census_table_c` | Preserve authoritative Table C rows, including known BARMM copies. |
| 7 | `01_bronze/05_bronze_boundaries` | Preserve boundary geometry without project mapping or spatial joins. |
| 8 | `01_bronze/06_bronze_flood_susceptibility` | Preserve the approved trimmed MGB extract with low-compute mechanics. |
| 9 | `04_validation/01_validation_bronze` | Record grouped STOP and FLAG checks without changing Bronze. |
| 10 | `04_validation/02_bronze_acceptance_evidence` | Summarize the latest load and validation evidence without rescanning data. |
| 11 | `02_silver/00_config_mappings` | Create five versioned configuration tables and report mapping coverage. |
| 12 | `04_validation/02_validation_silver_config` | Validate Silver configuration structure, governance, and Bronze coverage. |
| 13 | `02_silver/01_silver_psgc_place` | Standardize the selected official PSGC hierarchy without dropping source rows. |
| 14 | `02_silver/02_silver_population_place_reconciliation` | Reconcile every current Table C row through contextual PSGC matching and approved aliases. |
| 15 | `02_silver/03_silver_region_population` | Aggregate only accepted matched barangay population to official PSGC regions. |
| 16 | `04_validation/03_validation_silver_geography_population` | Validate row accounting, matches, lineage, region coverage, and population totals. |
| Bronze coordinator | `run_all.py` | Enforce order, require six safe results, and validate only after the complete Bronze batch. |

## Load Bronze

### Before running

Confirm that you can access the `buildabida-capstone` catalog and this R2-backed
volume directory:

```text
/Volumes/buildabida-capstone/00-source/cloudflare-r2/buildabida/
```

The directory must contain the six files configured in `src/config.py`:

```text
dpwh_projects.csv
flood_control_projects.csv
psgc.csv
population_2024_table_c_test.csv
boundary_bettergov.csv
flood_susceptibility.csv
```

Run these setup notebooks first:

1. `00_setup/00_setup_workspace.sql` defines missing schemas and verifies the
   existing source volume.
2. `00_setup/01_check_sources.py` checks file access, metadata, CSV headers, and
   required field groups without scanning each complete dataset.

Resolve any setup or source-precheck failure before loading Bronze.

### Run the complete Bronze batch

Open `run_all.py` in Databricks, select Serverless compute, and run all cells. This
file is the current Source-to-Bronze coordinator. It does not run Silver or Gold.

The coordinator runs the six source notebooks in order. It starts grouped Bronze
validation only after every source returns a safe status.

The coordinator accepts these optional parameters:

- `snapshot_id`: Leave blank to derive a deterministic ID from each file's metadata.
- `source_version`: Supply a publisher or release label when one is available.
- `force_reload`: Keep `false` for a normal run. Use `true` only for an intentional
  replacement of an otherwise identical selected snapshot.

Use each source notebook directly only for a controlled test that needs the
`source_path` override.

### Expected result

Each source must return one of these statuses:

- `SUCCESS`: The selected snapshot was committed and audited.
- `SKIPPED_IDEMPOTENT`: The current table already contains the exact snapshot,
  matching artifact identity, and expected row count.

Any other source result blocks validation. A successful coordinated run also
finishes `04_validation/01_validation_bronze` without a blocking check failure.

Review the stored results here:

- `buildabida-capstone.01-bronze.load_log` contains ingestion audit records.
- `buildabida-capstone.04-validation.dq_results` contains grouped validation results.
- `04_validation/02_bronze_acceptance_evidence.sql` summarizes the latest accepted
  load and validation evidence without rescanning the Bronze tables.

## Load Silver

Silver currently implements:

- five configuration tables
- three geography and population outputs
- silver_dpwh_project_component
- silver_project
- silver project validation

Flood-control reconciliation and project-mapping outputs remain planned.

Run these notebooks after Bronze has passed its blocking checks:

1. `02_silver/00_config_mappings.ipynb`
2. `04_validation/02_validation_silver_config.ipynb`

The configuration notebook creates these Delta tables:

- `02-silver.config_place_name_alias`
- `02-silver.config_project_category_mapping`
- `02-silver.config_project_status_mapping`
- `02-silver.config_mgb_susceptibility_mapping`
- `02-silver.config_manual_geographic_match`

Only the four documented MGB code mappings are seeded.
The other tables stay empty until a reviewer approves their rules.

Review the coverage output before running the validator.
The validator saves evidence in `04-validation.silver_config_dq_results`.

Run both notebooks in Databricks.
Local tests verify notebook structure but cannot create Unity Catalog tables.

See [Silver configuration mappings](../docs/silver_config_mappings.md) for table
grains, approval rules, and cost controls.

### Geography and population

After CONFIG validation passes every stop check, run:

1. `02_silver/01_silver_psgc_place.ipynb`
2. `02_silver/02_silver_population_place_reconciliation.ipynb`
3. `02_silver/03_silver_region_population.ipynb`
4. `04_validation/03_validation_silver_geography_population.ipynb`

The PSGC table must succeed before Table C reconciliation.
Reconciliation must succeed before region aggregation.
Do not continue after a blocking check failure.

The validator stores results in `04-validation.silver_dq_results` before enforcing its
gate. Review every `FLAG`, especially ambiguous and unmatched rows, without deleting them.

These notebooks use only current Bronze PSGC, current Bronze Table C, approved place
aliases, and compact audit evidence. They do not scan project, boundary, or MGB data.

See [Silver geography and population](../docs/silver_geography_population.md) for grains,
matching rules, population authority, lineage, and known limitations.

### Project foundation

After Silver configuration validation passes, run:

1. `02_silver/04_silver_dpwh_project_component.ipynb`
2. `02_silver/05_silver_project.ipynb`
3. `04_validation/04_validation_silver_projects.ipynb`

The component notebook preserves every selected Bronze DPWH source row while safely parsing supported project fields.

The project notebook consolidates component-level evidence into one canonical project-level record.

The validator confirms:

- Bronze-to-component row preservation
- component-to-project accounting
- project uniqueness
- budget double-count protection
- source lineage completeness
- retained source-quality findings

Run all notebooks in Databricks.

Local tests verify notebook structure and contracts but do not create Unity Catalog tables.

See [Silver project foundation](../docs/silver_project_cleaning.md) for project-table contracts, consolidation rules, and known limitations.

## Validation connection

`04-validation` is the shared evidence layer for Bronze, Silver, and Gold.
Each layer records checks that match its responsibility.

- Bronze validates source preservation, lineage, snapshot identity, and ingestion safety.
- Silver validates cleaning, typing, deduplication, reconciliation, and geographic matching.
- Gold validates analytical grain, keys, measures, dimensions, and reporting readiness.

This sequence produces Bronze, Silver configuration, and Silver geography and population
results. They live in `04-validation` using separate result tables during this milestone.
Promotion requires the current layer to pass its blocking checks.

## Future layer organization

Do not add Silver or Gold orchestration to `run_all.py`. When those layers are
implemented, use explicit layer runners and one top-level pipeline coordinator:

```text
notebooks/run_bronze.py
notebooks/run_silver.sql
notebooks/run_gold.sql
notebooks/run_pipeline.py
```

Keep validation notebooks separate too:

```text
04_validation/
├── 01_validation_bronze.py
├── 02_validation_silver_config.ipynb
├── 03_validation_silver_geography_population.ipynb
├── 04_validation_silver_projects.ipynb
├── 05_validation_gold.ipynb
└── 06_publish_acceptance_evidence.sql
```

Shared result-writing helpers can move to `src/validation.py` when Python-based
downstream validators need them. Do not create empty runners or modules before their
corresponding implementation exists.

## Central source contract

The six default paths come from one volume root in `src/config.py`:

```text
/Volumes/buildabida-capstone/00-source/cloudflare-r2/
```

Each source notebook accepts four widgets:

- `snapshot_id`: Optional caller-supplied source snapshot ID.
- `source_version`: Optional publisher or release label stored in `load_log`.
- `force_reload`: Replace an identical selected snapshot when set to `true`.
- `source_path`: Optional path override for a controlled test.

When `snapshot_id` is blank, the loader derives a deterministic ID from inexpensive
artifact metadata. It uses the source name, configured version, path, byte size, and
modification time. It never hashes the full source file.

The loader returns `SKIPPED_IDEMPOTENT` only after it verifies the current Delta table.
The requested snapshot, artifact identity, and expected row count must all match.
Reusing an established snapshot ID with changed metadata is an explicit conflict.

Bronze represents the selected current source snapshot. R2 keeps the raw history.
A new snapshot replaces the current Delta table only after Spark can read and write it.
No loader drops tables, schemas, volumes, or raw files.

CSV business fields remain strings. The shared loader adds technical lineage and
records `STARTED`, `SUCCESS`, `FAILED`, or `SKIPPED_IDEMPOTENT`. It also reconciles
source and Bronze row counts.

The loader does not deduplicate, cast, spatially join, categorize, aggregate,
standardize, or fill business values.

## Design summary

Thin notebooks keep source intent visible. One shared loader owns the mechanics.
A seventh CSV source needs one source contract and one documented notebook.
It also needs source-specific validation and focused tests. This structure avoids
copying ingestion logic or introducing an enterprise framework.
