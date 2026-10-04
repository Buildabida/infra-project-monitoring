# Bronze R2 architecture

## Purpose

Cloudflare R2 is the durable source-storage layer. Databricks sees it through the
existing Unity Catalog volume at
`/Volumes/buildabida-capstone/00-source/cloudflare-r2/`. Code stays in GitHub;
Databricks reads the selected file snapshot and writes Delta Bronze tables.

```text
Cloudflare R2 volume → Bronze Delta → Silver → Gold → dashboard / AI-BI
                              ↓
                       Bronze validation
```

Bronze preserves source rows and business values. It does not standardize names,
cast business fields, remove duplicates, map categories, match PSGC places, or run
spatial joins. Those decisions belong in Silver because they change analytical
meaning.

## Design goals

| Goal | Implementation |
| --- | --- |
| Batch-based | One finite CSV artifact is selected per source; there is no streaming state or checkpoint. |
| Idempotent | A skip requires the requested artifact to match the current Delta table and its expected row count. |
| Parameterized | Catalog, schemas, volume root, source files, tables, grains, aliases, and references are centralized. |
| Snapshot-aware | Artifact identity is derived from source name, version, path, size, and modification metadata. |
| Raw preserving | Business columns remain source strings and legitimate duplicate rows remain present. |
| Low cost | Header checks precede Spark, schema inference is disabled, and large-table checks share one aggregate. |
| Resilient | Conflicts fail closed, Delta replacement is atomic, failures are audited, and current state is reconciled. |
| Reusable | A thin source notebook supplies configuration to one shared loader instead of copying mechanics. |

## How one source becomes Bronze

1. `source_config` resolves the approved path, target table, grain, provenance, and
   documented identifying aliases.
2. `inspect_source` checks existence, size, readability, header quality, and a small
   proof of data without parsing the complete artifact.
3. Snapshot identity is accepted from the caller or derived from inexpensive artifact
   metadata; the full file is never hashed for routine identity.
4. Existing audit metadata and the current Delta table are compared. A safe match can
   skip replacement; conflicting reuse of a snapshot ID fails clearly.
5. Spark reads standard CSVs as strings with `FAILFAST` and no inferred business
   schema. The CRLF-delimited MGB extract uses a strict line parser that rejects
   unreadable or wrong-width records instead of fabricating null values.
6. Only technical lineage columns are added. Source values and row multiplicity remain.
7. Delta atomically replaces the selected/current table, source and Bronze row counts
   are reconciled, and `load_log` records the outcome.
8. Grouped validation records STOP and FLAG checks without transforming Bronze.

## Six sources and provenance

The classification describes the current R2 CSV, not the original publisher.

| R2 file | Bronze table and grain | Class | What the repository can prove |
| --- | --- | --- | --- |
| `dpwh_projects.csv` | `dpwh_projects`: one exported project row | D: preprocessed/derived | Earlier code read API JSON. The CSV export procedure and losslessness are not documented. |
| `flood_control_projects.csv` | `flood_control_projects`: one exported feature row | D: preprocessed/derived | Earlier code read ArcGIS JSON. Repeated Contract IDs are legitimate rows and remain. CSV losslessness is unverified. |
| `psgc.csv` | `psgc`: one exported place row | D: preprocessed/derived | Earlier code read the PSA XLSX workbook. The CSV export procedure and losslessness are not documented. |
| `population_2024_table_c_test.csv` | `census_2024_table_c`: one exported Table C row | D: preprocessed/derived | Original delivery used 18 regional workbooks. This combined/test CSV does not have proven original-file lineage. |
| `boundary_bettergov.csv` | `boundaries`: one exported shape row | D: preprocessed/derived | The prior design used seven GeoJSON files and excluded special geographic areas. The combined CSV's exact conversion is unverified. |
| `flood_susceptibility.csv` | `flood_susceptibility`: one flood-area row | C: approved trimmed extract | The project approved only required fields because full geometry is large. This is not described as the complete MGB response. |

No file is labeled an original publisher artifact or lossless export without evidence.
If stronger evidence is added later, update the source card/config and this table.

Table C is the authoritative population source. PSGC population is only a
cross-check. The old generic `population_2024` table is not part of the authoritative
Bronze interface.

## Snapshots and idempotency

The caller may pass `snapshot_id`. When it is blank, the loader derives a stable ID
from source name, configured source version, path, byte size and modification time. This
is intentionally cheap: routine snapshot identity never hashes the full 2 GB
flood-susceptibility file.

- Same snapshot ID and same metadata: return `SKIPPED_IDEMPOTENT` only when
  the current Bronze table also contains that one snapshot, the same artifact
  metadata and the expected row count. A historical success alone never causes
  a skip.
- Same snapshot ID but changed path, size or modification time: fail clearly. A
  changed source needs a new snapshot ID.
- Same completed snapshot with `force_reload=true`: atomically rebuild the current
  Bronze table.
- Different snapshot ID: atomically replace the selected/current Bronze table.

R2 retains raw snapshot history. Bronze holds only the selected/current snapshot to
avoid duplicating multi-GB files without a downstream requirement. If a future model
needs multiple Bronze snapshots, document that dependency before changing this rule.

## Technical metadata and load log

Every source row gets `_source_system`, `_source_path`, `_source_file`,
`_source_format`, `_source_snapshot_id`, `_ingest_run_id`, `_ingested_at`,
`_source_file_size_bytes`, `_source_modified_ns` and `_source_modified_at`.

`01-bronze.load_log` records run/source/table IDs, snapshot and source metadata,
rows loaded, timing, status, a concise error, and any unavoidable CSV-header mapping.
Statuses are `STARTED`, `SUCCESS`, `FAILED` and `SKIPPED_IDEMPOTENT`. Failures are
logged when possible and always re-raised.

Delta overwrite is atomic: readers see either the previous complete table or the
new complete table. The loader never drops the current table first. Delta cannot
atomically commit the Bronze table and `load_log` together. If the table commit
succeeds but the terminal audit append fails, the next rerun verifies the current
table's snapshot, artifact metadata and row count, then records an idempotent skip.

## Low-compute choices

- Standard sources use Spark CSV with `header=true`, strings, `inferSchema=false` and
  `FAILFAST`; the MGB text parser is also fail-closed.
- File identity uses metadata, not full-file checksums.
- Each normal load scans its source once; validation aggregates each Bronze table once.
- The MGB table is not cached, collected to the driver, spatially joined, sorted,
  coalesced to one file, or unnecessarily repartitioned.
- Validation uses `TRY_CAST`; Bronze does not cast business values.
- No streaming or continuous compute is used.

## Failure and recovery contract

- A missing, empty, unreadable, or structurally unexpected source fails before target
  replacement.
- Reusing a snapshot ID for different artifact metadata records a failed conflict and
  leaves the selected table unchanged.
- A failure before Delta commit leaves the previous complete version visible.
- A table commit and `load_log` append cannot share one cross-table transaction. When the
  table commit is complete but the terminal audit append is interrupted, the next attempt
  verifies table snapshot, artifact metadata, and row count before recording an
  idempotent skip.
- Validation accepts only `SUCCESS` or a verified `SKIPPED_IDEMPOTENT`; `STARTED`,
  `FAILED`, missing audit state, row mismatch, or snapshot mismatch blocks downstream use.

## Provenance limits

- To fully reproduce earlier Table C lineage, the CSV needs exact original
  `source_file`, `sheet_name` and `source_row_number` fields, plus a reliable marker
  for the four known copied BARMM sheets.
- To fully reproduce boundary lineage, the CSV needs original `source_file` and
  `source_feature_index` for the seven included geographic files, plus evidence that
  the special-geographic-areas file was excluded.
- The other derived CSVs need documented export commands, source versions and
  reconciliation evidence before they can be called lossless exports.

## Extend the source contract

1. Preserve the raw file in R2; do not overwrite an old snapshot if history matters.
2. Record publisher, original format, retrieval/version information and any export or
   trimming steps.
3. Update the configured file name if the path changes.
4. Use a meaningful new `snapshot_id`, or keep deterministic metadata identity.
5. Add the source-specific header contract and validation rules supported by evidence.
6. Resolve `FLAG` findings in review or Silver, never by changing Bronze source rows.

## Summary

R2 retains source history; Bronze exposes one selected raw snapshot per source with
technical lineage and audit evidence. The design is deliberately small: configuration
describes source differences, one shared loader owns mechanics, thin notebooks explain
intent, and validation reports quality without turning Bronze into a transformation layer.
