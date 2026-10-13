# Analytics views

This folder builds the views that the dashboard (#20) and Genie (#21) read. The Analytics layer contains six official business-question views plus five exploratory monitoring views. Each official view answers one business question. The exploratory views support broader monitoring and exploration (D-54, proposed). All views read current-snapshot Gold, live in the `05-analytics` schema, and hold no data of their own.

## Run order

1. `09_validation_gold` must pass first.
2. Run `01_business_questions.ipynb`. It stops unless current Gold holds exactly one DPWH snapshot. Then it creates `05-analytics` if it does not exist, and the eleven views with `CREATE OR REPLACE VIEW`. These are the six official views (D-50, D-51) and the five exploratory views (D-54, proposed).
3. Run `04_validation/10_validation_analytics.ipynb`. It checks the snapshot and the Gold validation again, rebuilds every view from Gold, and saves its checks to `04-validation.analytics_dq_results` (D-52). It stops the run if any STOP check fails. See [analytics validation](../../docs/validation.md#analytics-validation).

A rerun replaces the view definitions and updates the same validation rows, so it is safe to run twice.

## Views

### Official business-question views

| View | Question | One row per |
| --- | --- | --- |
| `analytics_regional_investment` | Q1. Which regions receive the most and least reported investment and projects? | Official PSGC region |
| `analytics_category_portfolio` | Q2. Which categories receive the largest budget share, and how does flood control compare? | Sector, flood flag, and mapping status |
| `analytics_project_delivery_status` | Q3. Which regions and categories have the most ongoing, inactive, or long-running projects? | Region, sector, status group, and mapping status |
| `analytics_population_equity` | Q4. Which regions receive more or less investment than their share of population? | Official region |
| `analytics_flood_control_exposure` | Q5. How does flood control compare with regional flood exposure? | Official region |
| `analytics_region_category` | Q6. How is each region's budget split across infrastructure types (D-27)? | Region, sector, and mapping status |

### Exploratory monitoring views

| View | What it helps explore | One row per |
| --- | --- | --- |
| `analytics_infrastructure_year_trend` | How do the projects of each infrastructure-year cohort look in the current snapshot? More or fewer projects, larger or smaller ones, and their current status and delivery flags. | `infra_year`, including `NULL` |
| `analytics_infrastructure_year_sector` | Does the sector mix differ across cohorts? | `infra_year`, sector, and mapping status |
| `analytics_delivery_cohort` | Do older cohorts still hold active, long-running, or zero-progress projects? | `infra_year`, status group, and status mapping status |
| `analytics_project_size_concentration` | Is a region's budget spread over many smaller projects or held by a few larger ones? | Official region |
| `analytics_implementing_office_portfolio` | Which implementing offices carry the largest observed workload? | `implementing_office`, including `NULL` |

The exploratory views add views. They never change the six official views.

Every view and column has a comment, so Genie can read what each one means.

## Rules every view follows

- Reads only `` `03-gold` `` tables, only rows where `is_current_snapshot = TRUE`.
- Budget means the reported project or contract budget, never payment (D-28). A missing budget stays `NULL`.
- Region key `0` (Central Office and unmatched projects) is left out of every regional view, including `analytics_project_size_concentration`. Q2 and the cohort and office views are national, so they include them.
- Every official region keeps a row. `source_coverage_status` says how far to trust it: `REPORTED`, `LIMITED_SOURCE_COVERAGE` for BARMM with projects, or `NO_MAPPED_PROJECT_DATA`. Only `REPORTED` regions are ranked or compared.
- An unmapped sector or status stays `NULL`, and a reason column says why (D-37). No view writes `Unknown` or `Unmapped`.
- Every view carries `source_snapshot_id` (D-29). Q5 also carries `mgb_source_snapshot_id`.

## Rules for the exploratory views

- `infra_year` is a **project cohort attribute** in the current snapshot. The cohort views compare the projects of different infrastructure years as they look now. They never show what the DPWH portfolio looked like in a past year. Write "projects in the 2018 cohort", never "DPWH in 2018".
- A project without an `infra_year` keeps its own `NULL` row. The views keep every year Gold publishes and have no 2016 to 2026 filter.
- Status counts use the approved groups `FINISHED`, `ACTIVE`, and `INACTIVE` (D-40). `ACTIVE` includes `For Procurement`. Projects with no group stay visible as `unmapped_status_count` or as their own `NULL` rows.
- Long-running and zero-progress use the Q3 rules: each rate divides by the projects where its flag is known. Long-running does not mean delayed.
- `pct_zero_progress` includes `For Procurement` projects, the same as Q3. D-46 allows a zero-progress count that says so. The cohort views add `for_procurement_count` to show how many there are. A zero-progress project is not stalled.
- `analytics_project_size_concentration` takes its regions and coverage from Q1 and leaves key `0` out. Its median and p90 are exact `PERCENTILE_CONT` values over projects with a reported budget that is not `NULL`. A reported 0 stays in. There are no budget bands, because bands need their own decision.
- `analytics_implementing_office_portfolio` keeps a `NULL` office as its own row with no rank. Gold does not say whether that office was missing or conflicting.
- No exploratory view reads contractors. A contractor view waits for Gold to carry contractor resolution status and for a name standardization rule (D-54, proposed).

## For the dashboard

- Label `NULL` sectors and statuses in the chart, such as "Not categorized". Keep the label out of the data.
- Show BARMM as "no or limited DPWH project coverage", never as low or zero investment.
- Q2 has two flood control shares. The strict share counts single-sector Flood Control and Drainage. The broad share counts every project with a flood component (D-39). Show both, because the real amount sits between them.
- In Q5, show `exposure_area_status` when area figures are blank, and show `flood_control_points_classified_pct` next to the High or Very High share. A point outside mapped zones is not low risk.
- These numbers describe the data. They do not show need, fairness, delay, or adequacy.
- For the cohort charts, label the axis "infrastructure-year cohort" and say the figures come from the current snapshot. A higher active share in a newer cohort is expected, because those projects started later. Do not present a cohort chart as DPWH performance over time.
- Show the `NULL` year and the `NULL` office with a display label, such as "No year in source" or "No resolved office". Keep the label out of the data, and never rank the `NULL` office.
- Next to any zero-progress rate, say that it includes projects still in procurement and show `for_procurement_count` where the view has it. Never call these projects stalled.
- In the size view, show the average and the median together. An average well above the median means a few large projects carry the region budget. Neither pattern is good or bad. Read BARMM as limited source coverage.
- Office figures describe workload. A high project count, budget, or long-running rate does not show office quality or performance.
- The flood-point chart needs no new view. Use the five `flood_control_points_*` columns of Q5.

## Known limits

- Q5 has no total flood area for regions whose flood levels overlap. A Gold column for the Silver all-level union would fix it.
- Q5 has no area figures for Western Visayas, Central Visayas, Zamboanga Peninsula, NIR, and BARMM, because the boundary file predates NIR and the Sulu move.
- Q4 uses Gold's population, which is about 3.4% below the census total (#61).
- Stalled projects are not reported (D-46).
- Gold has no reason column for a `NULL` `infra_year` or a `NULL` `implementing_office`, so the views cannot say why either is empty.
- The cohort views read one current snapshot. Showing how the portfolio changed over time would need older snapshots in Gold.

See issue #126 for the scope and acceptance evidence of the six official views. The first Databricks run of all eleven views is in the [exploratory analytics evidence](../../docs/evidence/exploratory-analytics-views/README.md).
