# Notebooks

Run `run_all.py` to execute the R2 Bronze batch in this order:

1. `00_setup/00_setup_workspace` creates missing schemas and verifies the existing
   `00-source`.`cloudflare-r2` volume. It never creates a replacement landing volume.
2. `01_bronze/01_bronze_dpwh_projects`
3. `01_bronze/02_bronze_flood_control`
4. `01_bronze/03_bronze_psgc`
5. `01_bronze/04_bronze_census_table_c`
6. `01_bronze/05_bronze_boundaries`
7. `01_bronze/06_bronze_flood_susceptibility`
8. `04_validation/01_validation_bronze`

## Load Bronze

The six default paths are centralized in `src/config.py` under:

```text
/Volumes/buildabida-capstone/00-source/cloudflare-r2/
```

Each source notebook accepts three widgets:

- `snapshot_id`: optional caller-supplied source snapshot ID;
- `source_version`: optional publisher/release label stored in `load_log`;
- `force_reload`: reload an identical completed snapshot when `true`;
- `source_path`: optional one-notebook path override for a controlled test.

If `snapshot_id` is blank, the loader derives a deterministic ID from source name,
configured source version, path, byte size and modification time. It does not hash the full file. An exact
successful rerun returns `SKIPPED_IDEMPOTENT`. Reusing a snapshot ID after its path,
size or modification time changes fails and requires a new ID.

Bronze represents the selected/current source snapshot. R2 keeps raw history. A new
snapshot atomically replaces the current Delta table only after Spark can read and
write it. No loader drops tables, schemas, volumes or raw files.

CSV fields stay strings. The shared loader adds ingestion metadata, logs `STARTED`,
`SUCCESS`, `FAILED` or `SKIPPED_IDEMPOTENT`, and checks source-to-Bronze row
preservation. It does not deduplicate, cast, spatially join, categorize or clean.

Run a notebook from VS Code with **Run on Databricks → Run File as Workflow**.
Databricks execution is required to verify real headers, row counts and Delta writes.
