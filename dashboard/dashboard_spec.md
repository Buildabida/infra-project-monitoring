# Dashboard build specification

This spec tells you how to build the capstone dashboard in Databricks AI/BI from the six Analytics views. The dashboard has six pages, one per insight. Every dataset reads one view in `` `buildabida-capstone`.`05-analytics` `` and nothing else. The view contracts are in the [Analytics views guide](../notebooks/05_analytics/README.md).

Build the dashboard only after `10_validation_analytics` passes. Then export it here, as the [dashboard README](README.md) says.

## Datasets

Create one dataset per row of this table. Each dataset is `SELECT * FROM` its view, with the filter shown. Two datasets read the same view when a page needs one figure that the cohort filter must not touch.

| Dataset | View | Filter in the dataset | Used on |
| --- | --- | --- | --- |
| `ds_investment_cohorts` | `analytics_investment_distribution` | None. Bind the geography level selector to it. | Page 1 |
| `ds_investment_members` | `analytics_investment_distribution` | None. Bind the geography level selector. Never bind the cohort filter. | Page 1 |
| `ds_investment_regions` | `analytics_investment_distribution` | `WHERE geography_level = 'REGION'`. Never bind the cohort filter. | Page 1 regional rollup |
| `ds_population_equity` | `analytics_population_equity` | None | Page 2 |
| `ds_flood_alignment` | `analytics_flood_alignment` | None | Page 3 |
| `ds_projects_monitoring` | `analytics_implementation_monitoring` | None | Page 4 |
| `ds_projects_network` | `analytics_infrastructure_network` | None | Pages 3 and 5 |
| `ds_integration` | `analytics_integration_coverage` | None | Page 6 |

## Shared filters

Bind a filter only to a dataset that has its field. Never bind a filter to a view without that field.

| Filter | Field | Datasets it binds to | Not bound to |
| --- | --- | --- | --- |
| Geography level | `geography_level` | `ds_investment_cohorts`, `ds_investment_members`. Single select, default `REPORTING_AREA`. Labels "Region" and "Province". | The others |
| Infrastructure-year cohort | `infra_year` | `ds_investment_cohorts`, `ds_projects_monitoring`, `ds_projects_network` | `ds_investment_members`, `ds_investment_regions`, `ds_population_equity`, `ds_flood_alignment`, `ds_integration` |
| Region | `parent_region_name` on view 1, `region_name` elsewhere | All datasets | None |
| Province (reporting area) | `geography_name` on view 1 when the level is `REPORTING_AREA`, `reporting_area_name` elsewhere | `ds_investment_cohorts`, `ds_investment_members`, `ds_population_equity`, `ds_projects_monitoring`, `ds_projects_network` | `ds_investment_regions`, `ds_flood_alignment`, `ds_integration`. Those views have no province field. |
| Sector or project type | `standardized_sector` | `ds_projects_monitoring`, `ds_projects_network` | The geographic and integration datasets |
| Status | `status_group` | `ds_projects_monitoring`, `ds_projects_network` | The geographic and integration datasets |
| Flood point class | `flood_point_class` | `ds_flood_alignment`, `ds_projects_network` | The others |
| Integration link | `integration_link` | `ds_integration` | The others. Make it single-select. |

The province filter lists reporting areas from Gold: official provinces, independent cities, and NCR as one area (D-57). Never type a province list into the dashboard.

Label the cohort filter **"Infrastructure-year cohort (current snapshot)"**. Show a `NULL` year as **"No year in source"**, a `NULL` sector as **"Not categorized"**, a `NULL` status group as **"Status not mapped"**, and reporting area key `0` as **"No province assigned"**. Set these labels in the widget. Never write them into the data.

## Footer on every page

> Reported project or contract budget from the DPWH snapshot of `snapshot_date` (`source_snapshot_id`). Budget is not payment or disbursement. Province means the governed reporting area: an official province, an independent city, or NCR as one area. About a quarter of projects have no province assigned. `infra_year` is a cohort of projects as they look in this snapshot, not the DPWH portfolio in that year. BARMM has limited DPWH project coverage in the source.

## Page 1. Where does the money go?

Story question: are infrastructure investments geographically concentrated, or broadly distributed?

The geography level selector switches every visual on this page between regions and provinces. The level is always a single select, because every project appears once at each level.

| Visual | Type | Dataset | Fields |
| --- | --- | --- | --- |
| Investment by province or region | Point (bubble) map | `ds_investment_cohorts` | Latitude `centroid_latitude`, longitude `centroid_longitude`, size `SUM(total_reported_budget_pesos)`, color `source_coverage_status`. Tooltip: `geography_name`, `geography_type`, `parent_region_name`, `SUM(project_count)`, `SUM(total_reported_budget_pesos)`, `MAX(boundary_status)`. |
| Investment ranking | Horizontal bar | `ds_investment_cohorts` | Y `geography_short_name`, X `SUM(total_reported_budget_pesos)`, sorted descending, top 20 at province level. Color `source_coverage_status`. Tooltip: `parent_region_name`, `SUM(project_count)`, `SUM(projects_with_budget)`. |
| Projects by province or region | Horizontal bar | `ds_investment_cohorts` | Y `geography_short_name`, X `SUM(project_count)`, sorted descending. |
| Regional rollup | Table | `ds_investment_regions` | Rows `geography_name`, columns `MAX(geography_project_count)`, `MAX(geography_budget_pesos)`, `MAX(geography_budget_share_pct)`, `MAX(geography_budget_rank)`. Region totals come from the region level, never from adding provinces. |
| Top-three concentration | Counter | `ds_investment_members` | `MAX(geography_cumulative_budget_share_pct)` where `geography_budget_rank <= 3`. Title "Share of reported budget in the top three, all cohorts". |
| Cohort concentration | Table | `ds_investment_cohorts` | Rows `geography_name`, columns `cohort_budget_rank`, `cohort_budget_share_pct`, `cohort_cumulative_budget_share_pct`. Show only when one cohort is selected. |

KPI definitions:

- **Reported budget** is `SUM(total_reported_budget_pesos)` over the filtered rows of one level.
- **Top-three concentration** is the running share of the three highest `REPORTED` members of the selected level over all cohorts.

Footnotes:

- A `cohort_*` column is valid only when one level and one cohort are selected.
- Projects on key `0` are not in this page. At region level they are Central Office, unmatched, and ambiguous projects. At province level they also include projects with a region but no province. Page 6 shows both.
- A province with `boundary_status` other than `VALID_BOUNDARY`, such as an independent city, cannot receive projects by map point. Show it as "no province boundary in the source", never as zero investment.
- Some members have no centroid because Gold has no safe boundary for them. They appear in the bars but not on the map.

Caveats: never write "DPWH investment in 2018". Write "the 2018 infrastructure-year cohort in the current snapshot". BARMM and its provinces have limited DPWH project coverage, never low or zero investment.

## Page 2. Are investments proportional to population?

Story question: which provinces receive a relatively larger or smaller investment share compared with their population share?

| Visual | Type | Dataset | Fields |
| --- | --- | --- | --- |
| Population and reported investment | Scatter | `ds_population_equity` | X `population_count`, Y `total_reported_budget_pesos`, size `investment_per_capita_pesos`, color `region_name`, label `reporting_area_short_name`. Reference line slope `comparable_set_per_capita_pesos`. Tooltip: `reporting_area_type`, `population_share_pct`, `investment_share_pct`, `share_gap_pp`, `equity_comparison_status`. |
| Investment share against population share | Grouped bar | `ds_population_equity` | Y `reporting_area_short_name`, bars `investment_share_pct` and `comparable_population_share_pct`. |
| Share gap | Diverging bar | `ds_population_equity` | Y `reporting_area_short_name`, X `share_gap_pp`, sorted, showing the 10 highest and 10 lowest. Tooltip `investment_to_population_share_ratio`, `region_name`. |
| Investment per person | Horizontal bar | `ds_population_equity` | Y `reporting_area_short_name`, X `investment_per_capita_pesos`, sorted by `investment_per_capita_rank`. |
| Provinces outside the comparison | Table | `ds_population_equity` | `reporting_area_name`, `region_name`, `equity_comparison_status`, `boundary_status`, `population_count`. |

KPI definitions:

- **Investment share** is the province's budget over the budget of the comparable provinces, the national included investment.
- **Comparable population share** is the province's population over the population of the same comparable provinces, the national included population.
- **Share gap** is investment share minus comparable population share, in percentage points.

Required on-page note:

> This is a screening indicator, not a verdict on fairness. A difference can reflect geography, existing infrastructure gaps, construction costs, who benefits from a project, project type mix, and source coverage. Projects with no province assigned are not in this comparison.

Caveats: do not label any province "underfunded" or "overfunded". No threshold for "substantially different" is approved, so sort by the gap and highlight the extremes instead of flagging.

## Page 3. Do flood-control investments overlap with flood-prone areas?

Story question: where are flood-control investments located relative to mapped flood exposure?

| Visual | Type | Dataset | Fields |
| --- | --- | --- | --- |
| Flood-control projects and MGB levels | Point map, layered | `ds_projects_network` | Points where `is_mappable` and `is_dpwh_flood_related`. Color `flood_point_class`. Tooltip: `contract_id`, `project_description`, `reported_budget_pesos`, `status_group`. |
| Flood-control projects by class | Stacked bar | `ds_flood_alignment` | X `flood_point_class` ordered by `severity_rank`, Y `SUM(flood_control_project_count)`. |
| Flood-control budget by class | Stacked bar | `ds_flood_alignment` | X `flood_point_class`, Y `SUM(flood_control_budget_pesos)`. |
| Flood-related KPIs | Counters | `ds_flood_alignment` | `SUM(flood_control_project_count)`, `SUM(flood_control_budget_pesos)`, `SUM(official_flood_list_project_count)`. |
| Regional exposure | Table | `ds_flood_alignment` | Rows `region_name`, columns per level `susceptible_area_sqkm` and `share_of_region_area_pct`, plus `exposure_area_status`. |

KPI definitions:

- **Flood-control projects** use the broad DPWH flag (D-39), which includes Multi-sector projects with a flood component. Show the strict single-sector count `flood_control_single_sector_project_count` beside it.
- **In a mapped level** is the sum over the four MGB level rows. `AMBIGUOUS`, `OUTSIDE_MAPPED_ZONES`, `NO_USABLE_POINT`, and `INVALID_SOURCE` stay visible as their own bars.

Footnotes:

- A project outside mapped MGB polygons is not low risk. MGB has no polygon there.
- Add level areas within a region only when `exposure_area_status` is `ADDITIVE_WITHIN_TOLERANCE`.

Province: Gold has MGB flood area per region only, so the class bars and exposure table stay regional. Province flood exposure is deferred (D-57). The layered map can filter to one province through `ds_projects_network`.

Caveats: overlap does not prove that a project protects the area, or a whole region. Never draw MGB polygons from the dashboard. The flood class already comes from the Silver spatial match.

## Page 4. Which projects need a closer look?

Story question: which recorded projects warrant further verification or follow-up?

| Visual | Type | Dataset | Fields |
| --- | --- | --- | --- |
| Status distribution | Bar | `ds_projects_monitoring` | X `status_group`, Y `COUNT(project_key)`. Color `status_mapping_status`. |
| Review indicators by region | Stacked bar | `ds_projects_monitoring` | Y `region_short_name`, X counts of each `review_*` column that is true. |
| Review indicators by province | Stacked bar | `ds_projects_monitoring` | Y `reporting_area_name`, X counts of each `review_*` column that is true. Show key `0` as "No province assigned". |
| Drilldown | Pivot | `ds_projects_monitoring` | Rows `standardized_sector`, `implementing_office`, `status_group`. Values `COUNT(project_key)`, `COUNT_IF(needs_review)`. |
| Exception table | Table | `ds_projects_monitoring` | Filter `needs_review = TRUE`. Columns `contract_id`, `project_description`, `region_name`, `reporting_area_name`, `implementing_office`, `status_group`, `source_status`, `start_date`, `source_completion_date`, `physical_progress_pct`, `progress_reporting_status`, `long_running_flag`, the five `review_*` columns, `reported_budget_pesos`. Sort by `review_reason_count` descending. |

KPI definitions:

- **Projects to verify** is `COUNT_IF(needs_review)`.
- **Active with zero reported progress** is `COUNT_IF(review_active_zero_progress)`. It excludes `For Procurement`.
- **Active and long-running** is `COUNT_IF(review_active_long_running)`, Gold's D-32 flag.

Required on-page note:

> A raised indicator means "verify this record". It is not a finding that work is stalled, delayed, or overdue. Zero reported progress, progress not published, For Procurement, inactive, and long-running are different states.

Caveats: there is no overdue measure, because DPWH gives no trustworthy target completion date. Never call a project stalled (D-46). `source_completion_date` is the date DPWH published, not a deadline.

## Page 5. Are we seeing projects or a connected infrastructure network?

Story question: what patterns emerge when we stop looking at each project in isolation?

| Visual | Type | Dataset | Fields |
| --- | --- | --- | --- |
| Project map | Point map | `ds_projects_network` | Filter `is_mappable = TRUE`. Latitude `latitude`, longitude `longitude`, color `standardized_sector` (switchable to `status_group` or `flood_point_class`), size `reported_budget_pesos`. Tooltip: `contract_id`, `project_description`, `region_name`, `reporting_area_name`, `infra_year`, `status_group`, `flood_point_class`, `region_population_count`, `reporting_area_population_count`. |
| Project density | Heatmap or point map | `ds_projects_network` | Group by `map_grid_latitude`, `map_grid_longitude`. Size `COUNT(project_key)`, color `SUM(reported_budget_pesos)`. Use it when the point map hits the visual row limit. |
| Projects without a map point | Counter | `ds_projects_network` | `COUNT_IF(NOT is_mappable)`, with `COUNT(project_key)` as the total. |

Footnotes:

- About one in five DPWH projects has no map point. A gap can be a place with no recorded project, or a project without a point.
- Region and province population are context. They repeat on every project of the area, so never add them up.
- `region_province_hierarchy_status = 'CONFLICT'` marks a project whose region and province come from different evidence. Show it in the tooltip, never hide it.

Caveats: use the words spatial cluster, corridor pattern, concentration, and gap. Gold has no road or transport topology, so never claim connected infrastructure or network connectivity.

## Page 6. What can we see only after connecting the datasets?

Story question: how much more can we understand after connecting previously separate sources?

| Visual | Type | Dataset | Fields |
| --- | --- | --- | --- |
| Integration coverage | Counter per link | `ds_integration` | For each `integration_link`: `SUM(project_count)` where `is_linked`, and `SUM(pct_of_link_projects)` where `is_linked`. |
| Total current projects | Counter | `ds_integration` | `SUM(project_count)` where `integration_link = 'PSGC_REGION'`. Any single link gives the same total. |
| Unmatched breakdown | Bar | `ds_integration` | Link filter set to one link. X `link_outcome`, Y `SUM(project_count)`, color `is_linked`. |
| Matched and unmatched budget | Stacked bar | `ds_integration` | X `integration_link`, Y `SUM(reported_budget_pesos)`, color `is_linked`. |
| Coverage by region | Heatmap | `ds_integration` | Rows `region_name`, columns `integration_link`, value `SUM(pct_of_region_projects)` where `is_linked`. |

KPI definitions (each is the linked rows of one link):

| KPI | `integration_link` |
| --- | --- |
| Projects mapped to an official PSGC region | `PSGC_REGION` |
| Projects mapped to a province reporting area | `PSGC_REPORTING_AREA` |
| Projects whose region and province agree | `REGION_PROVINCE_HIERARCHY` (`CONFLICT` and `NOT_EVALUATED` show in the breakdown) |
| Projects with valid coordinates | `COORDINATES` |
| Projects linked to population through their region | `POPULATION_VIA_REGION` |
| Projects linked to population through their province | `POPULATION_VIA_REPORTING_AREA` |
| Projects with one MGB flood level | `FLOOD_SUSCEPTIBILITY` (`AMBIGUOUS` and the unavailable outcomes show in the breakdown) |
| Projects with a governed category | `PROJECT_CATEGORY` |
| Projects with a governed status | `PROJECT_STATUS` |
| Projects with a reported budget | `REPORTED_BUDGET` |
| Projects in the official flood-control list | `OFFICIAL_FLOOD_LIST` |

Footnotes:

- Every project appears once in each link. Never add rows across links.
- A missing budget is never counted as 0. `reported_budget_pesos` is `NULL` for a row with no reported budget.

Caveats: "not linked" means the governed rules could not connect the record. It does not mean the project is wrong. The official flood list is membership, not a quality gap.

## Genie

Point the Genie space at the six views only. Their table and column comments carry the rules on this page. Add these instructions to the space:

- Answer at region or province level. Province means the governed reporting area. Never add the two levels together, and never sum provinces to get a region.
- Treat `infra_year` as a cohort in the current snapshot.
- Never call a project overdue, delayed, or stalled. Never call a region underfunded or a project network connected.
- Never add `region_*` columns of `analytics_investment_distribution` or rows across links of `analytics_integration_coverage`.
