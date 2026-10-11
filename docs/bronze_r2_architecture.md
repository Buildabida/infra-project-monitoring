# Bronze R2 architecture

## Purpose

Cloudflare R2 is the durable source-storage layer.
Databricks accesses it through this existing Unity Catalog volume:
`/Volumes/buildabida-capstone/00-source/cloudflare-r2/`.

Code stays in GitHub.
Databricks reads the selected file snapshot and writes Delta Bronze tables.

```text
Cloudflare R2 volume → Bronze Delta → Silver → Gold → dashboard / AI-BI
                              ↓
                       Bronze validation
```

Bronze preserves source rows and business values.
It does not standardize names, cast fields, remove duplicates, map categories, match PSGC places, or run spatial joins.
Those decisions belong in Silver because they change analytical meaning.

## Design goals

| Goal | Implementation |
| --- | --- |
| Batch-based | One finite CSV artifact is selected per source. There is no streaming state or checkpoint. |
| Idempotent | A skip requires the requested artifact to match the current Delta table. Its row count must also match. |
| Parameterized | Catalog, schemas, volume root, source files, tables, grains, aliases, and references are centralized. |
| Snapshot-aware | Source name, version, path, size, and modification metadata define the artifact identity. |
| Raw preserving | Business columns remain source strings. Legitimate duplicate rows remain present. |
| Low cost | Header checks precede Spark. Schema inference is disabled. Large-table checks share one aggregate. |
| Resilient | Conflicts fail closed. Delta replacement is atomic. Failures are audited, and current state is reconciled. |
| Reusable | A thin source notebook supplies configuration to one shared loader. It does not copy ingestion mechanics. |

## How one source becomes Bronze

1. `source_config` resolves the approved path, table, grain, provenance, and required aliases.
   These aliases cover identifiers and downstream-critical fields.
2. `inspect_source` checks existence, size, readability, header quality, and a small data proof.
   It does not parse the complete artifact.
3. The caller supplies snapshot identity, or the loader derives it from inexpensive artifact metadata.
   Routine identity never hashes the full file.
4. The loader compares existing audit metadata with the current Delta table.
   A safe match can skip replacement.
   Conflicting reuse of a snapshot ID fails clearly.
5. The loader verifies every required source field group before replacement.
   For example, the MGB extract requires a susceptibility field and geometry.
6. Spark reads standard CSVs as strings with `FAILFAST` and no inferred business schema.
   A strict line parser handles the CRLF-delimited MGB extract.
   It rejects unreadable or wrong-width records instead of creating null values.
   It reads fields up to 256 MiB, because 1,815 MGB geometry fields exceed the Python default of 131,072 characters.
   The largest field is 34,352,521 characters.
7. The loader adds only technical lineage columns.
   Source values and row multiplicity remain unchanged.
8. Delta atomically replaces the selected table.
   The loader reconciles source and Bronze row counts, then records the outcome in `load_log`.
9. Grouped validation records STOP and FLAG checks without transforming Bronze.

## Six sources and provenance

The classification describes each current R2 CSV, not the original publisher artifact.

| R2 file | Bronze table and grain | Class | What the repository can prove |
| --- | --- | --- | --- |
| `dpwh_projects.csv` | `dpwh_projects`: one exported project row | D: preprocessed/derived | Earlier code read API JSON. The CSV export procedure and losslessness are not documented. |
| `flood_control_projects.csv` | `flood_control_projects`: one exported feature row | D: preprocessed/derived | Earlier code read ArcGIS JSON. Repeated Contract IDs are legitimate and remain. CSV losslessness is unverified. |
| `psgc.csv` | `psgc`: one exported place row | D: preprocessed/derived | Earlier code read the PSA XLSX workbook. The CSV export procedure and losslessness are not documented. |
| `population_2024_table_c_test.csv` | `census_2024_table_c`: one exported Table C row | D: preprocessed/derived | Original delivery used 18 regional workbooks. The combined test CSV lacks proven original-file lineage. |
| `boundary_bettergov.csv` | `boundaries`: one exported shape row | D: preprocessed/derived | The prior design used seven GeoJSON files and excluded special areas. The combined CSV conversion is unverified. |
| `flood_susceptibility.csv` | `flood_susceptibility`: one flood-area row | C: approved trimmed extract | The project approved only required fields because full geometry is large. This is not the complete MGB response. |

No file is called an original publisher artifact or lossless export without evidence.
Update the configuration and this table when stronger evidence becomes available.

Table C is the authoritative population source.
PSGC population is only a cross-check.
The old generic `population_2024` table is not part of the authoritative Bronze interface.

## Snapshots and idempotency

The caller may pass `snapshot_id`.
When blank, the loader derives a stable ID from source name, configured version, path, byte size, and modification time.
This approach is intentionally inexpensive.
Routine snapshot identity never hashes the full 2 GB flood-susceptibility file.

- Same snapshot ID and metadata: return `SKIPPED_IDEMPOTENT` only after verifying the current Bronze table.
  The table must contain that snapshot, matching artifact metadata, and the expected row count.
  A historical success alone never causes a skip.
- Same snapshot ID with a changed path, size, or modification time: fail clearly.
  A changed source needs a new snapshot ID.
- Same completed snapshot with `force_reload=true`: atomically rebuild the current Bronze table.
- Different snapshot ID: atomically replace the selected Bronze table.

R2 retains raw snapshot history.
Bronze holds only the selected snapshot to avoid duplicating multi-GB files without a downstream requirement.
Document the dependency before supporting multiple Bronze snapshots for a future model.

## Technical metadata and load log

Every source row receives these technical fields:

- `_source_system`
- `_source_path`
- `_source_file`
- `_source_format`
- `_source_snapshot_id`
- `_ingest_run_id`
- `_ingested_at`
- `_source_file_size_bytes`
- `_source_modified_ns`
- `_source_modified_at`

`01-bronze.load_log` records run, source, table, snapshot, and source metadata.
It also records row counts, timing, status, concise errors, and unavoidable CSV-header mappings.
Statuses are `STARTED`, `SUCCESS`, `FAILED`, and `SKIPPED_IDEMPOTENT`.
Failures are logged when possible and always re-raised.

Delta overwrite is atomic.
Readers see either the previous complete table or the new complete table.
The loader never drops the current table first.

Delta cannot atomically commit the Bronze table and `load_log` together.
If the table commit succeeds but audit logging fails, the next rerun verifies the current table.
It checks snapshot identity, artifact metadata, and row count before recording an idempotent skip.

## Low-compute choices

- Standard sources use Spark CSV with `header=true`, strings, `inferSchema=false`, and `FAILFAST`.
  The MGB text parser is also fail-closed.
- Header validation checks every configured business-critical field family.
  It does not read or transform business rows.
- File identity uses metadata instead of full-file checksums.
- Each normal load scans its source once.
  Validation aggregates each Bronze table once.
- The MGB table is not cached, collected, spatially joined, sorted, or coalesced to one file.
  It is not repartitioned without a clear requirement.
- Validation uses `TRY_CAST`.
  Bronze does not cast business values.
- No streaming or continuous compute is used.

## Failure and recovery contract

- A missing, empty, unreadable, or structurally unexpected source fails before target replacement.
- Reusing a snapshot ID for different artifact metadata records a failed conflict.
  The selected table remains unchanged.
- A failure before Delta commit leaves the previous complete version visible.
- A table commit and `load_log` append cannot share one cross-table transaction.
  A later attempt reconciles an interrupted terminal audit append.
  It verifies snapshot identity, artifact metadata, and row count before recording an idempotent skip.
- Validation accepts only `SUCCESS` or a verified `SKIPPED_IDEMPOTENT`.
  Other audit states, missing state, row mismatches, and snapshot mismatches block downstream use.

## Provenance limits

- Complete Table C lineage requires exact `source_file`, `sheet_name`, and `source_row_number` fields.
  It also requires a reliable marker for the four copied BARMM sheets.
- Complete boundary lineage requires the original `source_file` and `source_feature_index`.
  Evidence must also confirm that the special-geographic-areas file was excluded.
- Other derived CSVs need documented export commands, source versions, and reconciliation evidence.
  Without that evidence, they cannot be called lossless exports.

## Extend the source contract

1. Preserve the raw file in R2.
   Do not overwrite an old snapshot when history matters.
2. Record publisher, original format, retrieval information, and source version.
   Document every export or trimming step.
3. Update the configured file name when the path changes.
4. Use a meaningful new `snapshot_id`, or keep deterministic metadata identity.
5. Add required alias groups for every field family needed downstream.
   Add source-specific validation only when supporting evidence exists.
6. Resolve `FLAG` findings during review or in Silver.
   Never resolve them by changing Bronze source rows.

## Summary

R2 retains source history.
Bronze exposes one selected raw snapshot per source with technical lineage and audit evidence.
Configuration describes source differences, while one shared loader owns ingestion mechanics.
Thin notebooks explain intent.
Validation reports quality without turning Bronze into a transformation layer.
