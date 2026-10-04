# Change manifest

File: `src/config.py`

Current behavior: Configured APIs, a managed landing volume, XLSX paths and five sources.

Revised behavior: Centralizes the existing R2 volume, six CSV paths/tables, run order,
provenance, grain, aliases and historical reference values.

Reason for change: Make source selection consistent, parameterized and six-source aware.

File: `src/bronze.py`

Current behavior: Downloaded/saved raw files, computed full-file SHA-256, overwrote
tables and wrote a success-only legacy log.

Revised behavior: Inspects cheap metadata/header data, derives snapshot IDs, detects
conflicts, skips exact reruns, performs atomic CSV-to-Delta writes, adds technical
metadata and records explicit status events.

Reason for change: Provide low-compute snapshot idempotency, lineage and failure recovery.

File: `notebooks/00_setup/00_setup_workspace.sql`

Current behavior: Created the deleted managed `landing` volume.

Revised behavior: Creates missing schemas safely and fails if the existing
`cloudflare-r2` volume cannot be described.

Reason for change: Setup must validate, not recreate, the external source volume.

File: `notebooks/00_setup/01_check_sources.py`

Current behavior: Sent network requests to publisher/API sites.

Revised behavior: Checks file existence, size, modification time and CSV header for all six R2 files.

Reason for change: The R2 volume is the current source boundary and preflight should be cheap.

File: `notebooks/01_bronze/01_bronze_dpwh_projects.py`

Current behavior: Paged the API, saved JSON and loaded nested API data.

Revised behavior: Calls the shared R2 CSV snapshot loader with notebook parameters.

Reason for change: Use the approved current source location without duplicated mechanics.

File: `notebooks/01_bronze/02_bronze_flood_control.py`

Current behavior: Paged ArcGIS JSON and saved raw replies.

Revised behavior: Loads the configured R2 CSV and explicitly preserves repeated Contract IDs.

Reason for change: Align with R2 while protecting legitimate source grain.

File: `notebooks/01_bronze/03_bronze_psgc.py`

Current behavior: Parsed XLSX and also created `population_2024`, manifests and issue tables.

Revised behavior: Loads only the R2 `psgc.csv` business source table.

Reason for change: Table C is authoritative population and the current source artifact is CSV.

File: `notebooks/01_bronze/04_bronze_census_table_c.py`

Current behavior: The Table C notebook ran sixth and parsed 18 XLSX files.

Revised behavior: Loads the combined/test R2 CSV fourth and does not fabricate workbook lineage.

Reason for change: Match the current source while keeping Table C authoritative and raw-preserving.

File: `notebooks/01_bronze/05_bronze_boundaries.py`

Current behavior: Downloaded seven GeoJSON files, expanded features and hashed files.

Revised behavior: Loads the combined R2 boundary CSV with no spatial mapping.

Reason for change: Use the current artifact and keep geographic transformation downstream.

File: `notebooks/01_bronze/06_bronze_flood_susceptibility.py`

Current behavior: No loader existed.

Revised behavior: Loads the approved trimmed 2 GB MGB CSV with shared low-compute mechanics.

Reason for change: Implement the approved sixth source.

File: `notebooks/01_bronze/06_bronze_census_table_c.py`

Current behavior: Contained the old XLSX Table C parser.

Revised behavior: Removed and replaced by `04_bronze_census_table_c.py`.

Reason for change: Keep the six-source order clear and remove the obsolete landing/XLSX path.

File: `notebooks/04_validation/01_validation_bronze.py`

Current behavior: Required legacy auxiliary/population tables and had no MGB checks.

Revised behavior: Aggregates each authoritative table once, separates STOP and FLAG,
reconciles `load_log`, validates six sources and reports provenance/reference limitations.

Reason for change: Make validation complete, low-compute and safe for current source grain.

File: `notebooks/run_all.py`

Current behavior: Ran five loaders and blocked every skipped result.

Revised behavior: Runs six loaders with shared snapshot/version/force parameters and
accepts only `SUCCESS` or `SKIPPED_IDEMPOTENT` before validation.

Reason for change: Orchestrate the complete batch without passing on stale tables.

File: `tests/test_bronze.py`

Current behavior: No snapshot/header helper tests existed.

Revised behavior: Tests deterministic snapshot identity, duplicate-header rejection,
minimal column mapping and explicit boolean parsing.

Reason for change: Keep core non-Spark behavior explainable and testable.

File: `README.md`

Current behavior: Described five sources and manual uploads to landing.

Revised behavior: Describes six R2 snapshots, current population authority and provenance limits.

Reason for change: Keep the entry point accurate.

File: `notebooks/README.md`

Current behavior: Documented API downloads, Excel parsing, hashes and landing folders.

Revised behavior: Documents exact six-source order, widgets, snapshots, reruns and recovery.

Reason for change: Give junior engineers one practical run guide.

File: `docs/data-model.md`

Current behavior: Included generic population and legacy manifest/parse tables as authoritative.

Revised behavior: Defines six authoritative Bronze grains, technical metadata and audit tables.

Reason for change: Match the revised interface.

File: `docs/validation.md`

Current behavior: Described five-source legacy checks.

Revised behavior: Documents grouped STOP/FLAG checks for all six R2 sources.

Reason for change: Make check meaning and cost clear.

File: `docs/decisions.md`

Current behavior: Left MGB as an open sixth-source decision.

Revised behavior: Adds D-23 approving six R2 source snapshots and marks D-21 resolved.

Reason for change: Preserve decision history while recording the current choice.

File: `docs/bronze_r2_architecture.md`

Current behavior: No consolidated R2 architecture or provenance guide existed.

Revised behavior: Explains source classes, grain, snapshots, idempotency, logging,
low-compute choices, recovery, limitations and future snapshots.

Reason for change: Provide one beginner-friendly source of truth without duplicated prose.

File: `docs/bronze_cleanup_plan.md`

Current behavior: Obsolete objects had no controlled migration plan.

Revised behavior: Lists dependency checks and manual example commands only.

Reason for change: Keep cleanup optional, reviewable and non-destructive.

File: `IMPLEMENTATION_NOTES.md`

Current behavior: Unverified local-versus-Databricks limits were not recorded.

Revised behavior: States exactly what provenance and execution evidence is still missing.

Reason for change: Prevent fabricated confidence or row counts.

File: `docs/README.md`

Current behavior: Did not link the R2 architecture or cleanup guidance.

Revised behavior: Adds both documents to the index.

Reason for change: Make the new operational documentation discoverable.

File: `REVIEW_SUMMARY.md`

Current behavior: No refactor review artifact existed.

Revised behavior: Records findings, design, files, checks, limitations, run order,
rollback and proposed PR text.

Reason for change: Supply the requested manual-review handoff.
