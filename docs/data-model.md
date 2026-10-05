# Data model

Every table lives in the `buildabida-capstone` catalog.
Bronze preserves one selected source snapshot.
Silver owns cleaning, reconciliation, matching, and mapping.
Gold contains the facts and dimensions used to answer the project questions.

## Implementation status

| Layer | Status | Meaning |
| --- | --- | --- |
| Bronze | Implemented | The six source tables, `load_log`, and Bronze validation results exist. |
| Silver | Partially implemented | Five governed configuration tables and three geography and population outputs exist. Other transformations remain planned. |
| Gold | Planned | The facts and dimensions below are design targets. They are not implemented yet. |

```text
R2 source snapshots → Bronze → Silver matching and reconciliation → Gold facts/dimensions
                      ↓                    ↓                         ↓
                 04-validation shared results for Bronze, Silver, and Gold
```

## Bronze source contracts (implemented)

| Table | One row is | Source-grain identity |
| --- | --- | --- |
| `01-bronze.dpwh_projects` | One exported DPWH project row | Contract or project identifier |
| `01-bronze.flood_control_projects` | One exported flood-control feature. Repeated Contract IDs remain. | Source object identifier |
| `01-bronze.psgc` | One exported PSGC place row | PSGC code |
| `01-bronze.census_2024_table_c` | One exported Table C row, including known BARMM copies | Source file, sheet, and row |
| `01-bronze.boundaries` | One exported geographic shape row | Source file and feature identifier |
| `01-bronze.flood_susceptibility` | One flood area in the approved trimmed MGB extract | Source row. No key is invented. |
| `01-bronze.load_log` | One ingestion status event | `run_id`, `status` |
| `04-validation.dq_results` | One data-quality check in one validation run | `run_id`, `table_name`, `column`, `data_quality_check` |

The Bronze result schema remains Bronze-only. Silver configuration checks use
`04-validation.silver_config_dq_results`. Silver transformation checks use
`04-validation.silver_dq_results`. Separate result tables avoid breaking fixed writers.
Silver results retain their source layer, snapshots, and rule versions.

Census Table C is the authoritative population source.
PSGC population remains a cross-check.
There is no authoritative generic `01-bronze.population_2024` table.

Every business-source Bronze table adds these technical fields:

- `_source_system`
- `_source_path`
- `_source_file`
- `_source_format`
- `_source_snapshot_id`
- `_ingest_run_id`
- `_ingested_at`
- `_source_file_size_bytes`
- `_source_modified_ns`
- `_source_modified_at`

An optional publisher `source_version` is stored in `load_log`.
Silver must carry it through `_ingest_run_id` when a target requires a source version.
This applies to PSGC, boundary, MGB, and flood-list versions.

Business columns remain source strings.
Only the minimum column-name substitutions required by Delta are permitted.
`load_log.column_mapping_json` records those changes.

## Silver configuration tables (implemented)

These five small Delta tables govern mappings used by later Silver transformations.
Only active `APPROVED` rows may drive downstream standardization or matching.

| Table | Grain | Natural key |
| --- | --- | --- |
| `02-silver.config_place_name_alias` | One context-specific source alias per alias version | Source system, raw place and context fields, place type, alias version |
| `02-silver.config_project_category_mapping` | One source category and infrastructure-type pair per taxonomy version | Source system, raw category, source infrastructure type, taxonomy version |
| `02-silver.config_project_status_mapping` | One source status per mapping version | Source system, source status, status mapping version |
| `02-silver.config_mgb_susceptibility_mapping` | One raw MGB code per source-contract and mapping version | Source system, raw code, source version, mapping version |
| `02-silver.config_manual_geographic_match` | One source-record override per mapping version | Source system, record type, source record ID, mapping version |

Every table records an approval status, version, active flag, and review evidence.
The approved MGB seed maps `LF`, `MF`, `HF`, and `VHF` to the documented levels.
Other tables begin empty until reviewers approve source-specific rules.

See [Silver configuration mappings](silver_config_mappings.md) for the field contracts,
approval workflow, validation rules, and current limits.

## Silver geography and population tables (implemented)

Place-level matching and region-level aggregation have different grains.
The approved population path is:

```text
01-bronze.psgc → silver_psgc_place
                         ↓
01-bronze.census_2024_table_c + config_place_name_alias
                         ↓
       silver_population_place_reconciliation
                         ↓
              silver_region_population
                         ↓
       03-gold.fact_region_population (planned)
```

The earlier single population-reconciliation design is retired.
It combined source-row reconciliation and region aggregation into one unclear contract.

| Table | Grain | Natural key | Main columns |
| --- | --- | --- | --- |
| `02-silver.silver_psgc_place` | One official PSGC place per selected PSGC version or snapshot | `psgc_code`, then `psgc_version` or `source_snapshot_id` | Raw and standardized name, place type, official hierarchy, PSGC population cross-check, snapshots, ingest run, Silver run, hierarchy status, rule version |
| `02-silver.silver_population_place_reconciliation` | One current Table C source-row result per Silver run | `source_file`, `sheet_name`, `source_row_number`, `run_id` | Raw and parsed population, matched PSGC place, method, status, quality, candidate count, final disposition, cross-check, snapshots, versions, lineage |
| `02-silver.silver_region_population` | One official PSGC region per reference year, source, and selected snapshots | `psgc_region_code`, `reference_year`, `source_name`, Table C snapshot, PSGC snapshot | Table C population, contributing rows, reference date, primary-source status, snapshots, ingest runs, alias and rule versions |

Only positive `ACCEPTED_PRIMARY` matched barangay rows contribute to region population.
Higher-level Table C subtotals remain reconciled but do not enter the aggregate.
PSGC population remains a cross-check.

See [Silver geography and population](silver_geography_population.md) for the matching,
lineage, validation, and cost contracts.

## Remaining Silver matching tables (planned)

These tables preserve explainable matching decisions.
The Gold model must not hide those decisions.
They describe the target design and do not claim that the tables already exist.

| Table | Grain | Primary key | Main columns |
| --- | --- | --- | --- |
| `02-silver.silver_dpwh_project_component` | One DPWH component or type-of-work record per contract and ingestion run | `component_key` | `source_system`, `contract_id`, `source_component_id`, `source_infra_type`, `source_type_of_work`, `component_description`, `source_row_number`, `run_id`, `source_load_ts` |
| `02-silver.silver_flood_control_component` | One published flood-control source row | `flood_component_key` | `source_contract_id`, matched project system and contract, `type_of_work`, `component_description`, `source_contract_cost`, `match_status`, `source_row_number`, `source_version`, `run_id`, `source_load_ts` |
| `02-silver.silver_project_region_map` | One project-to-region mapping result per pipeline run | `project_region_map_key` | `source_system`, `contract_id`, `psgc_region_code`, `reported_region_raw`, `mapping_method`, `match_status`, `match_quality`, `boundary_version`, `run_id`, `source_load_ts` |
| `02-silver.silver_project_flood_map` | One final project-to-flood classification per pipeline run | `project_flood_map_key` | `source_system`, `contract_id`, `flood_susceptibility_level`, `severity_rank`, `match_status`, `matched_polygon_count`, `classification_rule`, `mgb_source_version`, `run_id`, `source_load_ts` |

Required Silver uniqueness:

- Project-region and project-flood maps: `source_system`, `contract_id`, `run_id`.
- DPWH components: `source_system`, `contract_id`, `source_component_id`, `run_id`.
- Use `source_row_number` when no stable component ID exists.
- Flood-control components: `source_contract_id`, `source_row_number`, `source_version`, `run_id`.
- Implemented population reconciliation: `source_file`, `sheet_name`, `source_row_number`, `run_id`.
- Implemented region population: region code, reference year, source name, and both selected snapshots.

## Gold fact tables (planned)

These fact tables are design targets and do not exist yet.

### `03-gold.fact_project_snapshot`

Grain: one DPWH project per distinct source snapshot.

Primary key: `project_snapshot_key`.

Foreign keys:

- `project_key`
- `region_key`
- `status_key`
- `flood_susceptibility_key`
- `snapshot_date_key`
- `start_date_key`
- `source_completion_date_key`

Main measures and lineage:

- `reported_budget_pesos DECIMAL(20,2)`.
- `physical_progress_pct DECIMAL(5,2)`.
- `latitude DOUBLE`, `longitude DOUBLE`, and coordinate or match status fields.
- `long_running_flag`, `zero_progress_flag`, and `delivery_rule_version`.
- `source_snapshot_id`, `run_id`, `is_current_snapshot`, and `source_load_ts`.

Uniqueness: `project_key`, `source_snapshot_id`.

### `03-gold.fact_region_population`

Grain: one region per population reference year and source.

Primary key: `region_population_fact_key`.
Foreign key: `region_key`.

Main columns:

- `reference_year`
- `population_count`
- `source_name`
- `is_primary_source`
- `population_match_status`
- `source_row_count`
- `run_id`
- `source_load_ts`

Uniqueness: `region_key`, `reference_year`, `source_name`.

### `03-gold.fact_region_flood_exposure`

Grain: one region per susceptibility level, MGB version, and boundary version.

Primary key: `region_flood_exposure_key`.
Foreign keys: `region_key` and `flood_susceptibility_key`.

Measures and lineage:

- `susceptible_area_sqkm`
- `share_of_region_area_pct`
- `source_polygon_count`
- `mgb_source_version`
- `boundary_version`
- `spatial_match_status`
- `area_calculation_crs`
- `area_rule_version`
- `run_id`
- `source_load_ts`

Uniqueness includes these fields:

- `region_key`
- `flood_susceptibility_key`
- `mgb_source_version`
- `boundary_version`

## Gold dimensions (planned)

These dimensions are design targets and do not exist yet.

| Dimension | Grain and key | Main columns |
| --- | --- | --- |
| `03-gold.dim_date` | One row per calendar date. Key: `date_key`. | `calendar_date`, year, quarter, month, and day fields |
| `03-gold.dim_project` | One unique contract per source system. Key: `project_key`. | `contract_id`, descriptions, categories, standardized sector, mapping details, flood-list details, funding source, office, contractor, infrastructure year, lineage |
| `03-gold.dim_region` | One official PSGC region per PSGC version plus key `0`. Key: `region_key`. | PSGC code, names, version, BARMM and geographic flags, centroid, lineage |
| `03-gold.dim_project_status` | One source-status mapping per version. Key: `status_key`. | Source and standardized status, group, mapping version, source system, active flag, lineage |
| `03-gold.dim_flood_susceptibility` | One susceptibility classification per source version. Key: `flood_susceptibility_key`. | Level, severity rank, source system, source version, lineage |
| `03-gold.dim_region_boundary` | One boundary version per official region. Key: `boundary_key`. | `region_key`, geometry, version, CRS, validity, PSGC-match status, source system, lineage |

Dimension uniqueness:

- `dim_date`: `calendar_date`.
- `dim_project`: `source_system`, `contract_id`.
- `dim_region`: `psgc_region_code`, `psgc_version`.
- `dim_project_status`: `source_system`, `source_status`, `status_mapping_version`.
- `dim_flood_susceptibility`: `source_system`, `flood_susceptibility_level`, `source_version`.
- `dim_region_boundary`: `region_key`, `boundary_version`.

## Six-source lineage

| Source | Downstream destination |
| --- | --- |
| DPWH projects | DPWH component mapping, category mapping, project and status dimensions, and project snapshot fact |
| Flood-control list | Flood-control components and official flood-list flags on projects |
| PSGC | Region dimension and population reconciliation |
| PSA Table C | Population reconciliation and region population fact |
| BetterGov boundaries | Region boundary dimension, project-region mapping, and regional flood intersection |
| MGB flood susceptibility | Project-flood mapping, susceptibility dimension, and region flood-exposure fact |

## Join rules

- `fact_project_snapshot.project_key` joins to `dim_project.project_key`.
- `fact_project_snapshot.region_key` joins to `dim_region.region_key`.
- Status, susceptibility, and date keys join to their corresponding dimensions.
- Population and flood-exposure facts join to `dim_region` through `region_key`.
- Silver mapping tables retain the run, method, quality, and source version for every Gold key.
- Key `0` is reserved for unknown, unmapped, or non-geographic records.
  Central Office uses key `0` with `region_match_status = 'Non-geographic reporting unit'`.

## Required analytical validation (planned)

Apply these checks when the corresponding Silver and Gold tables are implemented.

1. At most one `is_current_snapshot = true` row exists per `project_key`.
2. Physical progress is between 0 and 100 or null.
3. Reported budget is non-negative or null.
4. Flood-exposure area is non-negative. Its regional share is between 0 and 100.
5. Primary population is positive. Each region and year has exactly one primary source.
6. Central Office is excluded from population-based ratios.
7. MGB classifications include Unknown, Low, Moderate, High, and Very High.
8. Severity rank is unique within each source system and version.
9. `source_snapshot_id` is not null. All fact foreign keys resolve.
10. Spatial areas use an appropriate projected CRS instead of square degrees.

## Business-question coverage (planned)

| Analysis | Main tables | Interpretation boundary |
| --- | --- | --- |
| Regional investment concentration | `fact_project_snapshot` and `dim_region` | Use reported budgets. Show coordinate and match coverage. |
| Infrastructure portfolio and categories | `fact_project_snapshot` and `dim_project` | Category rules are versioned and explainable. |
| Project delivery and status | Project fact plus status, date, and region dimensions | Use long-running or zero-progress rules. Do not claim that a project is delayed without evidence. |
| Investment relative to population | Project fact plus region population fact and region dimension | Describe allocation differences, not fairness. Exclude non-geographic Central Office. |
| Flood-control alignment | Project fact, project and susceptibility dimensions, flood-exposure and population facts, and region | Report comparative patterns. Do not claim proof of insufficient protection or causation. |

The available need proxies are population and flood-risk exposure.
They do not represent every form of infrastructure need.
Reported budgets and contract costs are not actual payments or disbursements.

## Bronze preservation boundary

Bronze does not clean names, cast business types, map places, or deduplicate source rows.
It does not standardize categories, calculate measures, or perform spatial joins.
These decisions begin in Silver and remain traceable.
Traceability uses snapshot IDs, run IDs, mapping statuses, rule versions, and source versions.
