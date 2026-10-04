# Source-to-Bronze notebooks

These Databricks notebooks present the Bronze batch as a documented sequence of
small, reviewable steps. Narrative cells explain why each decision exists; code
cells delegate shared mechanics to `src/bronze.py` and source contracts to
`src/config.py`.

## Bronze principles

- **Raw preserving:** source business values and legitimate duplicate rows remain.
- **Batch-based:** one bounded CSV artifact per source is selected at a time.
- **Idempotent:** a skip is safe only when the current table and artifact identity agree.
- **Parameterized:** widgets select snapshot/version/path behavior without duplicating constants.
- **Snapshot-aware:** rows and `load_log` link Bronze back to the R2 artifact.
- **Low cost:** metadata/header checks precede Spark; strings avoid schema inference;
  large-source validation is grouped.
- **Resilient:** malformed artifacts fail before replacement, Delta writes are atomic,
  conflicts are audited, and failures stay visible.

## Documented sequence

| Step | Notebook | Responsibility |
| --- | --- | --- |
| 1 | `00_setup/00_setup_workspace` | Define missing schemas and verify the existing R2-backed volume without destructive setup. |
| 2 | `00_setup/01_check_sources` | Check all six files, metadata, CSV headers, and required aliases without full Spark scans. |
| 3 | `01_bronze/01_bronze_dpwh_projects` | Preserve DPWH project rows and raw business values. |
| 4 | `01_bronze/02_bronze_flood_control` | Preserve source features and legitimate repeated Contract IDs. |
| 5 | `01_bronze/03_bronze_psgc` | Preserve the geographic reference; keep population as a cross-check only. |
| 6 | `01_bronze/04_bronze_census_table_c` | Preserve authoritative Table C rows, including known BARMM copies. |
| 7 | `01_bronze/05_bronze_boundaries` | Preserve boundary geometry without project mapping or spatial joins. |
| 8 | `01_bronze/06_bronze_flood_susceptibility` | Preserve the approved trimmed MGB extract with low-compute mechanics. |
| 9 | `04_validation/01_validation_bronze` | Record grouped STOP and FLAG checks without changing Bronze. |
| Coordinator | `run_all.py` | Enforce order, require all six safe results, and keep validation behind the complete batch. |

## Central source contract

The six default paths are derived from one volume root in `src/config.py`:

```text
/Volumes/buildabida-capstone/00-source/cloudflare-r2/
```

Each source notebook accepts four widgets:

- `snapshot_id`: optional caller-supplied source snapshot ID;
- `source_version`: optional publisher/release label stored in `load_log`;
- `force_reload`: deliberately replace an identical selected snapshot when `true`;
- `source_path`: optional one-notebook path override for a controlled test.

If `snapshot_id` is blank, the loader derives a deterministic ID from source name,
configured source version, path, byte size and modification time. It never hashes the
full source file. `SKIPPED_IDEMPOTENT` is returned only when the current Delta table
contains the requested snapshot, matching artifact identity, and expected row count.
Reusing an established snapshot ID for changed metadata is an explicit conflict.

Bronze represents the selected/current source snapshot. R2 keeps raw history. A new
snapshot atomically replaces the current Delta table only after Spark can read and
write it. No loader drops tables, schemas, volumes or raw files.

CSV business fields stay strings. The shared loader adds technical lineage, records
`STARTED`, `SUCCESS`, `FAILED`, or `SKIPPED_IDEMPOTENT`, and reconciles source and
Bronze row counts. It does not deduplicate, cast, spatially join, categorize, aggregate,
standardize, or fill business values.

## Design summary

Thin notebooks keep source intent visible while one shared loader owns mechanics. This
structure makes a seventh CSV source straightforward: add one source contract, one thin
documented notebook, source-specific validation, and focused tests—without introducing
an enterprise framework or copying ingestion logic.
