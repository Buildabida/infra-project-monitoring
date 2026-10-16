# Dashboard specification

This spec describes the capstone dashboard as built on October 16, 2026. The exported file is [`buildabida_infrastructure_project_monitoring.lvdash.json`](buildabida_infrastructure_project_monitoring.lvdash.json). The dashboard is written for citizens: every title, note, and label uses plain words.

It has seven tabs: an overview, then one tab per capstone insight. The tab name is the insight question. The view contracts are in the [Analytics views guide](../notebooks/05_analytics/README.md).

Build or refresh it only after `10_validation_analytics` passes. The `business_dashboard` task of the [pipeline job](../resources/buildabida_full_pipeline.job.yml) runs after that gate.

## Data rules

- Every dataset reads only the six views in `` `buildabida-capstone`.`05-analytics` ``. The two map datasets also read the Gold boundary tables `dim_region_boundary` and `dim_province_reporting_area_boundary`, for map shapes only.
- No dataset reads Silver, Bronze, or any table that is not listed here.
- No dataset creates an object in Unity Catalog. `05-analytics` holds only the six views.
- A missing value shows as "No data", never as 0.
- Never add up columns that repeat on many rows: `geography_project_count`, `geography_budget_pesos`, `geography_budget_share_pct`, the population columns of view 5, `physical_progress_pct`, and every rank. Read them with `MAX`.
- In `analytics_investment_distribution`, always filter one `geography_level`. Never add regions and provinces together.
- Do not use a hyphen in a dataset name. The dashboard turns the name into an entity name, and a hyphen breaks the widget queries.

## Theme

| Setting | Value |
| --- | --- |
| Colors | Violet only, light to dark: `#F5F3FF`, `#EDE9FE`, `#DDD6FE`, `#C4B5FD`, `#A78BFA`, `#8B5CF6`, `#7C3AED`, `#6D28D9`, `#5B21B6`, `#4C1D95`. Light gray `#D1D5DB` only for "No data" and "Outside the mapped flood areas". |
| Canvas background | `#FAF9FF` |
| Widget background | `#FFFFFF` |
| Widget outline | `#C4B5FD` |
| Text | `#2E1065` |
| Maps | Custom sequential scale from `#DDD6FE` or `#F5F3FF` (low) to `#4C1D95` (high). Named color schemes are not used. |
| Number format | Money as PHP with compact numbers, such as PHP 6.5T. Percentages with 1 decimal place. Counts with thousands separators. |

Every page ends with this note: "Budgets are the amounts written in DPWH project records. They are not actual payments. Data as of the DPWH file dated October 4, 2026."

## Datasets

| Dataset | Reads | Used on |
| --- | --- | --- |
| National Totals | views 3 and 4 | Overview KPIs |
| Region Scorecard | views 1, 3, 4, and 6, one row per region | Overview charts and table |
| Region Scorecard Look First | Region Scorecard SQL, sorted by the share of projects to check | Tab 7 table |
| Region Money by Year | view 1 at `REGION` level, with region boundaries | Overview map, Tab 2 |
| Province Money by Year | view 1 at `REPORTING_AREA` level, with province boundaries | Tab 2 |
| Top 3 Region Share | view 1, `MAX(geography_cumulative_budget_share_pct)` where `geography_budget_rank = 3` | Tab 2 KPI |
| Money and Population | view 2 | Tab 3 |
| Flood Risk by Region | view 3 | Tab 4 |
| Region Flood Map | view 3, with region boundaries | Tab 4 map |
| Flood Control Project Points | view 5, flood-control projects with a valid point | Tab 4 point map |
| Project Check List | view 4, every current project | Tab 5 |
| Project Map Cells | view 5, mappable projects grouped by 0.1-degree cell, region, province, type, year, status, and flood risk | Tab 6 map |
| Project Mix | view 5, every current project grouped by region, province, type, year, and status | Tab 6 charts |
| Data Connections | view 6 | Tab 7 |

## Tabs

### 1. Overview: What did we find?

KPIs: projects in the records, total budget in the records, projects worth a closer look, projects placed in a province or city, and flood-control projects in high or very high flood areas. Region map of the budget over all years, the top 10 regions by budget, the share of projects worth a closer look by region, and a region summary table.

### 2. Where does the money go? (insight 1)

Filters: year (2016 to 2026, and "No year given") and region. KPIs: budget and projects in the selected years, and the share held by the top three regions over all years. Region and province maps, the region ranking, the top 15 provinces and cities, and the budget year after year.

The year is the infrastructure year on each project record. It groups projects. It is not the amount paid in that year. The tab counts projects placed in a region, so its totals leave out the 572 projects with no region.

### 3. Does the money match where people live? (insight 2)

Filter: region. KPIs: provinces and cities compared, national budget per person, and highest budget per person. A scatter plot of people against budget for the compared provinces and cities, sized by budget per person and colored by whether the share of money is bigger or smaller than the share of people. Top 10 bigger and smaller shares, budget per person, and a table of the places not compared.

This is a first look, not a fairness verdict. No threshold for a "substantial" difference is approved.

### 4. Are flood-control projects where the floods are? (insight 3)

Filter: region. KPIs: flood-control projects, how many are in high or very high flood risk areas, and their budget. A region map of the share of flood-control budget in high risk areas, a point map of flood-control projects colored by flood risk, projects by flood risk per region, and budget by flood risk level.

A project inside a flood risk area does not prove it protects that area. Flood area is never added across levels, because the levels overlap in most regions.

### 5. Which projects need a closer look? (insight 4)

Filters: region, province or city, project type, year, and status. KPIs: projects to check and their share, their budget and its share, ongoing but zero progress, ongoing for a long time, and status not clear in the record. Status by region, reasons to check, projects to check by region and by province or city, budget by region, and the project list.

Only the project list and the "to check" counts filter on `needs_review`. Shares divide by all projects in the current filter. No overdue flag exists, because the records have no official target end date.

### 6. What patterns show when we map all projects? (insight 5)

Filters: project type, year, status, region, province or city, and flood risk (map only). KPIs: projects, budget, and kinds of projects. A cluster map of 0.1-degree cells, project types year after year, a region by type heatmap, and the top 15 provinces and cities by number of projects.

The map shows where projects cluster, not road or transport connections. Projects without a usable location are counted in the charts but not on the map.

### 7. What can we see only after connecting the data? (insight 6)

Filter: region. KPIs: placed in an official region, placed in a province or city, has a usable map location, and placed on the flood risk map. How much we could connect per link, why some records could not be connected, the "Where to look first, by region" table, and a "What we learned" summary without invented numbers.

"Where to look first" is a guide for follow-up, not a performance ranking.

## Check values

With no filter selected, on the October 16, 2026 data:

| Tab | Widget | Value |
| --- | --- | --- |
| 1 | Projects in the records | 265,656 |
| 1 | Total budget in the records | PHP 6.5T |
| 1 | Projects worth a closer look | 16,178 |
| 1 | Projects placed in a province or city | 75.3% |
| 1 | Flood-control projects in high or very high flood areas | 52.4% |
| 2 | Projects in selected years | 265,084 |
| 2 | Share held by the top 3 regions | 28.8% |
| 3 | Provinces and cities compared | 74 |
| 3 | National budget per person | PHP 58.8K |
| 4 | Flood-control projects | 34,967 |
| 4 | In high or very high flood risk areas | 18,335 |
| 4 | Budget in high or very high flood risk areas | PHP 1.0T |
| 5 | Share of all projects to check | 6.1% |
| 5 | Status not clear in the record | 102 |
| 6 | Projects on the map | 215,138 |
| 7 | Placed in an official region | 99.8% |
| 7 | Has a usable map location | 81.0% |
| 7 | Placed on the flood risk map | 42.4% |

If a widget shows another number with no filter, it is adding the wrong rows.

## Known gaps

- The Global Filters page still holds the old "Source Coverage Status" filter, bound to Region Scorecard. Delete it in the workspace and export again.
- The intro and note of tab 3 still describe a comparison by region. The charts compare provinces and cities. Fix the text in the workspace and export again.
- The table widget cannot shade cells, so the percent columns of the tab 7 table have no color scale.

## Genie

Point the Genie space at the six views only. Their table and column comments carry the rules on this page. Add these instructions to the space:

- Answer at region or province level. Province means the governed reporting area. Never add the two levels together, and never sum provinces to get a region.
- Treat `infra_year` as a cohort in the current snapshot.
- Never call a project overdue, delayed, or stalled. Never call a region underfunded or a project network connected.
- Never add `region_*` columns of `analytics_investment_distribution` or rows across links of `analytics_integration_coverage`.
