# Dashboard specification

This spec describes the latest capstone dashboard supplied on October 21, 2026.
The canonical file is
[`buildabida_infrastructure_project_monitoring.lvdash.json`](buildabida_infrastructure_project_monitoring.lvdash.json).
The dashboard is written for citizens: titles, notes, and labels use plain
words.

It answers one business question: **How can DPWH better monitor where its
infrastructure investments go?** It has five visible pages: an overview, one
page per analytics question, and Read Me. Most charts compare two things at
once, such as region and year, or flood risk and completion. The view contracts
are in the [Analytics views guide](../notebooks/05_analytics/README.md).

Build or refresh it only after `10_validation_analytics` and the end-to-end quality gate pass. The `business_dashboard` task of the [pipeline job](../resources/buildabida_full_pipeline.job.yml) runs after both.

## Data rules

- Every dataset reads only the Analytics views in `` `buildabida-capstone`.`05-analytics` ``. The map datasets also read the Gold boundary tables `dim_region_boundary` and `dim_province_reporting_area_boundary`, for map shapes only.
- No dataset reads Silver, Bronze, or any table that is not listed here.
- No dataset creates an object in Unity Catalog. `05-analytics` holds only the Analytics views.
- A missing value shows as "No data", never as 0.
- Never add up columns that repeat on many rows: `geography_project_count`, `geography_budget_pesos`, `geography_budget_share_pct`, the population columns of view 5, `physical_progress_pct`, and every rank. Read them with `MAX`, or group to one row per place first.
- In `analytics_investment_distribution`, always filter one `geography_level`. Never add regions and provinces together.
- Leave BARMM (`LIMITED_SOURCE_COVERAGE`) out of every ranking and comparison. Keep it in coverage counts.
- "Project year" is `infra_year`, a cohort. It is not the year money was paid.
- Do not use a hyphen in a dataset name. The dashboard turns the name into an entity name, and a hyphen breaks the widget queries.

## Theme

| Setting | Value |
| --- | --- |
| Visualization colors | `#077A9D`, `#FFAB00`, `#00A972`, `#FF3621`, `#8BCAE7`, `#AB4057`, `#99DDB4`, `#FCA4A1`, `#919191`, `#BF7080` |
| Canvas background | Light mode: `#F6F5FA`. Dark mode: `#11171C` |
| Widget background and outline | Light mode: `#FFFFFF`. Dark mode: `#11171C` |
| Text | Light mode: `#11171C`. Dark mode: `#E8ECF0` |
| Selection | Light mode: `#2272B4`. Dark mode: `#8ACAFF` |
| Font | Space Grotesk |
| Widget spacing | 20-pixel margin, left-aligned headers |
| Number format | Money as PHP with compact numbers, such as PHP 6.5T. Percentages with 1 decimal place. Counts with thousands separators |

## Datasets

The canonical export contains 38 datasets. Six unused Lakeview datasets were
removed from the supplied live export because they read Gold facts directly.
Three active support datasets were rewritten against Analytics without changing
their output columns. The exact live export remains in the
[dev-bundle evidence](../docs/evidence/dev-bundle-2026-10-21/README.md#dashboard-export).

| Dataset group | Datasets | Governed sources |
| --- | --- | --- |
| Headline and connection measures | `national_totals`, `data_connections`, `project_mix` | views 3, 4, and 5 |
| Region and province investment | `region_money_by_year`, `province_money_by_year`, `d01_region_budget_by_year`, `d09_region_share_by_year`, `top3_region_share`, `7d88fca9` | view 1 and boundary tables where a map needs geometry |
| Completion and review | `d02_region_completion`, `d03_flagged_by_type_year`, `d05_months_to_complete`, `d10_region_money_vs_completion`, `d12_type_completion_by_year`, `regional_review_by_cohort`, `project_check_list`, `7434c3a7`, `c5574c4d`, `b774fc89` | views 1, 4, and 5 |
| Project type and location | `d04_type_budget_by_year`, `d11_region_type_mix`, `d13_province_type_map`, `6d056075`, `4760d7d1` | views 1, 4, and 5, plus boundary tables for maps |
| Population comparison | `d08_places_left_behind`, `d14_province_per_person_map`, `d15_province_people_vs_money`, `region_budget_per_person_by_year` | views 1, 2, and 5, plus province boundaries |
| Flood alignment | `region_flood_map`, `d06_province_flood_vs_completion`, `d07_region_need_vs_money`, `flood_completion`, `flood_risk_by_region`, `flood_risk_per_project`, `4b45dfd2`, `flood_risk_by_province`, `completion_by_flood_risk`, `flood_budget_by_risk_year` | views 1, 2, 3, and 5, plus boundary tables where a map needs geometry |

Views: 1 `analytics_investment_distribution`, 2 `analytics_population_equity`, 3 `analytics_flood_alignment`, 4 `analytics_implementation_monitoring`, 5 `analytics_infrastructure_network`, 6 `analytics_integration_coverage`.

## Tabs

### Overview

- The business question and the national counters
- Region map, regional budget ranking, and budget by project type
- Project completion by region
- Region and province summary tables

### Where is the money going?

Which regions get the most money, how that changed, and how well each region finishes its projects.

- Budget trend by region, the region-by-year share heat map, and the latest map
- Most-funded and least-funded region, total budget, completion, and top type
- Region ranking, a region filter, and a project-year filter
- Budget by status and flood-risk classification, including a yearly trend

### What are we building?

What kinds of projects get the money, where they are built, how long they take, and how they do in flood-risk areas.

- Project-count, budget, completion, and average-completion counters
- Counts, budgets, and completion by project type and project-year cohort
- Completed, ongoing, and flagged maps by region
- Region-by-type mix, duration comparisons, and completion by flood risk
- Flagged project types by region

### Who are we leaving behind?

Money compared with people and flood risk.

- Population versus budget by province
- Budget per person and total budget maps and rankings for regions and provinces
- Budget per person by flood-risk level
- Provinces and cities to examine first

### Read Me

Page guide, glossary, caveats, BARMM coverage, connection measures, and data
lineage notes.

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
