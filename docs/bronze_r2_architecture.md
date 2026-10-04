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
from source name, configured source version, path, byte size and modification time. This is intentionally cheap:
normal runs never hash the full 2 GB flood-susceptibility file.

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

- Spark reads CSV with `header=true`, strings, `inferSchema=false` and `FAILFAST`.
- File identity uses metadata, not full-file checksums.
- Each normal load scans its source once; validation aggregates each Bronze table once.
- The MGB table is not cached, collected to the driver, spatially joined, sorted,
  coalesced to one file, or unnecessarily repartitioned.
- Validation uses `TRY_CAST`; Bronze does not cast business values.
- No streaming or continuous compute is used.

## Rerun and recovery

1. Run `00_setup/00_setup_workspace`; missing schemas are created and the external
   volume is described. A missing volume stops setup.
2. Run the six source notebooks, or `run_all.py`.
3. On `FAILED`, fix the file/header/access issue or choose the correct new snapshot ID.
   A failure before the Delta commit leaves the previous version visible. A failure
   after the commit can leave the new complete version visible without its terminal
   audit row; this is safe to rerun and reconcile.
4. Rerun. The loader skips only when the current table and artifact identity agree;
   otherwise it reloads the requested historical snapshot or reports a conflict.
5. Run validation only after all six return `SUCCESS` or `SKIPPED_IDEMPOTENT`.

## Known limitations

- The current files and Databricks tables were not executed during this local review.
- Actual CSV headers and exact row counts still require a Databricks run.
- To fully reproduce earlier Table C lineage, the CSV needs exact original
  `source_file`, `sheet_name` and `source_row_number` fields, plus a reliable marker
  for the four known copied BARMM sheets.
- To fully reproduce boundary lineage, the CSV needs original `source_file` and
  `source_feature_index` for the seven included geographic files, plus evidence that
  the special-geographic-areas file was excluded.
- The other derived CSVs need documented export commands, source versions and
  reconciliation evidence before they can be called lossless exports.

## Add a future source snapshot

1. Preserve the raw file in R2; do not overwrite an old snapshot if history matters.
2. Record publisher, original format, retrieval/version information and any export or
   trimming steps.
3. Update the configured file name if the path changes.
4. Pass a meaningful new `snapshot_id`, or accept the deterministic metadata ID.
5. Run the source notebook, then the complete Bronze validation.
6. Record observed counts and resolve `FLAG` results in review or Silver, not by
   changing Bronze source rows.
