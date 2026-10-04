# Data model

Every table lives in the `buildabida-capstone` catalog. Bronze keeps the selected
source snapshot as strings plus technical columns; business types and joins begin
in Silver.

| Table | One row is | Source-grain identity |
| --- | --- | --- |
| `01-bronze.dpwh_projects` | One exported DPWH project row | Documented contract/project key when present |
| `01-bronze.flood_control_projects` | One exported flood-control feature row; repeated Contract IDs remain | Source object ID when present |
| `01-bronze.psgc` | One exported PSGC place row | PSGC code when present |
| `01-bronze.census_2024_table_c` | One exported Table C row, including known BARMM copies | Original file/sheet/row only when the CSV supplies them |
| `01-bronze.boundaries` | One exported geographic shape row | Original file/feature index only when the CSV supplies them |
| `01-bronze.flood_susceptibility` | One flood area in the approved trimmed MGB extract | No row key is assumed without source evidence |
| `01-bronze.load_log` | One ingestion status event | `run_id`, `status` |
| `04-validation.dq_results` | One data-quality check in one validation run | `run_id`, `table_name`, `column`, `data_quality_check` |

There is no authoritative `population_2024` Bronze table. Census Table C is the
population source. A PSGC population column may be used downstream as a cross-check.

Every business-source table adds these technical columns:

| Column | Meaning | Why Bronze keeps it |
| --- | --- | --- |
| `_source_system` | Publisher/system description from source configuration | Identifies the source context without changing business values. |
| `_source_path` | Exact selected Unity Catalog volume path | Connects a table row to its R2-exposed artifact. |
| `_source_file` | Source file name | Supports concise file-level lineage and inspection. |
| `_source_format` | Physical source format (`csv`) | Distinguishes storage representation from business meaning. |
| `_source_snapshot_id` | Caller-supplied or deterministic artifact identity | Makes the selected snapshot explicit and supports idempotency. |
| `_ingest_run_id` | Unique ingestion-attempt identifier | Connects table rows with the corresponding audit events. |
| `_ingested_at` | Timestamp assigned by Spark | Records when the selected table version was written. |
| `_source_file_size_bytes` | Artifact byte size | Supports inexpensive identity and conflict checks. |
| `_source_modified_ns` | High-resolution file modification value | Prevents ambiguous identity when timestamps share display precision. |
| `_source_modified_at` | Readable source modification timestamp | Makes artifact recency understandable to reviewers. |

If a CSV header contains a character Delta cannot store, the loader makes the
smallest technical rename and records the original-to-stored mapping in
`load_log.column_mapping_json`. Business values are not changed.

See [Bronze R2 architecture](bronze_r2_architecture.md) for snapshot behavior and
current provenance limits.

## Raw-preservation rules by source

- **DPWH projects:** contract, budget, payment, progress, status, dates, office/location,
  and coordinates remain source strings.
- **Flood-control projects:** every feature row remains; repeated Contract IDs are not a
  Bronze deduplication key.
- **PSGC:** geographic codes and names remain; population is retained only as source data
  and a downstream cross-check.
- **Census Table C:** known copied BARMM rows remain; missing workbook/sheet/row lineage is
  not fabricated.
- **Boundaries:** geometry stays in its source representation; no project-to-place spatial
  assignment occurs.
- **Flood susceptibility:** the approved trimmed extract remains; no PSGC/place mapping or
  spatial intersection is introduced.

## Layer boundary summary

Bronze may add technical metadata and the minimum column-name substitutions required by
Delta. Cleaning, type conversion, standardization, matching, deduplication decisions,
spatial work, category mapping, measures, and aggregation belong in Silver or Gold.
