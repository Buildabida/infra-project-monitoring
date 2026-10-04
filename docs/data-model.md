# Data model

Every table lives in the `buildabida-capstone` catalog. Bronze preserves one selected
source snapshot. Silver owns cleaning, reconciliation, matching, and mapping. Gold
contains the facts and dimensions used to answer the project questions.

```text
R2 source snapshots → Bronze → Silver matching and reconciliation → Gold facts/dimensions
                              ↓                                  ↓
                       Bronze validation                  analytical validation
```

## Bronze source contracts

| Table | One row is | Source-grain identity |
| --- | --- | --- |
| `01-bronze.dpwh_projects` | One exported DPWH project row | Contract/project identifier |
| `01-bronze.flood_control_projects` | One exported flood-control feature; repeated Contract IDs remain | Source object identifier |
| `01-bronze.psgc` | One exported PSGC place row | PSGC code |
| `01-bronze.census_2024_table_c` | One exported Table C row, including known BARMM copies | Source file, sheet, and row |
| `01-bronze.boundaries` | One exported geographic shape row | Source file and feature identifier |
| `01-bronze.flood_susceptibility` | One flood area in the approved trimmed MGB extract | Source row; no key is invented |
| `01-bronze.load_log` | One ingestion status event | `run_id`, `status` |
| `04-validation.dq_results` | One data-quality check in one validation run | `run_id`, `table_name`, `column`, `data_quality_check` |

Census Table C is the authoritative population source. PSGC population remains a
cross-check. There is no authoritative generic `01-bronze.population_2024` table.

Every business-source Bronze table adds `_source_system`, `_source_path`,
`_source_file`, `_source_format`, `_source_snapshot_id`, `_ingest_run_id`,
`_ingested_at`, `_source_file_size_bytes`, `_source_modified_ns`, and
`_source_modified_at`.

An optional publisher `source_version` is stored in `load_log`. Silver must carry it
through the row's `_ingest_run_id` when a target table requires a PSGC, boundary, MGB,
or flood-list version.

Business columns remain source strings. The only permitted column-name changes are the
minimum substitutions required by Delta; `load_log.column_mapping_json` records them.

## Silver matching and reconciliation tables

These tables preserve explainable matching decisions that should not be hidden inside
the Gold model.

| Table | Grain | Primary key | Main columns |
| --- | --- | --- | --- |
| `02-silver.silver_dpwh_project_component` | One DPWH component or type-of-work record per contract and ingestion run | `component_key` | `source_system`, `contract_id`, `source_component_id`, `source_infra_type`, `source_type_of_work`, `component_description`, `source_row_number`, `run_id`, `source_load_ts` |
| `02-silver.silver_flood_control_component` | One published flood-control source row | `flood_component_key` | `source_contract_id`, matched project system/contract, `type_of_work`, `component_description`, `source_contract_cost`, `match_status`, `source_row_number`, `source_version`, `run_id`, `source_load_ts` |
| `02-silver.silver_project_region_map` | One project-to-region mapping result per pipeline run | `project_region_map_key` | `source_system`, `contract_id`, `psgc_region_code`, `reported_region_raw`, `mapping_method`, `match_status`, `match_quality`, `boundary_version`, `run_id`, `source_load_ts` |
| `02-silver.silver_project_flood_map` | One final project-to-flood classification per pipeline run | `project_flood_map_key` | `source_system`, `contract_id`, `flood_susceptibility_level`, `severity_rank`, `match_status`, `matched_polygon_count`, `classification_rule`, `mgb_source_version`, `run_id`, `source_load_ts` |
| `02-silver.silver_population_region_reconciliation` | One population source-row reconciliation result per pipeline run | `population_reconciliation_key` | `source_name`, `source_row_number`, `source_sheet`, `source_place_name`, `matched_psgc_code`, `match_status`, `match_method`, `ambiguity_reason`, `is_duplicate_sheet_row`, `is_primary_population_record`, `run_id`, `source_load_ts` |
| `02-silver.config_project_category_mapping` | One approved source category mapping per taxonomy version | Composite natural key | `source_system`, `raw_category`, `source_infra_type`, `standardized_sector`, `mapping_rule`, `taxonomy_version`, approval fields |

Required Silver uniqueness:

- project-region and project-flood maps: `source_system`, `contract_id`, `run_id`;
- DPWH components: `source_system`, `contract_id`, `source_component_id`, `run_id`;
- when no stable component ID exists, use `source_row_number` instead;
- flood-control components: `source_contract_id`, `source_row_number`, `source_version`, `run_id`;
- population reconciliation: `source_name`, `source_sheet`, `source_row_number`, `run_id`;
- category mapping: `source_system`, `raw_category`, `source_infra_type`, `taxonomy_version`.

## Gold fact tables

### `03-gold.fact_project_snapshot`

Grain: one DPWH project per distinct source snapshot.

Primary key: `project_snapshot_key`. Foreign keys: `project_key`, `region_key`,
`status_key`, `flood_susceptibility_key`, `snapshot_date_key`, `start_date_key`, and
`source_completion_date_key`.

Main measures and lineage:

- `reported_budget_pesos DECIMAL(20,2)`;
- `physical_progress_pct DECIMAL(5,2)`;
- `latitude DOUBLE`, `longitude DOUBLE`, and coordinate/match status fields;
- `long_running_flag`, `zero_progress_flag`, and `delivery_rule_version`;
- `source_snapshot_id`, `run_id`, `is_current_snapshot`, and `source_load_ts`.

Uniqueness: `project_key`, `source_snapshot_id`.

### `03-gold.fact_region_population`

Grain: one region per population reference year and source.

Primary key: `region_population_fact_key`. Foreign key: `region_key`. Main columns:
`reference_year`, `population_count`, `source_name`, `is_primary_source`,
`population_match_status`, `source_row_count`, `run_id`, and `source_load_ts`.

Uniqueness: `region_key`, `reference_year`, `source_name`.

### `03-gold.fact_region_flood_exposure`

Grain: one region per susceptibility level, MGB version, and boundary version.

Primary key: `region_flood_exposure_key`. Foreign keys: `region_key` and
`flood_susceptibility_key`. Measures and lineage: `susceptible_area_sqkm`,
`share_of_region_area_pct`, `source_polygon_count`, `mgb_source_version`,
`boundary_version`, `spatial_match_status`, `area_calculation_crs`,
`area_rule_version`, `run_id`, and `source_load_ts`.

Uniqueness: `region_key`, `flood_susceptibility_key`, `mgb_source_version`,
`boundary_version`.

## Gold dimensions

| Dimension | Grain and key | Main columns |
| --- | --- | --- |
| `03-gold.dim_date` | One row per calendar date; `date_key` | `calendar_date`, year, quarter, month, and day fields |
| `03-gold.dim_project` | One unique contract per source system; `project_key` | `contract_id`, descriptions/categories, standardized sector, mapping status/version, flood-list flags/version, funding source, office, contractor, infrastructure year, lineage |
| `03-gold.dim_region` | One official PSGC region per PSGC version plus key `0`; `region_key` | PSGC code, names, version, BARMM/geographic flags, centroid, lineage |
| `03-gold.dim_project_status` | One source-status mapping per version; `status_key` | source and standardized status, group, mapping version, source system, active flag, lineage |
| `03-gold.dim_flood_susceptibility` | One susceptibility classification per source version; `flood_susceptibility_key` | level, severity rank, source system/version, lineage |
| `03-gold.dim_region_boundary` | One boundary version per official region; `boundary_key` | `region_key`, geometry, version, CRS, validity and PSGC-match status, source system, lineage |

Dimension uniqueness:

- `dim_date`: `calendar_date`;
- `dim_project`: `source_system`, `contract_id`;
- `dim_region`: `psgc_region_code`, `psgc_version`;
- `dim_project_status`: `source_system`, `source_status`, `status_mapping_version`;
- `dim_flood_susceptibility`: `source_system`, `flood_susceptibility_level`, `source_version`;
- `dim_region_boundary`: `region_key`, `boundary_version`.

## Six-source lineage

| Source | Downstream destination |
| --- | --- |
| DPWH projects | DPWH component mapping, category mapping, project/status dimensions, and project snapshot fact |
| Flood-control list | Flood-control components and official flood-list flags on projects |
| PSGC | Region dimension and population reconciliation |
| PSA Table C | Population reconciliation and region population fact |
| BetterGov boundaries | Region boundary dimension, project-region mapping, and regional flood intersection |
| MGB flood susceptibility | Project-flood mapping, susceptibility dimension, and region flood exposure fact |

## Join rules

- `fact_project_snapshot.project_key` joins to `dim_project.project_key`.
- `fact_project_snapshot.region_key` joins to `dim_region.region_key`.
- Status, susceptibility, and date keys join to their corresponding dimensions.
- Population and flood-exposure facts join to `dim_region` through `region_key`.
- Silver mapping tables retain the run, method, quality, and source version used to
  produce every Gold key.
- Key `0` is reserved for unknown, unmapped, or non-geographic records. Central Office
  uses region key `0` with `region_match_status = 'Non-geographic reporting unit'`.

## Required analytical validation

1. At most one `is_current_snapshot = true` row exists per `project_key`.
2. Physical progress is between 0 and 100 or null.
3. Reported budget is non-negative or null.
4. Flood-exposure area is non-negative and its regional share is between 0 and 100.
5. Primary population is positive, with exactly one primary source per region and year.
6. Central Office is excluded from population-based ratios.
7. MGB classifications include Unknown, Low, Moderate, High, and Very High.
8. Severity rank is unique within source system and version.
9. `source_snapshot_id` is not null and all fact foreign keys resolve.
10. Spatial areas are calculated in an appropriate projected CRS, not square degrees.

## Business-question coverage

| Analysis | Main tables | Interpretation boundary |
| --- | --- | --- |
| Regional investment concentration | `fact_project_snapshot` + `dim_region` | Use reported budgets; show coordinate and match coverage. |
| Infrastructure portfolio/categories | `fact_project_snapshot` + `dim_project` | Category rules are versioned and explainable. |
| Project delivery and status | Project fact + status/date/region dimensions | Use long-running or zero-progress rules, not unsupported claims that a project is delayed. |
| Investment relative to population | Project fact + region population fact + region dimension | Describe allocation differences, not fairness; exclude non-geographic Central Office. |
| Flood-control alignment | Project fact + project/susceptibility dimensions + flood-exposure/population facts + region | Report comparative patterns, not proof of insufficient protection or causation. |

The available need proxies are population and flood-risk exposure. They do not represent
every form of infrastructure need. Reported budgets and contract costs are not actual
payments or disbursements.

## Bronze preservation boundary

Bronze does not clean names, cast business types, map places, deduplicate source rows,
standardize categories, calculate measures, or perform spatial joins. These decisions
begin in Silver and remain traceable through source snapshot IDs, run IDs, mapping
statuses, rule versions, and source versions.
