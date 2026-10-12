# Analytics views

This folder builds the views that the dashboard (#20) and Genie (#21) read. Each view answers one business question from current-snapshot Gold. The views live in the `05-analytics` schema and hold no data of their own.

## Run order

1. `09_validation_gold` must pass first.
2. Run `01_business_questions.ipynb`. It creates `05-analytics` if it does not exist, then the six views with `CREATE OR REPLACE VIEW`.
3. Run `04_validation/10_validation_analytics.ipynb`. It rebuilds every view from Gold and saves its checks to `04-validation.analytics_dq_results`. It stops the run if any STOP check fails.

A rerun replaces the view definitions and updates the same validation rows, so it is safe to run twice.

## Views

| View | Question | One row per |
| --- | --- | --- |
| `analytics_regional_investment` | Q1. Which regions receive the most and least reported investment and projects? | Official PSGC region |
| `analytics_category_portfolio` | Q2. Which categories receive the largest budget share, and how does flood control compare? | Sector, flood flag, and mapping status |
| `analytics_project_delivery_status` | Q3. Which regions and categories have the most ongoing, inactive, or long-running projects? | Region, sector, status group, and mapping status |
| `analytics_population_equity` | Q4. Which regions receive more or less investment than their share of population? | Official region |
| `analytics_flood_control_exposure` | Q5. How does flood control compare with regional flood exposure? | Official region |
| `analytics_region_category` | Q6. How is each region's budget split across infrastructure types (D-27)? | Region, sector, and mapping status |

Every view and column has a comment, so Genie can read what each one means.

## Rules every view follows

- Reads only `` `03-gold` `` tables, only rows where `is_current_snapshot = TRUE`.
- Budget means the reported project or contract budget, never payment (D-28). A missing budget stays `NULL`.
- Region key `0` (Central Office and unmatched projects) is left out of every regional view. Q2 is national, so it includes them.
- Every official region keeps a row. `source_coverage_status` says how far to trust it: `REPORTED`, `LIMITED_SOURCE_COVERAGE` for BARMM with projects, or `NO_MAPPED_PROJECT_DATA`. Only `REPORTED` regions are ranked or compared.
- An unmapped sector or status stays `NULL`, and a reason column says why (D-37). No view writes `Unknown` or `Unmapped`.
- Every view carries `source_snapshot_id` (D-29). Q5 also carries `mgb_source_snapshot_id`.

## For the dashboard

- Label `NULL` sectors and statuses in the chart, such as "Not categorized". Keep the label out of the data.
- Show BARMM as "no or limited DPWH project coverage", never as low or zero investment.
- Q2 has two flood control shares. The strict share counts single-sector Flood Control and Drainage. The broad share counts every project with a flood component (D-39). Show both, because the real amount sits between them.
- In Q5, show `exposure_area_status` when area figures are blank, and show `flood_control_points_classified_pct` next to the High or Very High share. A point outside mapped zones is not low risk.
- These numbers describe the data. They do not show need, fairness, delay, or adequacy.

## Known limits

- Q5 has no total flood area for regions whose flood levels overlap. A Gold column for the Silver all-level union would fix it.
- Q5 has no area figures for Western Visayas, Central Visayas, Zamboanga Peninsula, NIR, and BARMM, because the boundary file predates NIR and the Sulu move.
- Q4 uses Gold's population, which is about 3.4% below the census total (#61).
- Stalled projects are not reported (D-46).

See issue #126 for the full scope and acceptance evidence.
