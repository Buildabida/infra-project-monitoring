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

- `_source_system`
- `_source_file`
- `_source_format`
- `_source_snapshot_id`
- `_ingest_run_id`
- `_ingested_at`
- `_source_file_size_bytes`
- `_source_modified_at`

If a CSV header contains a character Delta cannot store, the loader makes the
smallest technical rename and records the original-to-stored mapping in
`load_log.column_mapping_json`. Business values are not changed.

See [Bronze R2 architecture](bronze_r2_architecture.md) for snapshot behavior and
current provenance limits.
