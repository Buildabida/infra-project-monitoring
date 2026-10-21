# Update resilience

Issue #48 asks whether the pipeline survives an update: a newer DPWH pull, new or renamed columns, and PSGC codes we can't match. This page says what is proven, what is only covered by checks, and what is still open.

## What happens when a source changes

| Change | What the pipeline does | Where | Proof |
| --- | --- | --- | --- |
| A required column is missing or renamed, like `budget` becoming `contract_amount` | **Stops** before any write. The last good Bronze table stays | `validate_source_header` in [`src/bronze.py`](../../src/bronze.py), run by `01_check_sources` and every loader | Unit tests `test_every_required_source_field_group_must_be_present` and `test_renamed_required_column_still_blocks_the_load` |
| An optional column is new, missing, or renamed | Loads, and `01_check_sources` reports it in `header_drift` without blocking | `header_drift` in [`src/bronze.py`](../../src/bronze.py) | Three `test_header_drift_*` unit tests with synthetic headers. Not run on Databricks yet |
| A newer file arrives | Gets a new snapshot ID from its metadata, replaces the Bronze table only after a full read, write, and row check, and logs it in `load_log` | [Bronze architecture](../bronze/bronze_r2_architecture.md) | Existing Bronze tests and evidence |
| The same file arrives again | `SKIPPED_IDEMPOTENT`, no reload | Same | Bronze evidence |
| A Silver or Gold table was not rebuilt after the new snapshot | The end-to-end gate **stops**: its evidence is older than the new Bronze load, or the layers name different snapshots | [Quality gate](../../notebooks/06_data_quality/README.md) | `test_evidence_older_than_the_latest_bronze_load_is_stale` and `test_layers_on_different_snapshots_stop` |
| A project's place can't be matched | It stays with match status and key `0`, visible as a FLAG. It is never dropped | Silver mapping and Gold key `0` rules | Silver and Gold validators |
| A PSGC code is not in the PSGC version we use | Not matched, so it stays unresolved with key `0` and shows in the FLAG counts. There is no separate "unknown PSGC code" check, and no old-to-new code crosswalk | Silver geography | Gap, see below |

## Still open

1. **A second real DPWH pull.** We hold one DPWH snapshot. The October 10 MGB reload was a different source, so it does not count. #48 needs two full runs on two DPWH pulls, with dates, row counts, and check results.
2. **The dashboard on the newer pull.** Needs item 1.
3. **A PSGC code change test on Databricks.** Copy the PSGC CSV and change one province code. Load it as a controlled snapshot with the `source_path` widget in a `dev` deploy. Confirm that affected projects move to key `0` and FLAG counts rise. Don't overwrite the team workspace's tables.
4. **An "unknown PSGC code" check and an old-to-new crosswalk.** Neither exists. Adding them is a Silver change that needs a decision first.

## How to run the second-pull test

1. Put the newer `dpwh_projects.csv` in the volume, keeping the older one as R2 history.
2. Run `01_check_sources`. Save its output, including `header_drift`.
3. Run the pipeline job. Save the run ID, every task status, and `quality_gate_summary`.
4. Compare row counts and FLAG counts with the [Analytics evidence](../evidence/analytics-2026-10-16/README.md).
5. Open the dashboard and confirm it shows the newer `source_snapshot_id`.
6. Save everything in a new dated folder under `docs/evidence/`, and link it from `docs/validation/validation.md`.
