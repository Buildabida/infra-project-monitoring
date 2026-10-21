# Silver validation evidence

This folder holds Databricks evidence for Silver fixes.
Each section names the issue, the commit that ran, the inputs, and the result.
The CSV files are exports of the queries named in each section.

## October 12, 2026 parsed MGB lineage check (issue #109)

### What changed (#109)

Notebooks 09 and 10 and validators 07 and 08 now stop when
`silver_mgb_flood_area` was parsed from an older Bronze MGB ingest run.
The expected ingest run is the `_ingest_run_id` of the current
`01-bronze.flood_susceptibility` rows.

The first version of the validator check compared the parsed ingest run with
`load_log.run_id`. That raised a false STOP, explained below.

### Why the check reads Bronze rows, not `load_log` (#109)

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

### Run identity and outcome (#109)

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

### Parsed MGB lineage check (#109)

The new STOP check `Parsed MGB lineage matches current accepted Bronze MGB ingest`
passed in both validators. The export is in
[`issue-109-validator-lineage-checks-2026-10-12.csv`](issue-109-validator-lineage-checks-2026-10-12.csv).

| Table | Status | Parsed ingest | Bronze ingest | Run time (UTC) |
| --- | --- | --- | --- | --- |
| `silver_region_flood_exposure` | PASS | `07bfbee8…` | `07bfbee8…` | 2026-10-12 14:29 |
| `silver_project_flood_map` | PASS | `07bfbee8…` | `07bfbee8…` | 2026-10-12 14:37 |

Both rows also show parsed and latest snapshot `metadata-17bf5e65e1838a2f7be9`.

### What this run does not prove (#109)

The run had no force reload, so the failing path was not exercised on Databricks.
Tests 44, 45, 46, 67, 68, and 69 check that the gates and validators compare
with the Bronze ingest run and stop on a mismatch.

## October 12, 2026 coordinate fallback for blank regions (issue #111)

### What changed (#111)

Table 13 excluded projects from candidate matching with
`reported_region_standardized <> 'CENTRAL OFFICE'`. When the reported region is
`NULL`, that test is `NULL`, so the project was dropped from the coordinate
fallback. A project with no region but a valid point ended `UNMATCHED` instead of
`COORDINATE_BOUNDARY`, which breaks [D-31](../../decisions.md).

Notebook 08 and validator 06 now use
`NOT (reported_region_standardized <=> 'CENTRAL OFFICE')`. Only rows that are
exactly `Central Office` skip the candidate stages.

### Run identity and outcome (#111)

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

### Projects affected (#111)

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

### What this run does not prove (#111)

- No project in this snapshot uses the new path, so it ran only in tests.
  Test 23 checks the notebook and test 61 checks the validator. Both fail on the
  old `<>` form.
- Table 13 keeps rule version `silver-project-region-map-v1`. The output is the
  same for this snapshot, so the run ID did not change. This run updated the
  earlier validation evidence in place.
- Validator 06 reads `spatial_candidate_count` from Table 13. It cannot recount
  spatial candidates on its own, so it would not catch a notebook that drops a
  project before the spatial stage. Issue #114 covers checks like this.

## October 13, 2026 coordinate pairs and status resolution (issue #110)

### What changed (#110)

`silver_project` resolved `latitude_parsed` and `longitude_parsed` on their
own. Components (14.5, `NULL`) and (`NULL`, 121.0) could publish (14.5, 121.0),
a point that no row reported. Status values also resolved on their own, so a
`CONFLICT` raw status could still publish a standardized status, and
`status_mapping_state` could be `NULL`.

Notebook 05 now resolves the coordinates as one pair from `VALID_PAIR` rows,
and publishes status values only for a resolved raw status with one complete
approved mapping. Validator 04 recounts both from the components and stops on
any difference. The rule version is `silver_project_v7` and the validation
version is `silver_project_validation_v6`. The number is v7 because `main`
already ran v6 for #119.

### Run identity and outcome (#110)

Databricks serverless, branch `fix/issue-109-stale-mgb-gate`, commit `c0097a8`.
The run started on October 12, 2026 at 16:15 UTC, which is October 13 in
Manila.

| Step | Notebook | Result |
| ---: | --- | --- |
| 1 | `05_silver_project` | Completed. Rule version `silver_project_v7`. |
| 2 | `04_validation_silver_projects` | 43 checks. All 27 STOP checks passed. 13 FLAG findings. 0 FAIL. |
| 3 | `07_silver_project_source_match` | Completed. |
| 4 | `05_validation_silver_source_reconciliation` | 23 checks. All 13 STOP checks passed. 6 FLAG findings. 0 FAIL. |
| 5 | `08_silver_project_region_map` | Completed. |
| 6 | `06_validation_silver_project_region_map` | 37 checks. All 18 STOP checks passed. 13 FLAG findings. 0 FAIL. |
| 7 | `10_silver_project_flood_map` | Completed. |
| 8 | `08_validation_silver_project_flood_map` | 55 checks. All 38 STOP checks passed. 13 FLAG findings. 0 FAIL. |

The run IDs and counts are in
[`issue-110-validator-run-summary-2026-10-13.csv`](issue-110-validator-run-summary-2026-10-13.csv).
The new project pipeline run is
`c6317d2b45b2b3f9832e9dfccf130317fea4d1b06a18922d837d22d449b6a424`.

### Projects affected (#110)

The impact query compares the old and new rules on the component rows.
It is in [`issue-110-impact-2026-10-13.csv`](issue-110-impact-2026-10-13.csv).

| Finding | Projects |
| --- | ---: |
| Old rule published a pair that the new rule does not | 0 |
| Old and new rules publish different pairs | 0 |
| Old rule published half a pair | 0 |
| New rule publishes a pair that the old rule did not | 0 |
| Components report more than one valid pair | 0 |
| Old rule published a status for an unresolved raw status | 0 |
| Old rule left `status_mapping_state` `NULL` | 0 |

The fix changes 0 projects in this snapshot. It protects later snapshots.

The published table agrees, in
[`issue-110-project-state-2026-10-13.csv`](issue-110-project-state-2026-10-13.csv):

| Measure | Projects |
| --- | ---: |
| All projects | 265,656 |
| `coordinate_resolution_status = RESOLVED` | 215,138 |
| `coordinate_resolution_status = MISSING_OR_INVALID` | 50,518 |
| `coordinate_resolution_status = CONFLICT` | 0 |
| Half pairs | 0 |
| `status_mapping_state = MAPPED` | 265,554 |
| `status_mapping_state = UNMAPPED` | 102 |
| `status_mapping_state` is `NULL` | 0 |
| Standardized status on an unresolved raw status | 0 |

The 215,138 resolved pairs equal the 215,138 projects with a `VALID_PAIR`
coordinate in Table 15.

### New checks (#110)

The three new checks are in
[`issue-110-new-checks-2026-10-13.csv`](issue-110-new-checks-2026-10-13.csv):

| Check | Action | Status | Failed rows |
| --- | --- | --- | ---: |
| Project coordinates publish as one pair from one component pair | STOP | PASS | 0 |
| Standardized status publishes only for a resolved and mapped raw status | STOP | PASS | 0 |
| Conflicting coordinate pairs remain visible | FLAG | PASS | 0 |

Both component recounts found 0 differences.

### Downstream tables (#110)

Table 13 outcomes match the #111 run row for row, in
[`issue-110-region-map-outcomes-2026-10-13.csv`](issue-110-region-map-outcomes-2026-10-13.csv).
No project changed region.

### What this run does not prove (#110)

- No project in this snapshot uses the new paths, so they ran only in tests.
  Tests 34, 35, and 36 fail on the old notebooks.
- Gold `03`, `04`, and `07` and the Gold validator did not rerun on the v7
  project run. They still describe the v6 run.

## October 13, 2026 Silver audit fixes (issues #112 to #115)

This run covers the population part of
[PR #128](https://github.com/Buildabida/infra-project-monitoring/pull/128) and
validators 02, 03, 05, and 06. The MGB flood part ran on October 13. See
"MGB flood run (#114 and #115)" below.

### What changed (#112 to #115)

- #112: the population reconciliation `run_id` now hashes the selected PSGC
  snapshot, not each row's PSGC lineage. Unmatched rows had a `NULL` PSGC
  snapshot, so one run published two run IDs. The rule version is
  `silver-population-place-v3`.
- #113: only the last heading row sets the locality context. An ambiguous or
  unresolved heading clears it, so its barangays never inherit the previous
  locality.
- #114: checks that could not fail can now fail. This run covers validators 02,
  03, 05, and 06. The SRID, polygon count, and territory checks in notebooks 09
  and 10 and validators 07 and 08 ran in the MGB flood run below.
- #115: the blank-geometry reference is 0 and the repair label is `buffer0`.
  Both ran in the MGB flood run below.

### Run identity and outcome (#112 to #115)

Databricks serverless, branch `fix/issue-112-115-silver-audit`, commit
`da59e3c`. The runs took place on October 12, 2026 from 18:03 to 18:21 UTC,
which is October 13 in Manila.

| Step | Notebook | Result |
| ---: | --- | --- |
| 1 | `02_validation_silver_config` | 23 checks. All 19 STOP checks passed. 4 FLAG findings. 0 FAIL. |
| 2 | `02_silver_population_place_reconciliation` | Completed. Rule version `silver-population-place-v3`. |
| 3 | `03_silver_region_population` | Completed. Every gate passed, including the new one-run-ID gate. |
| 4 | `03_validation_silver_geography_population` | 34 checks on three tables. All 22 STOP checks passed. 8 FLAG findings. 0 FAIL. |
| 5 | `05_validation_silver_source_reconciliation` | 24 checks on two tables. All 14 STOP checks passed. 6 FLAG findings. 0 FAIL. |
| 6 | `06_validation_silver_project_region_map` | 40 checks. All 21 STOP checks passed. 13 FLAG findings. 0 FAIL. |

The latest result for each table in `silver_dq_results`, read after step 6:

| Table | Run time (UTC) | Checks | STOP checks | STOP passed | FLAG | FAIL | From this run |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `silver_psgc_place` | 2026-10-12 18:13:55 | 8 | 5 | 5 | 3 | 0 | Yes |
| `silver_population_place_reconciliation` | 2026-10-12 18:13:55 | 18 | 10 | 10 | 5 | 0 | Yes |
| `silver_region_population` | 2026-10-12 18:13:55 | 8 | 7 | 7 | 0 | 0 | Yes |
| `silver_flood_control_component` | 2026-10-12 18:19:17 | 11 | 5 | 5 | 4 | 0 | Yes |
| `silver_project_source_match` | 2026-10-12 18:19:17 | 13 | 9 | 9 | 2 | 0 | Yes |
| `silver_project_region_map` | 2026-10-12 18:21:17 | 40 | 21 | 21 | 13 | 0 | Yes |
| `silver_mgb_flood_area` | 2026-10-12 14:08:33 | 23 | 18 | 18 | 3 | 0 | No |
| `silver_region_flood_exposure` | 2026-10-12 14:29:30 | 60 | 38 | 38 | 14 | 0 | No |
| `silver_project` | 2026-10-12 16:15:31 | 20 | 16 | 16 | 3 | 0 | No |
| `silver_dpwh_project_component` | 2026-10-12 16:15:31 | 23 | 11 | 11 | 10 | 0 | No |
| `silver_project_flood_map` | 2026-10-12 16:38:38 | 55 | 38 | 38 | 13 | 0 | No |

The run IDs of the six tables from this run:

| Table | Pipeline run ID | Validation run ID |
| --- | --- | --- |
| `silver_psgc_place` | `0b65c728d2436e0efe02825f2358c0eac765d5e76dc938518f519962a1f2aaa8` | `3fcf0491ef25e51a87e062e66c439c99589cfbfafc1d2a0388220fa719be830b` |
| `silver_population_place_reconciliation` | `611988e7136e0eb42838ff69af3a4dec45737e34c4d10416263837ceeaea8a16` | `55c790e673f06ae4a5e167f5ea5cecc85c39149b84e1d265e9ed593734507f15` |
| `silver_region_population` | `ec967198af156cb6ba8d8ad5e60a90648a1b60b036dbc34667a796a91e351668` | `cad8f9bede2582f9c8eae14875d87abccbafe094838b732771baf7086ab7bfb0` |
| `silver_flood_control_component` | `b60b91752c0fde0f8f9e948c62724895d4ac30c38b11889e29a172d65bdbbefb` | `60b4e121cad0f1008728e854f0c4a390c3d0908a3ae61d21ccde8ea10fd9e6a2` |
| `silver_project_source_match` | `b60b91752c0fde0f8f9e948c62724895d4ac30c38b11889e29a172d65bdbbefb` | `60b4e121cad0f1008728e854f0c4a390c3d0908a3ae61d21ccde8ea10fd9e6a2` |
| `silver_project_region_map` | `54441fa48025a4a2c1fbf86b6bd69b93a116a490b832ff68e43abe6ec0290c0c` | `544a9e22ea74b07de8b7f767d70d786ff7019099b49dbea5052d8331fc5d210b` |

### Checks before the run (#112 to #115)

Validator 02's new STOP compares each DPWH region alias with the Bronze PSGC
release. A read-only query ran first, so the STOP would not block Silver by
surprise. All 17 approved aliases matched:

| Alias | PSGC code | Alias version | Bronze release | Match |
| --- | --- | --- | --- | --- |
| Cordillera Administrative Region | `1400000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| National Capital Region | `1300000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Negros Island Region | `1800000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region I | `0100000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region II | `0200000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region III | `0300000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region IV-A | `0400000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region IV-B | `1700000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region IX | `0900000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region V | `0500000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region VI | `0600000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region VII | `0700000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region VIII | `0800000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region X | `1000000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region XI | `1100000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region XII | `1200000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |
| Region XIII | `1600000000` | 2Q 2026 as of 2026-06-30 | 2Q 2026 as of 2026-06-30 | Yes |

`silver_population_place_reconciliation` was at Delta version 4, written on
October 9 with 43,750 rows. The #113 comparison below reads that version.

The Table 14 and Table 15 outcomes were saved before the run. The MGB run
compares with them. Blank cells were `NULL`.

`silver_region_flood_exposure` before the run (Table 14):

| Level | Spatial match status | Region rows | Susceptible area (sq km) | Source polygons | Fragments |
| --- | --- | ---: | ---: | ---: | ---: |
| High | `CALCULATED` | 13 | 16,615.1039 | 11,341 | 11,341 |
| High | `NO_SAFE_REGION_BOUNDARY` | 5 | | | |
| Low | `CALCULATED` | 13 | 11,448.7952 | 14,915 | 14,915 |
| Low | `NO_SAFE_REGION_BOUNDARY` | 5 | | | |
| Moderate | `CALCULATED` | 13 | 11,626.4386 | 21,620 | 21,620 |
| Moderate | `NO_SAFE_REGION_BOUNDARY` | 5 | | | |
| Very High | `CALCULATED` | 12 | 4,528.3842 | 3,089 | 3,089 |
| Very High | `NO_MAPPED_EXPOSURE` | 1 | 0.0000 | 0 | 0 |
| Very High | `NO_SAFE_REGION_BOUNDARY` | 5 | | | |

`silver_project_flood_map` before the run (Table 15):

| Match status | Level | Projects | Matched polygons |
| --- | --- | ---: | ---: |
| `AMBIGUOUS` | | 250 | 502 |
| `MATCHED` | High | 35,672 | 35,781 |
| `MATCHED` | Low | 35,146 | 35,227 |
| `MATCHED` | Moderate | 27,467 | 27,526 |
| `MATCHED` | Very High | 14,425 | 14,462 |
| `UNMATCHED` | | 152,696 | 0 |

### Population run ID (#112)

| Measure | Before | After |
| --- | ---: | ---: |
| Distinct reconciliation `run_id` values | 2 | 1 |

After the run, every row carries rule version `silver-population-place-v3`.

`silver_region_population` was rebuilt from the new run:

| Reconciliation run IDs | Region rows | Region run IDs | Linked reconciliation run IDs | Uses the new run | Regional population |
| ---: | ---: | ---: | ---: | --- | ---: |
| 1 | 18 | 1 | 1 | Yes | 112,722,987 |

### Heading context (#113)

Every reconciliation row was compared with Delta version 4:

| Rows compared | Match changed | Locality changed | Disposition changed |
| ---: | ---: | ---: | ---: |
| 43,750 | 0 | 0 | 0 |

The impact query, which lists each old and new match status pair, returned no
rows because no match changed.

Row dispositions before the run, from Delta version 4:

| Disposition | Match status | Source rows | Population |
| --- | --- | ---: | ---: |
| `ACCEPTED_PRIMARY` | `MATCHED_ALIAS` | 15 | 46,612 |
| `ACCEPTED_PRIMARY` | `MATCHED_EXACT_CONTEXT` | 41,902 | 111,627,666 |
| `ACCEPTED_PRIMARY` | `MATCHED_NORMALIZED_CONTEXT` | 80 | 1,048,709 |
| `INVALID_POPULATION` | `MATCHED_EXACT_CONTEXT` | 11 | 0 |
| `INVALID_POPULATION` | `MATCHED_NORMALIZED_CONTEXT` | 1 | 0 |
| `MATCHED_NON_PRIMARY_LEVEL` | `MATCHED_ALIAS` | 2 | 37,766 |
| `MATCHED_NON_PRIMARY_LEVEL` | `MATCHED_EXACT_CONTEXT` | 1,730 | 196,723,997 |
| `MATCHED_NON_PRIMARY_LEVEL` | `MATCHED_NORMALIZED_CONTEXT` | 1 | 26,292 |
| `UNMATCHED` | `UNMATCHED` | 8 | 6,437,703 |

The three `ACCEPTED_PRIMARY` rows add up to 41,997 rows and 112,722,987
people. The regional total after the run is the same. It is 4,789 below the
national reference of 112,727,776. That gap equals the two known unmatched
barangays, Sawata (4,152) and San Rafael (637). So no other population was
missed or counted twice.

A query for PSGC barangays accepted more than once returned 0 rows before the
run. After the run, the new STOP check found 0 as well.

The fix changes 0 rows in this snapshot. It protects later snapshots with an
ambiguous or unresolved heading.

### New checks (#114)

The new and changed checks from this run:

| Validator | Table | Check | Action | Status | Failed rows | Total rows | Details |
| ---: | --- | --- | --- | --- | ---: | ---: | --- |
| 02 | `config_place_name_alias` | approved DPWH region aliases name the Bronze PSGC version | STOP | PASS | 0 | 17 | Each approved DPWH region alias must carry the PSGC release that Bronze holds for its target code |
| 03 | `silver_population_place_reconciliation` | One reconciliation run ID reproduces from its lineage | STOP | PASS | 0 | 43,750 | Distinct run IDs=1, rows whose run ID does not reproduce=0 |
| 03 | `silver_population_place_reconciliation` | Each PSGC barangay is accepted at most once | STOP | PASS | 0 | 41,997 | Accepted rows beyond distinct PSGC barangays=0 |
| 03 | `silver_population_place_reconciliation` | Every active approved alias produced an accepted match | FLAG | PASS | 0 | 19 | Active approved aliases with no accepted match=0 of 19 |
| 05 | `silver_project_source_match` | Match targets the current silver_project run | STOP | PASS | 0 | 9,704 | Match rows with an older target_project_run_id=0 |
| 06 | `silver_project_region_map` | Coordinate statuses use the controlled contract | STOP | PASS | 0 | 265,656 | Invalid coordinate statuses=0 |
| 06 | `silver_project_region_map` | Mapping uses the current silver_project run | STOP | PASS | 0 | 265,656 | Rows with an older project_run_id=0 |
| 06 | `silver_project_region_map` | Mapping uses the current PSGC run | STOP | PASS | 0 | 265,656 | Rows with an older psgc_run_id=0 |
| 06 | `silver_project_region_map` | Partial and outside-screening coordinates remain visible | FLAG | PASS | 0 | 265,656 | Coordinate exceptions=0, denominator=265656 |

The validator 06 coordinate FLAG now counts `OUT_OF_RANGE`. It found 0 because
the 215,138 usable pairs and the 50,518 missing pairs make up all 265,656
projects.

### MGB flood run (#114 and #115)

Databricks serverless, branch `fix/issue-109-stale-mgb-gate`, commit `eb318fa`.
Steps 7 to 10 ran on October 12, 2026 from 18:53 to 19:21 UTC. Steps 11 and 12
ran on October 13 at 05:25 and 05:33 UTC. The free daily compute limit stopped
step 11 overnight.

| Step | Notebook | Result |
| ---: | --- | --- |
| 7 | `08a_silver_mgb_flood_area` | `next_action = PARSE_AND_PUBLISH`. The `buffer0` label changed the parse run ID, so the full parse ran. |
| 8 | `06a_validation_silver_mgb_flood_area` | 23 checks. All 18 STOP checks passed. 3 FLAG findings. 0 FAIL. |
| 9 | `09_silver_region_flood_exposure` | Completed. Every gate passed. |
| 10 | `07_validation_silver_region_flood_exposure` | 60 checks. All 38 STOP checks passed. 13 FLAG findings. 0 FAIL. |
| 11 | `10_silver_project_flood_map` | Completed. Every gate passed. |
| 12 | `08_validation_silver_project_flood_map` | 55 checks. All 38 STOP checks passed. 12 FLAG findings. 0 FAIL. |

An earlier attempt at steps 11 and 12, at 04:55 UTC, ran from `main` by mistake
because the shared Git folder had been switched to `main`. Its validator wrote
54 checks without the #109 and #115 changes. The rerun above, from this branch,
replaced it. The Table 15 values did not change between the two runs.

#### Parsed MGB table (#115)

From [`issue-115-mgb-parse-version-2026-10-13.csv`](issue-115-mgb-parse-version-2026-10-13.csv):

| Parse rule version | MGB rows | Usable rows | Blank rows | Rows without SRID 4326 |
| --- | ---: | ---: | ---: | ---: |
| `silver-mgb-flood-area-parse-v2\|esri-rings-as-text\|holes-when-first-reading-invalid\|buffer0-invalid-within-ratio=0.01-or-sqm=10000.0` | 63,684 | 63,655 | 0 | 15 |

The new parse run ID is
`6667374783ea5197a1976589e8ee9da11e679a92657b9efaa28900f944597619`. The 15 rows
without SRID 4326 are the 15 `UNPARSEABLE_GEOMETRY` rows. They have no geometry,
so they have no SRID. Every usable row has SRID 4326, and the SRID STOP checks
below found 0 failures.

#### Table 14 and Table 15 after the run (#114 and #115)

Both tables equal the "before" tables above, row for row.

Table 14, from [`issue-114-115-table-14-after-2026-10-13.csv`](issue-114-115-table-14-after-2026-10-13.csv):

| Level | Spatial match status | Region rows | Susceptible area (sq km) | Source polygons | Fragments |
| --- | --- | ---: | ---: | ---: | ---: |
| High | `CALCULATED` | 13 | 16,615.1039 | 11,341 | 11,341 |
| High | `NO_SAFE_REGION_BOUNDARY` | 5 | | | |
| Low | `CALCULATED` | 13 | 11,448.7952 | 14,915 | 14,915 |
| Low | `NO_SAFE_REGION_BOUNDARY` | 5 | | | |
| Moderate | `CALCULATED` | 13 | 11,626.4386 | 21,620 | 21,620 |
| Moderate | `NO_SAFE_REGION_BOUNDARY` | 5 | | | |
| Very High | `CALCULATED` | 12 | 4,528.3842 | 3,089 | 3,089 |
| Very High | `NO_MAPPED_EXPOSURE` | 1 | 0.0000 | 0 | 0 |
| Very High | `NO_SAFE_REGION_BOUNDARY` | 5 | | | |

`source_polygon_count` is now counted on its own as distinct `object_id`, and it
equals `intersection_fragment_count` on every row.

Table 15, from [`issue-114-115-table-15-after-2026-10-13.csv`](issue-114-115-table-15-after-2026-10-13.csv):

| Match status | Level | Projects | Matched polygons |
| --- | --- | ---: | ---: |
| `AMBIGUOUS` | | 250 | 502 |
| `MATCHED` | High | 35,672 | 35,781 |
| `MATCHED` | Low | 35,146 | 35,227 |
| `MATCHED` | Moderate | 27,467 | 27,526 |
| `MATCHED` | Very High | 14,425 | 14,462 |
| `UNMATCHED` | | 152,696 | 0 |

#### Corrected checks (#114 and #115)

From [`issue-114-115-key-checks-2026-10-13.csv`](issue-114-115-key-checks-2026-10-13.csv):

| Validator | Check | Action | Status | Failed rows | Total rows |
| ---: | --- | --- | --- | ---: | ---: |
| 06a | Usable geometry is stored in the source SRID | STOP | PASS | 0 | 63,655 |
| 07 | Usable MGB geometry uses the expected longitude-latitude SRID | STOP | PASS | 0 | 63,655 |
| 07 | Source polygon and fragment counts follow their contract | STOP | PASS | 0 | 51 |
| 07 | Territory-mismatched boundaries are never treated as safe geography | STOP | PASS | 0 | 18 |
| 07 | Parsed MGB lineage matches current accepted Bronze MGB ingest | STOP | PASS | 0 | 1 |
| 07 | Runtime MGB counts are compared with historical Bronze references | FLAG | PASS | 0 | 63,684 |
| 08 | Usable MGB geometry uses the expected longitude-latitude SRID | STOP | PASS | 0 | 63,655 |
| 08 | Parsed MGB lineage matches current accepted Bronze MGB ingest | STOP | PASS | 0 | 1 |
| 08 | Runtime MGB counts are compared with historical Bronze references | FLAG | PASS | 0 | 63,684 |

The reference checks now compare 0 blank geometries with a reference of 0.
Before #115 they compared 0 with 1,815 and flagged every run, in
[`issue-115-reference-flag-before-2026-10-13.csv`](issue-115-reference-flag-before-2026-10-13.csv).
Validator 07 dropped from 14 to 13 FLAG findings and validator 08 from 13 to 12.

The territory FLAG still reports 5 of 13 regions with boundary differences from
current PSGC. That is the same finding as before the run. The shared null-safe
predicate did not change it.

#### Run IDs (#114 and #115)

From [`issue-114-115-validator-run-summary-2026-10-13.csv`](issue-114-115-validator-run-summary-2026-10-13.csv):

| Table | Pipeline run ID | Validation run ID |
| --- | --- | --- |
| `silver_mgb_flood_area` | `6667374783ea5197a1976589e8ee9da11e679a92657b9efaa28900f944597619` | `8235dd0bd058584cd9ffb8da8ffae369c8673da3a7d0f4c9739e51ec6ead6d50` |
| `silver_region_flood_exposure` | `5e09d8862ae65d5c304016531893d9c906f317de8056e42d6259c11ce4412ff8` | `f954fb59ecd760845c281b8fb2386da7dff26fb9909238db719dee502202dcf5` |
| `silver_project_flood_map` | `53072d13762efa5c36d7f3b327dfc34204805600c934a27d1ba4d01ae4a2a028` | `6627dbeecff3c3c226aa12b7bc4ba9db8acf38886b321fe2e1073b95e0485dab` |

After this run, every Silver table's newest validation has 0 FAIL.

### What this run does not prove (#112 to #115)

- No heading in this snapshot was ambiguous or unresolved in a way that affects
  its barangays, so the #113 path ran only in tests.
- None of the new STOP checks failed, so their failure paths ran only in tests.
  The 19 new or changed tests fail on the #124 head `80d58a0`.
- This run did not repeat any notebook, so it does not show a second run
  writing the same results.
- Gold `01`, `02`, `05`, `06`, and `07` and the Gold validator did not rerun.
  They still describe the earlier Silver runs.

## October 13, 2026 fail closed after an unresolved heading-like row (issue #113)

### What changed (#113 follow-up)

Review asked that the population match fail closed whenever a heading-like row
cannot be resolved. An all-caps row that is not the sheet subtotal and names no
PSGC locality is tried as a barangay. Before this change, when that row matched
nothing, the rows below it kept the previous locality.

Now that row is treated as a heading this run could not resolve. Every later row
up to the next heading becomes `UNMATCHED` with the reason
`Follows an unresolved heading-like row, so no locality is trusted`. The rule
version is `silver-population-place-v4`. Validator 03 adds the FLAG
`Rows under an unresolved heading-like row remain visible`, as validation
version `silver-geography-population-validation-v3`.

### Check before the change (#113 follow-up)

[`issue-113-unmatched-rows-before-2026-10-13.csv`](issue-113-unmatched-rows-before-2026-10-13.csv)
lists every unmatched row and the accepted rows that follow it:

| Row | All caps | Sheet first row | Accepted rows after it |
| --- | --- | --- | ---: |
| `NEGROS ORIENTAL 1` | Yes | Yes | 0 |
| `SPECIAL GEOGRAPHIC AREA 1` | Yes | Yes | 0 |
| `MAGUINDANAO DEL NORTE 1` | Yes | Yes | 0 |
| `MAGUINDANAO DEL SUR 1` | Yes | Yes | 0 |
| `NEGROS OCCIDENTAL 1*` | Yes | Yes | 0 |
| `SIQUIJOR 1` | Yes | Yes | 0 |
| `San Rafael` | No | No | 5 |
| `Sawata` | No | No | 0 |

The six all-caps rows are sheet subtotals, which are never tried as barangays.
`San Rafael` and `Sawata` are the two known unmatched barangays, not headings. So
no row in this snapshot triggers the rule.

### Run identity and outcome (#113 follow-up)

Databricks serverless, branch `fix/issue-109-stale-mgb-gate`, commit `aa8b7d2`,
October 13, 2026 at 06:05 UTC.

| Step | Notebook | Result |
| ---: | --- | --- |
| 1 | `02_silver_population_place_reconciliation` | Completed. Rule version `silver-population-place-v4`. |
| 2 | `03_silver_region_population` | Completed. Every gate passed. |
| 3 | `03_validation_silver_geography_population` | 35 checks on three tables. All 22 STOP checks passed. 8 FLAG findings. 0 FAIL. |

The reconciliation now has 19 checks, up from 18. The STOP and FLAG counts did
not change, so the new FLAG passed with 0 rows. The run IDs are in
[`issue-113-validator-run-summary-2026-10-13.csv`](issue-113-validator-run-summary-2026-10-13.csv).

### Rows and population (#113 follow-up)

From [`issue-113-fail-closed-run-2026-10-13.csv`](issue-113-fail-closed-run-2026-10-13.csv):

| Disposition | Match status | Source rows | Population | Failed closed |
| --- | --- | ---: | ---: | ---: |
| `ACCEPTED_PRIMARY` | `MATCHED_ALIAS` | 15 | 46,612 | 0 |
| `ACCEPTED_PRIMARY` | `MATCHED_EXACT_CONTEXT` | 41,902 | 111,627,666 | 0 |
| `ACCEPTED_PRIMARY` | `MATCHED_NORMALIZED_CONTEXT` | 80 | 1,048,709 | 0 |
| `INVALID_POPULATION` | `MATCHED_EXACT_CONTEXT` | 11 | 0 | 0 |
| `INVALID_POPULATION` | `MATCHED_NORMALIZED_CONTEXT` | 1 | 0 | 0 |
| `MATCHED_NON_PRIMARY_LEVEL` | `MATCHED_ALIAS` | 2 | 37,766 | 0 |
| `MATCHED_NON_PRIMARY_LEVEL` | `MATCHED_EXACT_CONTEXT` | 1,730 | 196,723,997 | 0 |
| `MATCHED_NON_PRIMARY_LEVEL` | `MATCHED_NORMALIZED_CONTEXT` | 1 | 26,292 | 0 |
| `UNMATCHED` | `UNMATCHED` | 8 | 6,437,703 | 0 |

Every count equals the v3 run above. Regional population stays 112,722,987. The
rule changed 0 rows in this snapshot and protects later snapshots.

### What this run does not prove (#113 follow-up)

- No row in this snapshot triggers the rule, so the fail-closed path ran only in
  tests. The new test fails on the v3 notebook.
- A misspelled heading that happens to match a real barangay in the previous
  locality still passes as a barangay. The at-most-once STOP catches it if that
  accepts one barangay twice.
- Gold `05` and the Gold validator read population. They reran on v4 in the
  next section.

## October 13, 2026 Gold rerun on the final Silver tables (issues #109 to #115)

### Run identity and outcome (Gold rerun)

Databricks serverless, branch `fix/issue-109-stale-mgb-gate`, commit `dbd1824`,
October 13, 2026. Gold `00` started at about 06:38 UTC. The validator wrote its
rows at 06:59:25 UTC.

| Step | Notebook | Result |
| ---: | --- | --- |
| 1 to 8 | Gold `00` to `07` | Completed. |
| 9 | `09_validation_gold` | 75 checks. All 65 STOP checks passed. 9 FLAG checks had findings, and 1 found nothing. 0 FAIL. The gate returned no error. |

The validation run ID is `eb6145ab846c3ddac3f5ed2fbe33809524ab54b8d2f04efe995c4c9cc0ebbd4f`,
with rule version `gold-validation-v2`. Every row is in
[`issue-109-115-gold-validation-2026-10-13.csv`](issue-109-115-gold-validation-2026-10-13.csv).

### Gold equals Silver (Gold rerun)

| Measure | Gold | Silver |
| --- | ---: | ---: |
| Projects (`dim_project`, current `fact_project_snapshot` rows) | 265,656 | 265,656 |
| Current reported budget (PHP) | 6,535,616,688,962.02 | 6,535,616,688,962.02 |
| Project count and budget by region | No differences | |
| Primary population | 112,722,987 | 112,722,987 |
| Flood area (sq km) | 44,218.7219 | 44,218.7219 |
| Region and level pairs with no area | 20 | 20 |
| Official regions | 18 | 18 |

Gold read Silver project run `c6317d2b…`, region map run `54441fa4…`, population
run `c0d36ec4…`, and flood exposure run `5e09d886…`. The full IDs are in the CSV.

### FLAG findings (Gold rerun)

| Check | Rows | Out of |
| --- | ---: | ---: |
| Projects without a region (key `0`): 306 Central Office, 266 unmatched | 572 | 265,656 |
| Projects without a flood level (key `0`): 250 ambiguous, 50,518 with no map point, 102,178 unmatched | 152,946 | 265,656 |
| Projects without a status (key `0`) | 76 | 265,656 |
| Progress not published because Silver did not mark it `VALID` | 98 | 265,656 |
| Long-running flag is empty: no start date, or completion before start | 20,045 | 265,656 |
| Region and level pairs with no area data | 20 | 72 |
| Official regions without a boundary | 1 | 18 |
| Active statuses that look like numbers: `0.00` and `121.0181138` | 2 | 18 |
| Table C rows behind the 4,789-person gap to the 2024 census total: San Rafael 637, Sawata 4,152 | 2 | 43,750 |

Boundary shapes marked not valid found nothing. Every FLAG count equals the
October 12 run for #116 and #119 in [`docs/gold_model.md`](../../model/gold_model.md).

### What this run does not prove (Gold rerun)

- The FLAG counts match the October 12 run, but this run does not compare
  row-level values against it.
- The Power BI report was not refreshed in this run.

## October 13, 2026 pre-match Table C row-role guard (issue #113, PR #130)

### Runtime source

The five supplied Databricks notebook exports contain executed results for the
new row-role contract. The exports show notebook names and results, but they do
not retain a Git commit identifier. This evidence therefore does not assert an
exact executing commit.

No uppercase barangay exception was approved or seeded. The active exception
version remained `NO_APPROVED_ROW_ROLE_EXCEPTION`.

### Run identity and outcome

| Step | Notebook | Result |
| ---: | --- | --- |
| 1 | `00_config_mappings` | Completed. The row-role exception table exists with 0 rows and 0 active approved exceptions. |
| 2 | `02_validation_silver_config` | 26 checks. All 22 STOP checks passed. 4 FLAG checks reported governed review findings. 0 FAIL. |
| 3 | `02_silver_population_place_reconciliation` | Completed. All 43,750 Table C rows were published once under rule version `silver-population-place-v5`. |
| 4 | `03_silver_region_population` | Completed. All 18 official regions were published and the population reconciliation difference was 0. |
| 5 | `03_validation_silver_geography_population` | 40 checks. All 25 STOP checks passed. 10 FLAG checks reported findings, 5 FLAG checks had no finding, and 0 checks failed. |

The selected Table C snapshot was
`metadata-afa2fa4c580930b7c10a`. The selected PSGC snapshot was
`metadata-9f97e93e082df80535d6`. The alias version was
`census-table-c-aliases-2026-10-v1`.

### Row-role and matching results

The executed results are in
[`issue-113-row-role-outcomes-2026-10-13.csv`](issue-113-row-role-outcomes-2026-10-13.csv).

| Measure | Rows |
| --- | ---: |
| Table C source rows | 43,750 |
| Silver reconciliation rows | 43,750 |
| Accepted primary barangays | 41,951 |
| Matched non-primary rows | 1,733 |
| Invalid or non-positive population rows | 12 |
| Unmatched rows | 54 |
| Unresolved heading-like rows | 5 |
| Rows forced unmatched after an unresolved heading-like row | 41 |
| Ambiguous rows | 0 |

The fail-closed checks are in
[`issue-113-row-role-validation-2026-10-13.csv`](issue-113-row-role-validation-2026-10-13.csv).

- unresolved heading-like rows produced 0 trusted matches or localities
- rows after unresolved headings inherited 0 trusted localities
- every Table C row produced exactly one reconciliation row
- accepted PSGC barangay targets remained unique
- the deterministic reconciliation run ID reproduced for all 43,750 rows
- no active approved row-role exception existed

### Regional population result

The 41,951 accepted primary barangays contributed to all 18 official regions.
Accepted and regional population both equal 112,348,732, for a reconciliation
difference of 0.

### Non-blocking follow-up

The five `UNRESOLVED_HEADING_LIKE` rows may use the read-only profiling query in
[`docs/silver_geography_population.md`](../../silver/silver_geography_population.md).
No exception may be approved from the aggregate counts alone. Human review must
confirm the exact source file, sheet, and raw standardized name.

The supplied evidence does not include these operational follow-ups:

- the five-row uppercase candidate profile
- an identical second run proving rerun behavior
- the dependent Gold population fact and Gold validator rerun
- analytics and analytics validation after any Gold change

These items do not block Issue #113. The issue's unsafe locality inheritance is
closed by the fail-closed row role, and the independent duplicate-target STOP
passed with 0 failures. The five candidates remain visible and unmatched rather
than receiving an inferred PSGC assignment.
