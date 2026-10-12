# Silver validation evidence

This folder holds Databricks evidence for Silver fixes.
Each section names the issue, the commit that ran, the inputs, and the result.
The CSV files are exports of the queries named in each section.

## October 12, 2026 parsed MGB lineage check (issue #109)

### What changed

Notebooks 09 and 10 and validators 07 and 08 now stop when
`silver_mgb_flood_area` was parsed from an older Bronze MGB ingest run.
The expected ingest run is the `_ingest_run_id` of the current
`01-bronze.flood_susceptibility` rows.

The first version of the validator check compared the parsed ingest run with
`load_log.run_id`. That raised a false STOP, explained below.

### Why the check reads Bronze rows, not `load_log`

A `SKIPPED_IDEMPOTENT` Bronze load writes a new `load_log` run ID.
It does not rewrite the Bronze rows, so their `_ingest_run_id` stays the same.

The lineage query in
[`issue-109-mgb-ingest-lineage-2026-10-12.csv`](issue-109-mgb-ingest-lineage-2026-10-12.csv)
shows this on the live data:

| Source | Ingest run | Status | Time (UTC) |
| --- | --- | --- | --- |
| Newest `load_log` event | `eea999ed-fb27-4f9b-86f4-1b2387983ddc` | `SKIPPED_IDEMPOTENT` | 2026-10-11 15:42 |
| `load_log` load that wrote the rows | `07bfbee8-62ba-4b45-976f-10e51c4ab9f3` | `SUCCESS` | 2026-10-10 02:20 |
| Current Bronze MGB rows | `07bfbee8-62ba-4b45-976f-10e51c4ab9f3` | None | 2026-10-10 02:19 |
| `silver_mgb_flood_area` | `07bfbee8-62ba-4b45-976f-10e51c4ab9f3` | None | 2026-10-10 02:19 |

All rows use MGB snapshot `metadata-17bf5e65e1838a2f7be9` with 63,684 rows.

The parsed table matches the current Bronze rows, so it was not stale.
The `eea999ed` event is the October 11 `run_all.py` rerun, where all six
sources returned `SKIPPED_IDEMPOTENT`.
The earlier validator 07 run on this branch stopped only because it compared
`07bfbee8` with `eea999ed`.

### Run identity and outcome

Databricks serverless, branch `fix/issue-109-stale-mgb-gate`, commit `6cf2b2d`,
October 12, 2026. The run used the same code under its earlier hash `0d91766`.
Only the commit message changed.

| Step | Notebook | Result |
| ---: | --- | --- |
| 1 | `08a_silver_mgb_flood_area` | `is_current = true`, `next_action = SKIP_PARSE`. The parsed table already held the current snapshot and ingest run, so it was kept. |
| 2 | `06a_validation_silver_mgb_flood_area` | 23 checks. All 18 STOP checks passed. 3 FLAG findings: 7 blank MGB codes, 297 repaired polygons, and 29 unusable polygons. |
| 3 | `09_silver_region_flood_exposure` | Completed. Every gate passed, including the parsed lineage gate. |
| 4 | `07_validation_silver_region_flood_exposure` | 60 checks. All 38 STOP checks passed. 14 FLAG findings. 0 FAIL. |
| 5 | `10_silver_project_flood_map` | Completed. Every gate passed, including the parsed lineage gate. |
| 6 | `08_validation_silver_project_flood_map` | 55 checks. All 38 STOP checks passed. 13 FLAG findings. 0 FAIL. |

The run IDs and counts are in
[`issue-109-validator-run-summary-2026-10-12.csv`](issue-109-validator-run-summary-2026-10-12.csv):

| Table | Pipeline run ID | Validation run ID |
| --- | --- | --- |
| `silver_mgb_flood_area` | `12765b9cc50d7f107298ab18de2f6bafd8ab10f04bc2a9bee06800c9d984969c` | `c4480b126dc6e45fde488e1beff61362f239d20a1213baf8c53fd21cbd5a5f41` |
| `silver_region_flood_exposure` | `423a78d92beeeea9c36888d8fb27a43466a1f6c7ce16b9eb303b0aa645946afb` | `5d7544dc846b35a75bd1f99cce6b70e6987be7af7e25a2da9a59fcecab66f603` |
| `silver_project_flood_map` | `21eb2668f05700875d260918b2f4691e7b7ba1fdfab6e3fc3bb3a5ba2f82297e` | `78877d563450ad22881eb314a789f13c15dcbbd949f457fbd595d0bac0a3c8e3` |

FLAG findings stay visible for review and do not block the run.
This run did not compare FLAG counts with earlier runs.

### Parsed MGB lineage check

The new STOP check `Parsed MGB lineage matches current accepted Bronze MGB ingest`
passed in both validators. The export is in
[`issue-109-validator-lineage-checks-2026-10-12.csv`](issue-109-validator-lineage-checks-2026-10-12.csv).

| Table | Status | Parsed ingest | Bronze ingest | Run time (UTC) |
| --- | --- | --- | --- | --- |
| `silver_region_flood_exposure` | PASS | `07bfbee8…` | `07bfbee8…` | 2026-10-12 14:29 |
| `silver_project_flood_map` | PASS | `07bfbee8…` | `07bfbee8…` | 2026-10-12 14:37 |

Both rows also show parsed and latest snapshot `metadata-17bf5e65e1838a2f7be9`.

### What this run does not prove

The run had no force reload, so the failing path was not exercised on Databricks.
Tests 44, 45, 46, 67, 68, and 69 check that the gates and validators compare
with the Bronze ingest run and stop on a mismatch.

## October 12, 2026 coordinate fallback for blank regions (issue #111)

### What changed

Table 13 excluded projects from candidate matching with
`reported_region_standardized <> 'CENTRAL OFFICE'`. When the reported region is
`NULL`, that test is `NULL`, so the project was dropped from the coordinate
fallback. A project with no region but a valid point ended `UNMATCHED` instead of
`COORDINATE_BOUNDARY`, which breaks [D-31](../../decisions.md).

Notebook 08 and validator 06 now use
`NOT (reported_region_standardized <=> 'CENTRAL OFFICE')`. Only rows that are
exactly `Central Office` skip the candidate stages.

### Run identity and outcome

Databricks serverless, branch `fix/issue-109-stale-mgb-gate`, commit `5cf7fdd`,
October 12, 2026.

| Step | Notebook | Result |
| ---: | --- | --- |
| 1 | `08_silver_project_region_map` | Completed. Every gate passed. |
| 2 | `06_validation_silver_project_region_map` | 37 checks. All 18 STOP checks passed. 13 FLAG findings. 0 FAIL. |

The run IDs and counts are in
[`issue-111-validator-run-summary-2026-10-12.csv`](issue-111-validator-run-summary-2026-10-12.csv):

| Table | Pipeline run ID | Validation run ID |
| --- | --- | --- |
| `silver_project_region_map` | `1c133bd92a875720ccb7069114625b463e951ff0ca98e47d0a5b096f7f14fc6d` | `0e76a18a7cf429d0a2b50139bb04047e2ab8090b97f0b713a58d0668ca0752c3` |

### Projects affected

The outcome query is in
[`issue-111-region-map-outcomes-2026-10-12.csv`](issue-111-region-map-outcomes-2026-10-12.csv):

| Method | Status | Projects | `NULL` region | `NULL` region with a valid point |
| --- | --- | ---: | ---: | ---: |
| `APPROVED_REGION_ALIAS` | `MATCHED` | 242,443 | 0 | 0 |
| `APPROVED_REGION_ALIAS` | `MATCHED_WITH_CONFLICT` | 11,885 | 0 | 0 |
| `EXACT_REGION_NAME` | `MATCHED` | 10,742 | 0 | 0 |
| `NON_GEOGRAPHIC_RULE` | `NON_GEOGRAPHIC` | 306 | 0 | 0 |
| `NONE` | `UNMATCHED` | 266 | 255 | 0 |
| `EXACT_REGION_NAME` | `MATCHED_WITH_CONFLICT` | 14 | 0 | 0 |
| **Total** | | **265,656** | **255** | **0** |

All 265,656 canonical projects are present. The 255 projects with a `NULL`
reported region are all `UNMATCHED`, and none of them has a valid coordinate
pair. So no project could take the coordinate fallback in this snapshot, and the
fix changes 0 rows today. This matches the issue's audit of the October 11 run.
The fix protects later snapshots that hold a project with no region and a valid
point.

### What this run does not prove

- No project in this snapshot uses the new path, so it ran only in tests.
  Test 23 checks the notebook and test 61 checks the validator. Both fail on the
  old `<>` form.
- Table 13 keeps rule version `silver-project-region-map-v1`. The output is the
  same for this snapshot, so the run ID did not change. This run updated the
  earlier validation evidence in place.
- Validator 06 reads `spatial_candidate_count` from Table 13. It cannot recount
  spatial candidates on its own, so it would not catch a notebook that drops a
  project before the spatial stage. Issue #114 covers checks like this.
