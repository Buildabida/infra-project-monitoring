# Dashboard specification

This spec describes the capstone dashboard as exported on October 20, 2026. The exported file is [`buildabida_infrastructure_project_monitoring.lvdash.json`](buildabida_infrastructure_project_monitoring.lvdash.json). The dashboard is written for citizens: every title, note, and label uses plain words.

It answers one business question: **How can DPWH better monitor where its infrastructure investments go?** After a mentor review on October 19, it has four tabs: an overview, then one tab per analytics question, plus a Read Me page. Most charts compare two things at once, such as region and year, or flood risk and completion. The view contracts are in the [Analytics views guide](../notebooks/05_analytics/README.md).

Build or refresh it only after `10_validation_analytics` and the end-to-end quality gate pass. The `business_dashboard` task of the [pipeline job](../resources/buildabida_full_pipeline.job.yml) runs after both.

## Data rules

- Every dataset reads only the six views in `` `buildabida-capstone`.`05-analytics` ``. The map datasets also read the Gold boundary tables `dim_region_boundary` and `dim_province_reporting_area_boundary`, for map shapes only.
- No dataset reads Silver, Bronze, or any table that is not listed here.
- No dataset creates an object in Unity Catalog. `05-analytics` holds only the six views.
- A missing value shows as "No data", never as 0.
- Never add up columns that repeat on many rows: `geography_project_count`, `geography_budget_pesos`, `geography_budget_share_pct`, the population columns of view 5, `physical_progress_pct`, and every rank. Read them with `MAX`, or group to one row per place first.
- In `analytics_investment_distribution`, always filter one `geography_level`. Never add regions and provinces together.
- Leave BARMM (`LIMITED_SOURCE_COVERAGE`) out of every ranking and comparison. Keep it in coverage counts.
- "Project year" is `infra_year`, a cohort. It is not the year money was paid.
- Do not use a hyphen in a dataset name. The dashboard turns the name into an entity name, and a hyphen breaks the widget queries.

## Theme

| Setting | Value |
| --- | --- |
| Colors | Navy, orange, and light blue: `#1A1B41`, `#F79820`, `#1B5B93`, `#87CBEB`, `#41497B`, `#F7B055`, `#0D2C54`, `#B8DEEF`, `#5C6B8A`, `#2E3A59` |
| Canvas and widget background | `#FFFFFF` |
| Widget outline and grid lines | `#E4EAF2` |
| Text | `#1A1B41` |
| Maps and heat maps | Custom sequential scale from `#87CBEB` (low) to `#1A1B41` (high) |
| Number format | Money as PHP with compact numbers, such as PHP 6.5T. Percentages with 1 decimal place. Counts with thousands separators |

## Datasets

| Dataset | Reads | Used on |
| --- | --- | --- |
| `national_totals` | views 3 and 4 | Overview counters |
| `data_connections` | views 4 and 5 | Overview "Why connecting the data mattered" |
| `region_money_by_year` | view 1 at `REGION` level, region boundaries | Overview map, AQ1 map, AQ3 map |
| `d01_region_budget_by_year` | view 1, region by project year | AQ1 line charts and ranking |
| `d02_region_completion` | view 4, BARMM left out | AQ1 completion heat map |
| `d03_flagged_by_type_year` | view 4, BARMM left out | AQ1 and AQ2 flagged charts |
| `d09_region_share_by_year` | view 1 | AQ1 region by year heat map |
| `d10_region_money_vs_completion` | views 1 and 4 | AQ1 money vs completion scatter |
| `regional_review_by_cohort` | views 1 and 4 | AQ1 no-progress and long-running heat maps |
| `top3_region_share` | view 1, one row per region first | AQ1 top-3 counter |
| `project_check_list` | view 4, flagged projects only | AQ1 projects to check |
| `d04_type_budget_by_year` | view 4 | AQ2 type line charts and status bar |
| `d05_months_to_complete` | view 4, completed projects with both dates | AQ2 months to finish |
| `d06_province_flood_vs_completion` | view 5 | AQ2 flood vs completion scatter |
| `d11_region_type_mix` | views 1 and 4 | AQ2 region by type heat map |
| `d12_type_completion_by_year` | view 4 | AQ2 type by year heat map |
| `d13_province_type_map` | view 5, province boundaries | AQ2 province map by type |
| `flood_completion` | view 5 | AQ2 completion by flood risk |
| `d07_region_need_vs_money` | views 1, 3, and 5 | AQ3 flood risk vs money per person |
| `d08_places_left_behind` | view 2, compared places only | AQ3 least money per person |
| `d14_province_per_person_map` | view 2, province boundaries | AQ3 budget per person map |
| `d15_province_people_vs_money` | view 2 | AQ3 people share vs money share |
| `region_flood_map` | view 3, region boundaries | AQ3 flood risk map |
| `flood_risk_by_region` | view 3 | AQ3 flood-control budget by risk |

Views: 1 `analytics_investment_distribution`, 2 `analytics_population_equity`, 3 `analytics_flood_alignment`, 4 `analytics_implementation_monitoring`, 5 `analytics_infrastructure_network`, 6 `analytics_integration_coverage`.

## Tabs

### Overview

- The business question and the national counters
- What this shows that the DPWH portal doesn't
- How the six source datasets connect, with connection counters
- A one-line answer for each question
- The map of where the money goes

### AQ1: Where is the money going?

Which regions get the most money, how that changed, and how well each region finishes its projects.

- Region lines by year, the region by year heat map, and the top-3 share
- The latest-year map and the region ranking
- The completion heat map and the money vs completion scatter
- Flagged projects by region and type
- No-progress and long-running heat maps, and the projects to check first

### AQ2: What are we building?

What kinds of projects get the money, where they are built, how long they take, and how they do in flood-risk areas.

- Type lines by year: budget, completed, ongoing, not started, and flagged
- Status by type and usual months to finish
- Region by type and type by year heat maps
- The province map by type
- The flood vs completion scatter and completion by flood risk

### AQ3: Who are we leaving behind?

Money compared with people and flood risk.

- Flood risk vs money per person, by region
- Budget per person by province, beside flood risk by region
- Places with the least money per person, and people share vs money share
- Flood-control budget by flood risk level
- What DPWH can do next, and what other questions we can ask

### Read Me

Page guide, glossary, caveats, and BARMM coverage.

## Check values

With no filter selected, on the data of the October 19, 2026 job runs:

| Tab | Widget | Value |
| --- | --- | --- |
| Overview | Projects | 265,582 |
| Overview | Recorded budget | PHP 6.5T |
| Overview | Projects completed | 80.8% |
| Overview | Projects flagged for checking | 6.1% |
| Overview | Flood-control projects in high flood-risk areas | 52.4% |
| AQ1 | Lowest completion, Zamboanga Peninsula | 72.8% |
| AQ1 | Highest completion, SOCCSKSARGEN | 87.8% |

The project count matches the [end-to-end gate evidence](../docs/evidence/end-to-end-gate-2026-10-19/README.md). If a widget shows another number with no filter, it is adding the wrong rows.

## Known gaps

- Budget per kilometer is not shown. The DPWH data has no project length field.
- On AQ2, the Region filter does not change the year-by-year type charts, because their datasets have no region column.
- The table widget cannot shade cells, so the percent columns of the tables have no color scale.
