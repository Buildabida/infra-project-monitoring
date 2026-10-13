# Exploratory analytics views validation evidence

## Scope

This report records Databricks evidence for the five exploratory monitoring views from issue #131 (D-54, proposed).
The views sit beside the six official business-question views, Q1 to Q6, and do not change them.

The evidence covers:

- building all eleven views in `05-analytics`
- the snapshot gate and the Gold gate before validation
- 152 checks under rule version `analytics-validation-v2`, which rebuild each view from Gold and compare it row by row
- a regression comparison of the 87 Q1 to Q6 checks with the October 12 evidence

The evidence comes from the executed notebooks `05_analytics/01_business_questions` and `04_validation/10_validation_analytics`, exported from Databricks.
The SQL in both exported notebooks is the same, cell for cell, as the SQL on the feature branch.
The exported notebooks carry no run timestamp. The run read the Gold built on October 13, 2026, after the Silver audit fixes for #109 to #115. See the run IDs below and the [Gold model](../../gold_model.md#runtime-evidence).

## Run identity

| Item | Value |
| --- | --- |
| Validation run ID | `388660efc9c6034b28e5cfbc2c5ba8ff7d6b4e350da9964667b0167186f7a995` |
| Rule version | `analytics-validation-v2` |
| DPWH snapshot ID | `metadata-6321c7aa6f2a14e12f4c` |
| MGB snapshot ID | `metadata-17bf5e65e1838a2f7be9` |
| Gold `fact_project_snapshot` run ID | `def31215c60484374b1bbe3c284d60cff77d2f0728753bde48c74cb1064d6286` |
| Gold `dim_region` run ID | `ebbacae44fad379b5ea2488e0bb38294fb5d816cb5d2d543f01e3cd3fa4e6b95` |
| Gold `fact_region_population` run ID | `63284e351aad12e62ccde0d27b719fa4a1e089cde22203238ba3db65a017b253` |
| Gold `fact_region_flood_exposure` run ID | `26416088e406d1a4d959dc069cd65bab019880815bbe763d3a66e2125f892e48` |

The validation run ID uses the D-52 recipe unchanged. It differs from the October 12 ID because the Gold runs and the rule version are new.

## Outcome

- The snapshot gate passed in both notebooks: current Gold holds exactly one DPWH snapshot, with no empty ID.
- The Gold gate passed: the latest Gold validation had no failed STOP check and covered the current population and exposure facts.
- `01_business_questions` created all eleven views.
- `10_validation_analytics` saved 152 checks: 134 `PASS` and 18 `FLAG`, with zero `FAIL`.
- All 132 checks with action `stop` passed, and the STOP gate passed.
- Two checks with action `flag` found nothing, so they count as `PASS`. Both belong to Q1 to Q6.

| Views | STOP passed | FLAG with findings | FLAG with none |
| --- | ---: | ---: | ---: |
| Six official views (Q1 to Q6) | 74 of 74 | 11 | 2 |
| Five exploratory views | 58 of 58 | 7 | 0 |
| **All** | **132 of 132** | **18** | **2** |

The complete results are in [`validation-results-analytics-v2.csv`](validation-results-analytics-v2.csv).

## Q1 to Q6 regression

The 87 Q1 to Q6 checks in this run match the [October 12 evidence](../analytics-views/validation-results-2026-10-12-after-125.csv) row for row. Each has the same status, failed rows, total rows, and details.
This holds although the run read a newer Gold `fact_project_snapshot` run.
The six view definitions are byte-for-byte the same as on `main`, and `tests/test_analytics.py` pins them.

| View | Rows on October 12 | Rows in this run |
| --- | ---: | ---: |
| `analytics_regional_investment` | 18 | 18 |
| `analytics_category_portfolio` | 9 | 9 |
| `analytics_project_delivery_status` | 342 | 342 |
| `analytics_population_equity` | 18 | 18 |
| `analytics_flood_control_exposure` | 18 | 18 |
| `analytics_region_category` | 123 | 123 |

## Exploratory views

| View | Rows | Grain |
| --- | ---: | --- |
| `analytics_infrastructure_year_trend` | 12 | 11 years from 2016 to 2026, plus the `NULL` year |
| `analytics_infrastructure_year_sector` | 76 | Year, sector, and mapping status |
| `analytics_delivery_cohort` | 35 | Year, status group, and status mapping status |
| `analytics_project_size_concentration` | 18 | Official region, the same 18 as Q1 |
| `analytics_implementing_office_portfolio` | 222 | 221 offices plus the `NULL` office |

Every exploratory view carries the DPWH snapshot `metadata-6321c7aa6f2a14e12f4c`.

### Totals

| View | Projects | Reported budget (₱) |
| --- | ---: | ---: |
| `analytics_infrastructure_year_trend` | 265,656 | 6,535,616,688,962.02 |
| `analytics_infrastructure_year_sector` | 265,656 | 6,535,616,688,962.02 |
| `analytics_implementing_office_portfolio` | 265,656 | 6,535,616,688,962.02 |
| **All current Gold projects** | **265,656** | **6,535,616,688,962.02** |

The cohort view adds up to the trend view's projects, flag denominators, and For Procurement count for every year.
The size view matches Q1 for every region, so with region key `0` (572 projects) it adds up to every current Gold project.

### Infrastructure-year cohorts

`infra_year` is a project cohort in the current snapshot, not the DPWH portfolio of that year.
The table is in [`infra-year-cohorts.csv`](infra-year-cohorts.csv). Databricks shows the `NULL` year as `null`.

| `infra_year` | Projects | Reported budget (₱) | For Procurement | No status group |
| --- | ---: | ---: | ---: | ---: |
| 2016 | 21,216 | 393,687,705,953.15 | 0 | 0 |
| 2017 | 26,387 | 467,605,603,262.97 | 0 | 0 |
| 2018 | 26,623 | 641,842,673,931.36 | 0 | 0 |
| 2019 | 22,927 | 415,245,512,222.90 | 0 | 0 |
| 2020 | 21,865 | 490,859,668,035.35 | 0 | 0 |
| 2021 | 23,187 | 483,072,639,132.83 | 0 | 0 |
| 2022 | 23,164 | 739,275,046,442.61 | 0 | 0 |
| 2023 | 26,171 | 906,191,518,447.53 | 0 | 0 |
| 2024 | 30,741 | 1,078,916,760,286.30 | 2,043 | 0 |
| 2025 | 27,794 | 865,146,960,960.33 | 3,363 | 0 |
| 2026 | 15,479 | 53,772,600,271.67 | 13,631 | 0 |
| `NULL` | 102 | 15.02 | 0 | 102 |

What the run shows, without interpretation:

- Every observed year is between 2016 and 2026. No shifted or outlier year appears, so the views need no year filter.
- All 19,037 For Procurement projects are in the 2024, 2025, and 2026 cohorts. In the 2026 cohort, 13,631 of the 15,479 projects are For Procurement. The total matches D-46.
- 19,037 of the 23,569 zero-progress projects are For Procurement (D-46). A cohort's `pct_zero_progress` must be read with its `for_procurement_count`.
- The 102 projects without an `infra_year` are the same 102 projects with no status group. Of these, 76 have no source status and 26 have no approved status rule. Together they report a budget of ₱15.02. This run does not show why the two sets match.

### Delivery by cohort

Each year has three rows, one per status group, and the `NULL` year has two rows, one per status reason.
Within each year, `pct_of_year_projects` adds up to 100.00.

### Project size concentration

- Every region in the view has a reported budget for all its projects. All 87 projects without a budget are on region key `0`, in the `UNMATCHED` group.
- 19,379 projects in the view report a budget of 0, and they stay in the median and p90.
- BARMM has no mapped DPWH project, so its row shows `NO_MAPPED_PROJECT_DATA` and no distribution value. This is the same as on October 12.

### Implementing offices

- 221 offices and one `NULL` office row. The `NULL` row holds 97 projects with a reported budget of ₱15.02, and it has no rank.
- No office row had a count, budget, median, spread, flag, rate, or rank break.

## Validation flags

The flags keep known data limits visible. They do not change any view.

### Flags on the exploratory views

| View | Check | Finding |
| --- | --- | ---: |
| Trend | Projects with no infrastructure year (`infra_year` `NULL`), ₱15.02 | 102 of 265,656 |
| Trend | Projects without a long-running flag | 20,045 of 265,656 |
| Trend | Zero-progress projects that are For Procurement (D-46) | 19,037 of 23,569 |
| Cohort | Projects with no mapped status group (76 `NO_SOURCE_STATUS`, 26 `NO_APPROVED_STATUS_RULE`) | 102 of 265,656 |
| Size | Projects in the view with a reported budget of 0 | 19,379 of 265,084 |
| Size | Official regions with no or limited DPWH project coverage (BARMM `NO_MAPPED_PROJECT_DATA`) | 1 of 18 |
| Office | Projects with no resolved implementing office, ₱15.02 | 97 of 265,656 |

### Flags on Q1 to Q6

The 11 Q1 to Q6 flags with findings, and the 2 with none, are the same as in the [October 12 evidence](../analytics-views/README.md#validation-flags).

## Not covered

- The exported notebooks carry no run timestamp, so this report gives none.
- This run does not show a rerun of the validator on the same Gold. The `MERGE` key is unchanged from D-52, so a rerun updates the same 152 rows.
- The run does not output the median, p90, or rank values themselves. The validator compared every one of them with Gold, and none broke.
