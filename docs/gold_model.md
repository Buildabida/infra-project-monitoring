# Gold model

This doc defines the nine Gold tables in the `03-gold` schema.

Gold holds the facts and dimensions that answer the project questions. The dashboard and Genie read these tables.

Status: five notebooks in `notebooks/03_gold` build the six dimensions. They need a Databricks run before the tables exist. Three more notebooks build the facts. The Gold validator is planned.

## Build rules

Follow the [style guide](style-guide.md) for all Gold work. These points matter most for Gold:

1. Write Gold in SQL. See decision [D-08](decisions.md).
2. Start each notebook with ``USE CATALOG `buildabida-capstone` ``. Name tables as `` `03-gold`.dim_region ``.
3. Make every run safe to repeat. Use `CREATE OR REPLACE TABLE` or `MERGE INTO`.
4. Add a comment to every table and every column. Genie reads them.
5. Use the table names, column names, types and column order in this doc exactly.
6. Do not add tables, columns or relationships that this doc does not list.
7. If a name looks like a typo, flag it. Do not change it without approval.

## Table definitions

Each table lists its key type, column, and data type in the order the column appears in the table. `PK` means primary key. `FK` means foreign key.

### Dimensions

#### `dim_project`

Grain: one unique contract per source system.
Uniqueness: `source_system`, `contract_id`.

| Key | Column | Type |
| --- | --- | --- |
| PK | `project_key` | BIGINT |
| None | `contract_id` | STRING |
| None | `source_system` | STRING |
| None | `project_description` | STRING |
| None | `raw_category` | STRING |
| None | `source_infra_type` | STRING |
| None | `standardized_sector` | STRING |
| None | `infra_type_mapping_status` | STRING |
| None | `taxonomy_version` | STRING |
| None | `is_dpwh_flood_related` | BOOLEAN |
| None | `is_in_official_flood_list` | BOOLEAN |
| None | `flood_list_match_status` | STRING |
| None | `flood_list_version` | STRING |
| None | `funding_source` | STRING |
| None | `implementing_office` | STRING |
| None | `contractor_name` | STRING |
| None | `infra_year` | INT |
| None | `run_id` | STRING |
| None | `source_load_ts` | TIMESTAMP |

#### `dim_date`

Grain: one row per calendar date.
Uniqueness: `calendar_date`.

| Key | Column | Type |
| --- | --- | --- |
| PK | `date_key` | INT |
| None | `calendar_date` | DATE |
| None | `calendar_year` | INT |
| None | `calendar_quarter` | INT |
| None | `month_number` | INT |
| None | `month_name` | STRING |
| None | `day_of_month` | INT |

#### `dim_project_status`

Grain: one source status mapping per mapping version.
Uniqueness: `source_system`, `source_status`, `status_mapping_version`.

| Key | Column | Type |
| --- | --- | --- |
| PK | `status_key` | INT |
| None | `source_status` | STRING |
| None | `standardized_status` | STRING |
| None | `status_group` | STRING |
| None | `status_mapping_version` | STRING |
| None | `source_system` | STRING |
| None | `is_active` | BOOLEAN |
| None | `run_id` | STRING |
| None | `source_load_ts` | TIMESTAMP |

#### `dim_flood_susceptibility`

Grain: one susceptibility classification per source version.
Uniqueness: `source_system`, `flood_susceptibility_level`, `source_version`.

| Key | Column | Type |
| --- | --- | --- |
| PK | `flood_susceptibility_key` | INT |
| None | `flood_susceptibility_level` | STRING |
| None | `severity_rank` | INT |
| None | `source_system` | STRING |
| None | `source_version` | STRING |
| None | `run_id` | STRING |
| None | `source_load_ts` | TIMESTAMP |

#### `dim_region`

Grain: one official PSGC region per PSGC version, plus key `0`.
Uniqueness: `psgc_region_code`, `psgc_version`.

| Key | Column | Type |
| --- | --- | --- |
| PK | `region_key` | BIGINT |
| None | `psgc_region_code` | STRING |
| None | `region_name` | STRING |
| None | `region_short_name` | STRING |
| None | `psgc_version` | STRING |
| None | `is_barmm` | BOOLEAN |
| None | `is_geographic_region` | BOOLEAN |
| None | `centroid_latitude` | DOUBLE |
| None | `centroid_longitude` | DOUBLE |
| None | `run_id` | STRING |
| None | `source_load_ts` | TIMESTAMP |

#### `dim_region_boundary`

Grain: one boundary version per official region.
Uniqueness: `region_key`, `boundary_version`.

| Key | Column | Type |
| --- | --- | --- |
| PK | `boundary_key` | BIGINT |
| FK | `region_key` | BIGINT |
| None | `boundary_geometry` | GEOMETRY(4326) |
| None | `boundary_version` | STRING |
| None | `coordinate_reference_system` | STRING |
| None | `geometry_valid_flag` | BOOLEAN |
| None | `psgc_match_status` | STRING |
| None | `source_system` | STRING |
| None | `run_id` | STRING |
| None | `source_load_ts` | TIMESTAMP |

### Facts

#### `fact_project_snapshot`

Grain: one DPWH project per distinct source snapshot.
Uniqueness: `project_key`, `source_snapshot_id`.

| Key | Column | Type |
| --- | --- | --- |
| PK | `project_snapshot_key` | BIGINT |
| FK | `project_key` | BIGINT |
| FK | `region_key` | BIGINT |
| FK | `status_key` | INT |
| FK | `flood_susceptibility_key` | INT |
| FK | `snapshot_date_key` | INT |
| FK | `start_date_key` | INT |
| FK | `source_completion_date_key` | INT |
| None | `reported_region_raw` | STRING |
| None | `reported_budget_pesos` | DECIMAL(20,2) |
| None | `physical_progress_pct` | DECIMAL(5,2) |
| None | `latitude` | DOUBLE |
| None | `longitude` | DOUBLE |
| None | `coordinate_status` | STRING |
| None | `region_match_status` | STRING |
| None | `region_match_method` | STRING |
| None | `region_match_confidence` | STRING |
| None | `flood_match_status` | STRING |
| None | `long_running_flag` | BOOLEAN |
| None | `zero_progress_flag` | BOOLEAN |
| None | `delivery_rule_version` | STRING |
| None | `run_id` | STRING |
| None | `is_current_snapshot` | BOOLEAN |
| None | `source_load_ts` | TIMESTAMP |
| None | `source_snapshot_id` | STRING |

#### `fact_region_flood_exposure`

Grain: one region per susceptibility level, MGB snapshot, and boundary version.
Uniqueness: `region_key`, `flood_susceptibility_key`, `mgb_source_snapshot_id`, `boundary_version`.

The MGB publisher version is not available, so `mgb_source_version` is `NULL`. The MGB snapshot ID keeps the grain traceable instead. Never add level areas together for a region unless `level_area_additivity_status` is `ADDITIVE_WITHIN_TOLERANCE`. Flood levels can overlap.

| Key | Column | Type |
| --- | --- | --- |
| PK | `region_flood_exposure_key` | BIGINT |
| FK | `region_key` | BIGINT |
| FK | `flood_susceptibility_key` | INT |
| None | `susceptible_area_sqkm` | DECIMAL(18,4) |
| None | `share_of_region_area_pct` | DECIMAL(7,4) |
| None | `source_polygon_count` | BIGINT |
| None | `mgb_source_version` | STRING |
| None | `boundary_version` | STRING |
| None | `spatial_match_status` | STRING |
| None | `area_calculation_crs` | STRING |
| None | `area_rule_version` | STRING |
| None | `run_id` | STRING |
| None | `source_load_ts` | TIMESTAMP |
| None | `level_area_additivity_status` | STRING |
| None | `mgb_source_snapshot_id` | STRING |

#### `fact_region_population`

Grain: one region per population reference year and source.
Uniqueness: `region_key`, `reference_year`, `source_name`.

| Key | Column | Type |
| --- | --- | --- |
| PK | `region_population_fact_key` | BIGINT |
| FK | `region_key` | BIGINT |
| None | `reference_year` | INT |
| None | `population_count` | BIGINT |
| None | `source_name` | STRING |
| None | `is_primary_source` | BOOLEAN |
| None | `population_match_status` | STRING |
| None | `source_row_count` | BIGINT |
| None | `run_id` | STRING |
| None | `source_load_ts` | TIMESTAMP |

## Relationships

Every relationship is one-to-many, from a dimension to a fact or to another dimension.

| Parent (one) | Child (many) | Join columns |
| --- | --- | --- |
| `dim_project.project_key` | `fact_project_snapshot` | `project_key` |
| `dim_project_status.status_key` | `fact_project_snapshot` | `status_key` |
| `dim_date.date_key` | `fact_project_snapshot` | `snapshot_date_key`, `start_date_key`, `source_completion_date_key` |
| `dim_flood_susceptibility.flood_susceptibility_key` | `fact_project_snapshot` | `flood_susceptibility_key` |
| `dim_flood_susceptibility.flood_susceptibility_key` | `fact_region_flood_exposure` | `flood_susceptibility_key` |
| `dim_region.region_key` | `fact_project_snapshot` | `region_key` |
| `dim_region.region_key` | `fact_region_flood_exposure` | `region_key` |
| `dim_region.region_key` | `fact_region_population` | `region_key` |
| `dim_region.region_key` | `dim_region_boundary` | `region_key` |

Two rules apply:

- `dim_date` is a role-playing dimension. The project fact joins to it three times, once for each date column. Do not split it into separate start, snapshot, or completion date tables.
- Do not add relationships beyond this list.

## Surrogate keys

Gold keys are deterministic. The same Silver inputs always give the same key, so a rerun never changes a key. See decision [D-33](decisions.md).

| Key | Type | How it is made |
| --- | --- | --- |
| `date_key` | INT | The date as `yyyymmdd`, such as `20261004` |
| `region_key` | BIGINT | `XXHASH64` of the PSGC region code and PSGC version |
| `boundary_key` | BIGINT | `XXHASH64` of the region key and boundary version |
| `project_key` | BIGINT | `XXHASH64` of the source system and Contract ID |
| `status_key` | INT | `HASH` of the source system, source status, and status mapping version |
| `flood_susceptibility_key` | INT | `HASH` of the source system, level, and source version |

Each hash input starts with a fixed label, such as `PSGC_REGION`, so two key types never share an input. A STOP check proves every key is unique and that no real member gets key `0`.

Silver keys are SHA-256 strings. Gold does not reuse them as keys. `dim_project` joins back to Silver through `source_system` and `contract_id`.

## Unknown and non-geographic records

Key `0` is reserved for unknown, unmapped, or non-geographic records.

| Dimension | Key `0` member | Facts use it when |
| --- | --- | --- |
| `dim_date` | `month_name = 'Unknown'` and a `NULL` date | A source date is missing |
| `dim_region` | `Unknown or non-geographic` | The project is Central Office, unmatched, or ambiguous |
| `dim_project_status` | `Missing or conflicting status` | The source status is missing or its rows disagree |
| `dim_flood_susceptibility` | `Unknown` with `severity_rank = 0` | Silver published no single approved level |
| `dim_project` | None | Never. Every fact row comes from a real Silver project. |

Central Office uses `region_key = 0`. Its `region_match_status` stays `NON_GEOGRAPHIC`, the value Silver publishes. Gold copies Silver statuses and never relabels them.

Flood key `0` never means low or zero risk. It means the point fell outside every approved polygon, inside polygons of more than one level, or had no usable coordinate.

Silver keeps the real mapping result. Gold only resolves it to a key. See [Silver project-to-region mapping](silver_project_region_mapping.md#gold-handoff).

## Unmapped values stay visible

The category and status configuration tables have no approved rows yet. Until the team approves them:

- `dim_project.standardized_sector` is `NULL`, and `infra_type_mapping_status` says why.
- `dim_project.is_dpwh_flood_related` is `NULL`.
- `dim_project_status` has one row per observed DPWH status. `standardized_status` and `status_group` are `NULL`, and `status_mapping_version` is `NO_APPROVED_STATUS_MAPPING`.

Gold never adds its own `CASE` rule for a category or a status. See [Silver configuration mappings](silver_config_mappings.md).

About 30 projects have a status that is really another field, such as `0.00` or a place name. Those rows were shifted in the source CSV. They stay as their own status members, and the Gold validator flags them.

`source_infra_type` and `implementing_office` are `NULL`:

- `implementing_office`: Bronze has the District Engineering Office in `deo`, filled for almost every project. Silver does not carry it yet. Gold reads only Silver, so the column fills once `silver_project` publishes it.
- `source_infra_type`: DPWH has no infrastructure-type column. The raw JSON field `componentCategories` may be a candidate. The team has not decided.

## Project delivery rules

`fact_project_snapshot` applies two rules. Both are versioned in `delivery_rule_version`.

- **Long-running ([D-32](decisions.md)):** true when more than 24 months pass from the start date to the completion date. A project without a completion date is measured to its snapshot date instead. The snapshot date is the file date of the DPWH snapshot, never the current date. The flag is `NULL` without a start date.
- **Progress range:** `physical_progress_pct` is published only between 0 and 100. Values outside that range are shifted source values, such as `2026`. They become `NULL` in Gold, stay visible in Silver, and the Gold validator counts them. This follows the analytical check in [Data model](data-model.md#required-analytical-validation-planned).

`zero_progress_flag` comes unchanged from Silver. A stalled flag waits for an approved status mapping, because it needs to know which projects are ongoing.

## Load pattern

Every Gold notebook follows the same steps:

1. Check that each Silver input is one run and passed its Silver validation. Stop if not.
2. Create the table with `CREATE TABLE IF NOT EXISTS`, with explicit types and a comment on every column.
3. Build the rows in a temporary view and check the keys.
4. `MERGE` the rows by key. Rows are never deleted, so older facts always find their dimension members.

`dim_project_status` also marks rows from an older mapping version `is_active = false`.

## Silver to Gold handoff

Gold does not repeat cleaning, matching, or mapping. Each Gold table reads a Silver output.

| Gold table | Notebook | Reads from |
| --- | --- | --- |
| `dim_date` | `00_gold_dim_date` | Generated from a date range. No source table. |
| `dim_region` | `01_gold_dim_region` | `02-silver.silver_psgc_place`, plus boundary safety from `02-silver.silver_region_flood_exposure` |
| `dim_region_boundary` | `01_gold_dim_region` | `01-bronze.boundaries` region rows, parsed with the Table 13 rule, plus boundary safety from `02-silver.silver_region_flood_exposure` |
| `dim_flood_susceptibility` | `02_gold_dim_flood_susceptibility` | `02-silver.config_mgb_susceptibility_mapping` |
| `dim_project_status` | `03_gold_dim_project_status` | `02-silver.silver_project` statuses and `02-silver.config_project_status_mapping` |
| `dim_project` | `04_gold_dim_project` | `02-silver.silver_project` and `02-silver.silver_project_source_match` |
| `fact_region_population` | `05_gold_fact_region_population` | `02-silver.silver_region_population` |
| `fact_region_flood_exposure` | `06_gold_fact_region_flood_exposure` | `02-silver.silver_region_flood_exposure` |
| `fact_project_snapshot` | `07_gold_fact_project_snapshot` | `02-silver.silver_project`, `02-silver.silver_project_region_map`, `02-silver.silver_project_flood_map` |

Gold runs no spatial matching, clipping, or area work. Region shapes are parsed only to store them for maps. The parser is the Table 13 rule. Its two patterns are written as raw literals, `r'...'`, and a test proves the rule is the same.

Gold SQL never uses `\\`. The VS Code `%sql` runner turns `\\` into `\` before Spark reads the statement. An escaped pattern then breaks, and the shapes silently become `NULL`. A test fails if Gold SQL contains `\\`.

For the details of each handoff, read the "Gold handoff" section in these docs:

- [Silver geography and population](silver_geography_population.md#gold-handoff)
- [Silver project foundation](silver_project_cleaning.md#gold-handoff)
- [Silver source reconciliation](silver_source_reconciliation.md)
- [Silver project-to-region mapping](silver_project_region_mapping.md#gold-handoff)
- [Silver regional flood exposure](silver_region_flood_exposure.md#gold-handoff)
- [Silver project flood mapping](silver_project_flood_mapping.md#gold-handoff)

## Build order

Facts need dimension keys, so build the dimensions first. Run each notebook in Databricks with **Run File as Workflow**.

1. `notebooks/03_gold/00_gold_dim_date.ipynb`
2. `notebooks/03_gold/01_gold_dim_region.ipynb`, which builds `dim_region` and `dim_region_boundary`
3. `notebooks/03_gold/02_gold_dim_flood_susceptibility.ipynb`
4. `notebooks/03_gold/03_gold_dim_project_status.ipynb`
5. `notebooks/03_gold/04_gold_dim_project.ipynb`
6. `notebooks/03_gold/05_gold_fact_region_population.ipynb`
7. `notebooks/03_gold/06_gold_fact_region_flood_exposure.ipynb`
8. `notebooks/03_gold/07_gold_fact_project_snapshot.ipynb`

## Validation

The analytical checks live in [Data model](data-model.md#required-analytical-validation-planned). Keep them there.

The planned notebook `notebooks/04_validation/09_validation_gold.ipynb` runs them. It writes to `04-validation.gold_dq_results`. See the [Notebooks guide](../notebooks/README.md).

`tests/test_gold_dimensions.py` checks each dimension notebook against this doc. It fails when a column name, type, or order differs from the tables above.

Before you finish any Gold task, check that:

- [ ] Only the nine tables in this doc were created or changed.
- [ ] Every table and column name matches this doc, in the listed order.
- [ ] Every data type, precision, and scale matches this doc.
- [ ] Every PK and FK matches the tables and the relationships above.
- [ ] Every table and column has a comment.
- [ ] Nothing was added that this doc does not list.
- [ ] Any doubt was raised with the team, not settled by guessing.

## Settled questions

1. **How do we generate surrogate keys?** With deterministic hashes. See [Surrogate keys](#surrogate-keys) and D-33.
2. **What date range does `dim_date` cover?** January 1, 2000 to December 31, 2035. Key `0` stands for a missing date.
3. **Which dimensions get an unknown row?** `dim_date`, `dim_region`, `dim_project_status`, and `dim_flood_susceptibility`. `dim_project` does not need one. See [Unknown and non-geographic records](#unknown-and-non-geographic-records).
4. **How do we refresh `is_current_snapshot`?** The project fact merges each snapshot by `project_key` and `source_snapshot_id`. Then it sets `is_current_snapshot` to true only for the newest DPWH snapshot. This is built with the fact.
