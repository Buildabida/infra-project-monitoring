# Analytics views

This folder builds the views that the dashboard (#20) and Genie (#21) read. The Analytics layer has **exactly six views**, one per capstone insight ([D-56](../../docs/decisions.md), proposed). One notebook in this folder builds them all, after `09_validation_gold` passes. The views live in `05-analytics`, read governed Gold only, and hold no data of their own.

The views report two governed geographic levels: the official PSGC region and the D-57 province reporting area. The earlier designs are retired: six business-question views (D-50, D-51), five exploratory monitoring views (D-54), a proposed regional progress view (D-55) in a second notebook, and five `analytics_reporting_area_*` views first built for D-57. The notebook now drops those views, and `10_validation_analytics` stops the run if any of them remains.

## Run order

1. `04_validation/09_validation_gold.ipynb` and `04_validation/09a_validation_gold_province_reporting.ipynb` must pass first.
2. Run `01_business_questions.ipynb`. It stops unless current Gold holds exactly one DPWH snapshot. Then it creates `05-analytics` if it does not exist, drops the retired views, and builds the six views with `CREATE OR REPLACE VIEW`.
3. Run `04_validation/10_validation_analytics.ipynb`. It checks the snapshot and both Gold validations again, proves that `05-analytics` holds exactly the six views, rebuilds every view from Gold, and saves its checks to `04-validation.analytics_dq_results` before its STOP gate. See [analytics validation](../../docs/validation.md#analytics-validation).

A rerun replaces the view definitions and updates the same validation rows, so it is safe to run twice. No Databricks job or bundle runs these notebooks yet. `databricks.yml` defines no job, and `run_all.py` coordinates Bronze only.

## The six views

| # | Insight | View | One row per | Gold tables read |
| --- | --- | --- | --- | --- |
| 1 | Where does the money go? | `analytics_investment_distribution` | Geography level (`REGION` or `REPORTING_AREA`), geography key, and `infra_year` cohort | `fact_project_snapshot`, `dim_project`, `dim_region`, `dim_province_reporting_area`, `dim_province_reporting_area_boundary`, `dim_date` |
| 2 | Are investments proportional to population? | `analytics_population_equity` | Province reporting area | `fact_province_reporting_area_population`, plus view 1 |
| 3 | Do flood-control investments overlap with flood-prone areas? | `analytics_flood_alignment` | Official PSGC region and flood point class | `fact_project_snapshot`, `dim_project`, `dim_flood_susceptibility`, `fact_region_flood_exposure`, plus view 1 |
| 4 | Which projects need a closer look? | `analytics_implementation_monitoring` | Current DPWH project | `fact_project_snapshot`, `dim_project`, `dim_region`, `dim_province_reporting_area`, `dim_project_status`, `dim_date` |
| 5 | Are we seeing projects or a connected infrastructure network? | `analytics_infrastructure_network` | Current DPWH project | `fact_project_snapshot`, `dim_project`, `dim_region`, `dim_province_reporting_area`, `dim_project_status`, `dim_flood_susceptibility`, `fact_region_population`, `fact_province_reporting_area_population` |
| 6 | What can we see only after connecting the datasets? | `analytics_integration_coverage` | Integration link, link outcome, and region key | `fact_project_snapshot`, `dim_project`, `dim_project_status`, `dim_region`, `dim_province_reporting_area`, `fact_region_population`, `fact_province_reporting_area_population` |

Every view and column has a comment, so Genie can read what each one means. The dashboard build is in the [dashboard specification](../../dashboard/dashboard_spec.md).

## Rules every view follows

- Reads only `` `03-gold` `` tables, and only current project rows (`is_current_snapshot = TRUE`). Views 2 and 3 also read view 1, so the regional views share one region list and one coverage status.
- Never repeats Silver or Gold work. Region and flood matching, category and status mapping, and the long-running rule come from Gold as published. No view parses geometry or runs a spatial join.
- Budget means the reported project or contract budget, never payment (D-28). A missing budget stays `NULL`. A reported `0` stays `0`.
- An unmapped or unresolved value stays `NULL` or keeps its own status row (D-37). No view writes `Unknown` or `Unmapped`.
- Every view carries `source_snapshot_id` (D-29). View 3 also carries `mgb_source_snapshot_id`.
- Key `0` holds Central Office, unmatched, ambiguous, and unresolved projects at each level. Views 1, 2, and 3 leave it out. Views 4, 5, and 6 keep it, and view 6 accounts for every key `0` project at both levels.
- Every official region and reporting area keeps a row in views 1, 2, and 3. `source_coverage_status` says how far to trust it: `REPORTED`, `LIMITED_SOURCE_COVERAGE` for BARMM and its reporting areas with mapped projects, or `NO_MAPPED_PROJECT_DATA`. Only `REPORTED` members are ranked or compared.

## Geography and time

- **Two levels.** Region comes from `fact_project_snapshot.region_key` (D-31). The province reporting area comes from `fact_project_snapshot.reporting_area_key` (D-57): an official PSGC province, a city with no province parent (`INDEPENDENT_CITY`), or NCR as one area. Silver assigns it once, mostly by the project point inside one province boundary. The DPWH `location.province` field can hold a District Engineering Office name, so it never decides a province.
- **Never add the two levels together, and never derive region totals from provinces.** The levels come from different evidence. About a quarter of projects have a region but no reporting area, and the parent region of a reporting area can differ from the project region. View 5 and view 6 show those conflicts.
- **Boundary gaps.** Independent cities and a few provinces, such as those of the Negros Island Region, have no compatible boundary in the selected boundary file. They cannot receive projects by coordinates, so their zero is a coverage gap. `boundary_status` shows it.
- **Cohorts, not history.** Gold holds one DPWH snapshot. `infra_year` is a project cohort attribute in that snapshot. Write "the 2018 infrastructure-year cohort in the current snapshot", never "DPWH investment in 2018". A newer cohort can hold more active projects simply because its projects started later.

## View contracts

### 1. `analytics_investment_distribution`

- **Business question:** which regions and provinces account for the largest share of recorded investment, and is it concentrated in a few areas or broadly distributed?
- **Grain:** one row per `geography_level`, `geography_key`, and `infra_year` cohort. `geography_level` is `REGION` or `REPORTING_AREA`. A `NULL` cohort keeps its own row (`cohort_row_type = 'NO_INFRA_YEAR'`). A member with no mapped project keeps one row (`NO_MAPPED_PROJECT`). Every project appears once at each level.
- **Measures:** additive `project_count`, `projects_with_budget`, and `total_reported_budget_pesos`, plus the average. Within a level and cohort: `cohort_budget_share_pct`, `cohort_budget_rank`, `cohort_project_count_rank`, and `cohort_cumulative_budget_share_pct`. Over all cohorts, repeated on every cohort row: `geography_project_count`, `geography_budget_pesos`, `geography_budget_share_pct`, `geography_budget_rank`, `geography_project_count_rank`, and `geography_cumulative_budget_share_pct`. Context: `geography_type`, `parent_region_key`, `parent_region_name`, `boundary_status`, and the centroid.
- **Filters:** geography level (single select), `infra_year`, parent region, reporting-area type.
- **Dashboard visual:** a region or province bubble map, a ranking bar chart, a regional rollup table, and a concentration KPI.
- **Interpretation:** the running share at rank 3 reads "the top three hold this percent". It describes where reported budget sits, not need or fairness.
- **Limitations:** key `0` is not in the shares. A `cohort_*` figure is valid only when one level and one cohort are selected. Read `geography_*` columns with `MAX`, never `SUM`. The regional rollup is the `REGION` level, not a sum of reporting areas.
- **Validation:** one row per level, member, and cohort, no key `0`, every count, budget, share, rank, and running share equal to a rebuild from each Gold key, shares adding up to 100 within each level, member columns the same on every cohort row, and each level plus its key `0` adding up to every current project and budget.

### 2. `analytics_population_equity`

- **Business question:** which provinces receive a larger or smaller share of recorded investment than their share of the national population?
- **Grain:** one row per province reporting area.
- **Measures:** `population_count`, `population_share_pct`, `comparable_population_share_pct`, `investment_share_pct`, `share_gap_pp`, `investment_to_population_share_ratio`, `investment_per_capita_pesos`, `investment_per_capita_rank`, and `comparable_set_per_capita_pesos`, with the parent region, `boundary_status`, and `equity_comparison_status`. "National included" means the comparable areas: `REPORTED`, with a budget, and with a population.
- **Filters:** parent region, reporting-area type.
- **Dashboard visual:** scatterplot of population against reported budget, sized by investment per capita, a diverging bar of the share gap, and a per-capita ranking.
- **Interpretation:** a **screening indicator, not a verdict on fairness**. A gap can reflect geography, existing infrastructure gaps, construction costs, who benefits from a project, project type mix, or source coverage.
- **Limitations:** the comparison covers projects with a reporting area only. The view has no "substantially different" flag, because no threshold is approved. Population is the Census Table C barangay population rolled up to reporting areas. Accepted rows that resolve to no area stay on key `0`, outside the view. BARMM provinces stay visible but outside the comparison.
- **Validation:** one row per area, no key `0`, population equal to the newest Gold primary reporting-area population and adding up to it, every share, gap, ratio, and per-capita value equal to Gold, the three share sets adding up to 100, and no ratio on an excluded area.

### 3. `analytics_flood_alignment`

- **Business question:** where are flood-control investments located relative to mapped MGB flood susceptibility?
- **Grain:** one row per official region and flood point class. The classes are the four MGB levels plus `AMBIGUOUS`, `OUTSIDE_MAPPED_ZONES`, `NO_USABLE_POINT`, and `INVALID_SOURCE`. Every region has every class.
- **Measures:** all projects and budget, broad flood-control (`is_dpwh_flood_related`, D-39), strict single-sector flood-control, official flood-list projects, other and uncategorized counts, flood-control shares within the region, and the area and area share of each MGB level with `exposure_area_status`.
- **Filters:** region, flood point class.
- **Dashboard visual:** a layered map that combines the region bubbles with the project points of view 5, stacked bars of flood-control projects and budget by class, and a regional exposure table.
- **Interpretation:** overlap does not prove that a project protects an area or a whole region. A point outside mapped MGB polygons is not low risk.
- **Limitations:** project classes come from one point per project. Level areas may be added within a region only when `exposure_area_status` is `ADDITIVE_WITHIN_TOLERANCE`. Some regions have no safe boundary, so they have no area figures.
- **Validation:** one row per region and class, every project outside key `0` in a published class, flood-control, other, and uncategorized adding up to the row, each region adding up to view 1, areas equal to the newest Gold run and only on level rows, and `NULL` project figures for a region with no mapped project.

### 4. `analytics_implementation_monitoring`

- **Business question:** which recorded projects warrant further verification or follow-up?
- **Grain:** one row per current DPWH project, including key `0`.
- **Measures and fields:** region and province reporting area with its match status, status, standardized status, status group, status reason, `is_for_procurement`, start and completion dates, snapshot date, `physical_progress_pct`, `progress_reporting_status`, `zero_progress_flag`, `long_running_flag`, budget, and five review indicators with `review_reason_count` and `needs_review`.
- **Filters:** `infra_year`, region, province reporting area, sector, implementing office, status group.
- **Dashboard visual:** status distribution, region monitoring bars, drilldown by sector, office, and status, and a project exception table filtered on `needs_review`.
- **Interpretation:** a raised indicator means "verify this record". It never means stalled, delayed, or overdue. Zero reported progress, progress that is not published, `For Procurement`, inactive, and long-running stay separate.
- **Limitations:** **overdue is not built**, because the repo has no trustworthy target completion date and no approved rule (D-40). "Low reported accomplishment" is not a flag, because no threshold is approved. Show `physical_progress_pct` instead. Gold does not say why progress is not published.
- **Validation:** one row per current project, every field and indicator equal to a separate rebuild from Gold, rows and budget equal to Gold, and no `For Procurement` project raising a progress indicator.

### 5. `analytics_infrastructure_network`

- **Business question:** what patterns emerge when projects are seen together rather than one at a time?
- **Grain:** one row per current DPWH project, including key `0`.
- **Measures and fields:** `latitude`, `longitude`, `coordinate_status`, `is_mappable`, a 0.1-degree display cell (`map_grid_latitude`, `map_grid_longitude`), sector, flood flags, `infra_year`, status, budget, `flood_point_class`, region and reporting-area population context, and `region_province_hierarchy_status`.
- **Filters:** sector, `infra_year`, status group, region, province reporting area, flood point class, and map location.
- **Dashboard visual:** an interactive project point map, with a density map on the display cell when there are too many points to draw.
- **Interpretation:** use spatial cluster, corridor pattern, concentration, or gap. Gold has no road or transport topology, so the map **cannot show network connectivity**.
- **Limitations:** about one in five DPWH projects has no map point. A gap on the map can be a project without a point. Region population repeats on every project of a region, so never add it up.
- **Validation:** one row per current project, points equal to Gold, only valid pairs mappable, each mappable point inside its own cell, flood class and population equal to Gold, and rows and budget equal to Gold.

### 6. `analytics_integration_coverage`

- **Business question:** how many project records connect to each governed source, and which cannot?
- **Grain:** one row per integration link, link outcome, and region key. Every current project appears once in each link, so never add rows across links.
- **Links:** `PSGC_REGION`, `PSGC_REPORTING_AREA`, `REGION_PROVINCE_HIERARCHY`, `COORDINATES`, `POPULATION_VIA_REGION`, `POPULATION_VIA_REPORTING_AREA`, `FLOOD_SUSCEPTIBILITY`, `PROJECT_CATEGORY`, `PROJECT_STATUS`, `REPORTED_BUDGET`, and `OFFICIAL_FLOOD_LIST`.
- **Measures:** `project_count`, `projects_with_budget`, `reported_budget_pesos`, `pct_of_link_projects`, `pct_of_link_budget`, and `pct_of_region_projects`, with `is_linked` and `connected_source`.
- **Filters:** integration link, region, `is_linked`.
- **Dashboard visual:** integration KPI cards, an unmatched-record breakdown by outcome, matched against unmatched reported budget, and coverage by region.
- **Interpretation:** this view shows what the pipeline adds: matching, standardization, lineage, and visible data quality. "Not linked" means the governed rules could not connect the record. It does not mean the project is wrong.
- **Limitations:** `OFFICIAL_FLOOD_LIST` is membership, not a quality gap. Most DPWH projects are not flood control.
- **Validation:** one row per link, outcome, and region, exactly eleven links, every link adding up to every current project and budget, region-linked and reporting-area-linked projects equal to Gold, shares equal to Gold and adding up to 100.

## Requests the governed data cannot support

| Request | Status | Why |
| --- | --- | --- |
| Province flood exposure (area per MGB level) | Not built | Deferred by D-57 until a one-time Silver intersection is proven safe and affordable. View 3 stays regional, and view 5 gives the flood class at each project point. |
| Year-over-year portfolio trend | Not built | Gold holds one DPWH snapshot. `infra_year` is a cohort attribute. |
| Overdue projects | Not built | No trustworthy target or contractual completion date and no approved rule (D-40). |
| "Low" accomplishment flag | Not built | No approved threshold. `physical_progress_pct` is shown instead. |
| "Substantially different" equity flag | Not built | No approved threshold. The share gap and ratio are shown and sorted instead. |
| Stalled projects | Not built | Out of scope (D-46). |
| Network connectivity | Not built | Gold has no road or transport topology. The map shows spatial patterns only. |

## Evidence

No Databricks run of the six-view design has been recorded yet. Record it under `docs/evidence/` with its date, run IDs, and results before the dashboard is published. The [retired evidence](../../docs/evidence/analytics-views/README.md) of the eleven-view design stays as history.
