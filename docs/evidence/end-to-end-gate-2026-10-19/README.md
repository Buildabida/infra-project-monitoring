# End-to-end quality gate: first Databricks run

The 50-task `buildabida-full-pipeline` job ran in the team workspace on October 19, 2026, with the end-to-end quality gate for the first time. The first attempt stopped at the gate because of a bug in the gate. The fix, a repair, and a passing gate followed in the same job run. This page records what happened and what the gate saw.

| Field | Value |
| --- | --- |
| Job | `buildabida-full-pipeline`, job ID `795625524246928` |
| Job run | `457335378856032`, launched manually |
| Started | 2026-10-19 12:17:51 UTC |
| Branch | `feat/productionize-governance` (pull request #138) |
| DPWH snapshot | `metadata-6321c7aa6f2a14e12f4c` |

## Incident: the gate stopped a good run

| Part | What happened |
| --- | --- |
| Incident | After 1h 6m 44s, `end_to_end_quality_gate` failed and `business_dashboard` was skipped. The failure email arrived. |
| Problem | The gate said `silver_validation_geography_population` was missing `silver_psgc_place` and `silver_population_place_reconciliation`, although its 8 saved checks all passed. The gate grouped each validator's rows by `validation_run_id`, but that validator gives each of its three tables its own run ID. So the gate found only one table under the run ID it looked up. The data was fine. The gate was wrong. |
| Resolution | Commit `adb3a1f` made the geography validator use one run ID for all three tables, and a repair of the same job run passed the gate. The gate itself was then changed to group a validator's rows by its save time (`run_ts`): every validator saves all its rows in one write with one timestamp. That works with either run-ID recipe. |
| Prevention | `tests/test_quality_gate.py` now gives each validator its own save time, and gives the geography validator one run ID per table, as real runs do. Three regression tests were added. Against the old gate, two of them fail the same way Databricks did. |

The failure path itself behaved as designed. The gate saved its result before it failed, Databricks skipped the dashboard refresh, and the failure email arrived.

## Gate result after the repair

Saved at 2026-10-19 13:40:22 UTC.

| Layer | Status | Checks | Pass | Flag | Failed STOP | Missing |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| bronze | FLAG | 126 | 119 | 7 | 0 | 0 |
| silver | FLAG | 334 | 263 | 71 | 0 | 0 |
| gold | FLAG | 99 | 90 | 9 | 0 | 0 |
| analytics | FLAG | 112 | 90 | 22 | 0 | 0 |
| end_to_end | PASS | 4 | 4 | 0 | 0 | 0 |
| **ALL** | **FLAG** | **675** | **566** | **109** | **0** | **0** |

`FLAG` means known data limits, which stay visible. No STOP check failed and no evidence was missing, so the dashboard refreshed.

The check counts match earlier evidence: 126 Bronze checks, 112 Analytics checks, and 99 Gold checks (75 from `09_validation_gold` and 24 from `09a_validation_gold_province_reporting`).

## Totals across layers

| Layer | Projects | Reported budget (pesos) |
| --- | ---: | ---: |
| `02-silver.silver_project` | 265,582 | 6,535,616,688,947.00 |
| `03-gold.fact_project_snapshot`, current rows | 265,582 | 6,535,616,688,947.00 |
| `05-analytics.analytics_implementation_monitoring` | 265,582 | 6,535,616,688,947.00 |

This is the reported project or contract budget, not payment (D-28). The October 12 and 13 Gold evidence had 265,656 current projects. This run has 74 fewer. The difference has not been traced yet. A likely cause is the Bronze multiline CSV fix in #133, but that is not confirmed.

## Validator runs

After this one gate run, `quality_gate_results` holds one validator run ID for each of the 13 validators. The four cross-layer checks have no validator run ID by design. This becomes rerun evidence only after a second run, below.

## Still to record

- **Rerun on unchanged data.** Run the job again with no data change, then repeat the gate summary, the totals, and the validator-run query. The totals must not change. Every Silver, Gold, and Analytics validator must keep one run ID across both runs. Bronze gets a new run ID each run, by design.
- **Screenshots** for this folder: the failure email, the failed gate task with its error, the run timeline with `business_dashboard` skipped, and the final task graph with every task green. Add them under `images/` and link them here.
