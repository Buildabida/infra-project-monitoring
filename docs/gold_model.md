# Gold model

This doc defines the nine Gold tables in the `03-gold` schema.

Gold holds the facts and dimensions that answer the project questions. The dashboard and Genie read these tables.

Status: five notebooks in `notebooks/03_gold` build the six dimensions. Three more notebooks build the three facts. The Gold validator is planned.

## Build rules

Follow the [style guide](style-guide.md) for all Gold work. These points matter most for Gold:

1. Write Gold in SQL. See decision [D-08](decisions.md).
2. Start each notebook with ``USE CATALOG `buildabida-capstone` ``. Name tables as `` `03-gold`.dim_region ``.
3. Make every run safe to repeat. Create each table once with `CREATE TABLE IF NOT EXISTS`, then load it with `MERGE INTO`. Never use `CREATE OR REPLACE TABLE`, `DELETE`, or `TRUNCATE` on a Gold table.
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

As of the Oct 9 run, the 18 regions total 112,722,987 people for 2024. The national census total is 112,727,776. The gap of 4,789 people (0.004 percent) is two Table C barangays that Silver leaves `UNMATCHED`: `Sawata` in Sawata, Davao del Norte (4,152 people, Region XI), and `San Rafael` in the City of Calaca, Batangas (637 people, Region IV-A). No PSGC barangay in either place has a close name, so they need a source check before any alias. Silver adds only `ACCEPTED_PRIMARY` barangay rows to a region, so these rows are in no region total. See [Silver geography and population](silver_geography_population.md#known-limitations).

Before the issue #88 fix, the gap was 3,783,955 people (3.4 percent), and NCR had no Manila population.

Gold copies the Silver totals and does not fill the gap. The Gold population checks flag it.

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

| Key | Type | Label | How it is made | Code |
| --- | --- | --- | --- | --- |
| `date_key` | INT | None | The date as `yyyymmdd`, such as `20261004` | `00_gold_dim_date.ipynb`, cell 6, line 224 |
| `region_key` | BIGINT | `PSGC_REGION` | `XXHASH64(CONCAT_WS('\|', 'PSGC_REGION', psgc_region_code, COALESCE(psgc_version, source_snapshot_id)))` | `01_gold_dim_region.ipynb`, cell 8, lines 448 to 451, and the gate in cell 2, line 121 |
| `boundary_key` | BIGINT | `REGION_BOUNDARY` | `XXHASH64(CONCAT_WS('\|', 'REGION_BOUNDARY', CAST(region_key AS STRING), boundary_version))` | `01_gold_dim_region.ipynb`, cell 10, lines 557 to 559 |
| `project_key` | BIGINT | `PROJECT` | `XXHASH64(CONCAT_WS('\|', 'PROJECT', source_system, contract_id))` | `04_gold_dim_project.ipynb`, cell 8, line 380 |
| `status_key` | INT | `PROJECT_STATUS` | `HASH(CONCAT_WS('\|', 'PROJECT_STATUS', source_system, source_status, status_mapping_version))` | `03_gold_dim_project_status.ipynb`, cell 6, lines 340 to 342 |
| `flood_susceptibility_key` | INT | `FLOOD_SUSCEPTIBILITY` | `HASH(CONCAT_WS('\|', 'FLOOD_SUSCEPTIBILITY', source_system, flood_susceptibility_level, source_version))` | `02_gold_dim_flood_susceptibility.ipynb`, cell 6, lines 293 to 295 |

Cell numbers count from 0. Line numbers are lines of the `.ipynb` file, so they move when a cell above them changes.

`region_key` uses the PSGC snapshot ID when Silver has no PSGC version. When no status mapping is approved, `status_mapping_version` is `NO_APPROVED_STATUS_MAPPING`.

Each hash input starts with its label, so two key types never share an input. Facts must build each key with this exact recipe. A STOP check proves every key is unique and that no real member gets key `0`.

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

The category taxonomy is approved and lives in Silver (D-39). The DPWH status mapping `dpwh-status-2026-10-v1` is approved in configuration (D-40). So:

- `dim_project` copies `source_infra_type`, `standardized_sector`, `taxonomy_version` and `is_dpwh_flood_related` from `silver_project`. A project with no usable `componentCategories` value keeps a `NULL` sector and flag.
- `dim_project.infra_type_mapping_status` copies Silver's `category_classification_status`, so it says why a sector is `NULL`. See D-37.
- `dim_project_status` has one row per observed DPWH status. The five approved statuses carry `standardized_status` and `status_group`. Shifted or malformed statuses keep `NULL` values. Gold reads configuration with the config key `source_system = 'dpwh_projects'`, while its own rows keep the Silver label `DPWH`.

Gold never adds its own `CASE` rule for a category or a status. See [Silver configuration mappings](silver_config_mappings.md).

About 30 projects have a status that is really another field, such as `0.00` or a place name. Those rows were shifted in the source CSV. They stay as their own status members, and the Gold validator flags them.

`implementing_office` copies `silver_project.implementing_office`, which Silver resolves from the DPWH `deo` field since #95. It is `NULL` when a project has no single office, and Silver's `implementing_office_resolution_status` says why.

## Project delivery rules

`fact_project_snapshot` applies two rules. Both are versioned in `delivery_rule_version`.

- **Long-running ([D-32](decisions.md)):** true when more than 24 months pass from the start date to the completion date. A project without a completion date is measured to its snapshot date instead. A completion date later than the snapshot date is capped at the snapshot date, so the flag never counts time the snapshot has not reached. The snapshot date is the file date of the DPWH snapshot, never the current date. The flag is `NULL` without a start date.
- **Progress range:** `physical_progress_pct` is published only when Silver's `progress_quality_status` is `VALID`. Silver checks the 0 to 100 range once and marks values outside it `OUT_OF_RANGE`. Those are shifted source values, such as `2026`. They become `NULL` in Gold, stay visible in Silver, and the Gold validator counts them. This follows the analytical check in [Data model](data-model.md#required-analytical-validation-planned).

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
| `dim_region_boundary` | `01_gold_dim_region` | `01-bronze.boundaries` region rows, parsed with the Table 13 rule, plus boundary safety from `02-silver.silver_region_flood_exposure`. Allowed by D-35. |
| `dim_flood_susceptibility` | `02_gold_dim_flood_susceptibility` | `02-silver.config_mgb_susceptibility_mapping`, plus the MGB load time from `02-silver.silver_project_flood_map` |
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
