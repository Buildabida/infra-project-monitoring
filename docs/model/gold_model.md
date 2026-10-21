# Gold model

This doc defines the regional Gold model and the three D-57 province
reporting-area additions in the `03-gold` schema.

Gold holds the facts and dimensions that answer the project questions. The Analytics views in `05-analytics` read these tables, and the dashboard reads the views. See [Analytics views](../../notebooks/05_analytics/README.md).

Status: Gold notebooks in `notebooks/03_gold` build eight dimensions and four facts. `09_validation_gold` validates the regional model, and `09a_validation_gold_province_reporting` validates the province reporting-area model. Runtime evidence for both is in [Runtime evidence](#runtime-evidence) and the [province-reporting evidence](../evidence/province-reporting/README.md).

## Build rules

Follow the [style guide](../style-guide.md) for all Gold work. These points matter most for Gold:

1. Write Gold in SQL. See decision [D-08](../decisions.md).
2. Start each notebook with ``USE CATALOG `buildabida-capstone` ``. Name tables as `` `03-gold`.dim_region ``.
3. Make every run safe to repeat. Create each table once with `CREATE TABLE IF NOT EXISTS`, then load it with `MERGE INTO`. Never use `CREATE OR REPLACE TABLE`, `DELETE`, or `TRUNCATE` on a Gold table.
4. Add a comment to every table and every column, so anyone who queries them knows what they mean.
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
| None | `psgc_run_id` | STRING |
| None | `exposure_run_id` | STRING |

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
| None | `psgc_run_id` | STRING |
| None | `exposure_run_id` | STRING |

`psgc_run_id` is the run of `02-silver.silver_psgc_place` and `exposure_run_id` is the run of `02-silver.silver_region_flood_exposure` (Table 14) behind each row in `dim_region` and `dim_region_boundary`. They make a row traceable to its Silver runs without recomputing the `run_id` hash (issue #93). `run_id` and every key keep their recipe. `CREATE TABLE IF NOT EXISTS` does not add columns to an existing table, so `01_gold_dim_region` adds the two columns once with `ALTER TABLE ... ADD COLUMNS` when `information_schema.columns` does not list them. A STOP check blocks a row without either value.

#### `dim_province_reporting_area`

Grain: one governed reporting area per selected PSGC version, plus one Unknown.
Uniqueness: `reporting_area_key`.

| Key | Column | Type |
| --- | --- | --- |
| PK | `reporting_area_key` | BIGINT |
| None | `psgc_reporting_area_code` | STRING |
| None | `reporting_area_name` | STRING |
| None | `reporting_area_short_name` | STRING |
| None | `reporting_area_type` | STRING |
| FK | `region_key` | BIGINT |
| None | `psgc_version` | STRING |
| None | `is_geographic_area` | BOOLEAN |
| None | `centroid_latitude` | DOUBLE |
| None | `centroid_longitude` | DOUBLE |
| None | `run_id` | STRING |
| None | `source_load_ts` | TIMESTAMP |
| None | `psgc_run_id` | STRING |
| None | `boundary_run_id` | STRING |

Allowed `reporting_area_type` values are `PROVINCE`, `INDEPENDENT_CITY`, `NCR`,
and `UNKNOWN`. Key `0` is the one Unknown member. Region is the required parent
for every geographic member.

#### `dim_province_reporting_area_boundary`

Grain: one selected boundary-status row per reporting area and boundary version.
Unavailable or unsafe geometry stays `NULL`. Its status is never presented as
zero area or a valid boundary.

| Key | Column | Type |
| --- | --- | --- |
| PK | `boundary_key` | BIGINT |
| FK | `reporting_area_key` | BIGINT |
| None | `boundary_geometry` | GEOMETRY(4326) |
| None | `boundary_version` | STRING |
| None | `coordinate_reference_system` | STRING |
| None | `geometry_valid_flag` | BOOLEAN |
| None | `boundary_status` | STRING |
| None | `run_id` | STRING |
| None | `source_load_ts` | TIMESTAMP |
| None | `psgc_run_id` | STRING |
| None | `boundary_run_id` | STRING |

### Facts

#### `fact_project_snapshot`

Grain: one DPWH project per distinct source snapshot.
Uniqueness: `project_key`, `source_snapshot_id`.

| Key | Column | Type |
| --- | --- | --- |
| PK | `project_snapshot_key` | BIGINT |
| FK | `project_key` | BIGINT |
| FK | `region_key` | BIGINT |
| FK | `reporting_area_key` | BIGINT |
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
| None | `reporting_area_match_status` | STRING |
| None | `reporting_area_match_method` | STRING |
| None | `reporting_area_match_quality` | STRING |
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

As of the Oct 9 run, the 18 regions total 112,722,987 people for 2024. The national census total is 112,727,776. The 4,789-person gap (0.004 percent) comes from two Table C barangays that Silver leaves `UNMATCHED`. The first is `Sawata` in Sawata, Davao del Norte, with 4,152 people in Region XI. The second is `San Rafael` in the City of Calaca, Batangas, with 637 people in Region IV-A. No PSGC barangay in either place has a close name. They need a source check before any alias. Silver adds only `ACCEPTED_PRIMARY` barangay rows to a region, so these rows are in no region total. See [Silver geography and population](../silver/silver_geography_population.md#known-limitations).

Before the issue #88 fix, the gap was 3,783,955 people (3.4 percent), and NCR had no Manila population.

After the final Issue #113 fail-closed rerun on October 13, Gold and Silver both total 112,348,732. The difference from the national census total is 379,044. Gold preserves the accepted Silver population and does not infer a replacement for rows that Silver leaves unmatched.

Gold copies the Silver totals and does not fill the gap. The Gold population checks flag it.

#### `fact_province_reporting_area_population`

Grain: one reporting area per population reference year, authoritative source,
and deterministic Silver run. Population is the sum of reconciled Table C
`ACCEPTED_PRIMARY` barangay rows. Missing population remains `NULL`.

| Key | Column | Type |
| --- | --- | --- |
| PK | `reporting_area_population_fact_key` | BIGINT |
| FK | `reporting_area_key` | BIGINT |
| None | `reference_year` | INT |
| None | `population_count` | BIGINT |
| None | `source_name` | STRING |
| None | `is_primary_source` | BOOLEAN |
| None | `population_match_status` | STRING |
| None | `source_row_count` | BIGINT |
| None | `source_snapshot_id` | STRING |
| None | `run_id` | STRING |
| None | `source_load_ts` | TIMESTAMP |
| None | `population_reconciliation_run_id` | STRING |
| None | `reporting_area_population_run_id` | STRING |

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
| `dim_region.region_key` | `dim_province_reporting_area` | `region_key` |
| `dim_region.region_key` | `fact_region_flood_exposure` | `region_key` |
| `dim_region.region_key` | `fact_region_population` | `region_key` |
| `dim_region.region_key` | `dim_region_boundary` | `region_key` |
| `dim_province_reporting_area.reporting_area_key` | `fact_project_snapshot` | `reporting_area_key` |
| `dim_province_reporting_area.reporting_area_key` | `fact_province_reporting_area_population` | `reporting_area_key` |
| `dim_province_reporting_area.reporting_area_key` | `dim_province_reporting_area_boundary` | `reporting_area_key` |

Two rules apply:

- `dim_date` is a role-playing dimension. The project fact joins to it three times, once for each date column. Do not split it into separate start, snapshot, or completion date tables.
- Do not add relationships beyond this list.

## Surrogate keys

Gold keys are deterministic. The same Silver inputs always give the same key, so a rerun never changes a key. See decision [D-33](../decisions.md).

| Key | Type | Label | How it is made | Code |
| --- | --- | --- | --- | --- |
| `date_key` | INT | None | The date as `yyyymmdd`, such as `20261004` | `00_gold_dim_date.ipynb`, cell 6, line 224 |
| `region_key` | BIGINT | `PSGC_REGION` | `XXHASH64(CONCAT_WS('\|', 'PSGC_REGION', psgc_region_code, COALESCE(psgc_version, source_snapshot_id)))` | `01_gold_dim_region.ipynb`, cell 8, lines 506 to 509, and the gate in cell 2, line 121 |
| `boundary_key` | BIGINT | `REGION_BOUNDARY` | `XXHASH64(CONCAT_WS('\|', 'REGION_BOUNDARY', CAST(region_key AS STRING), boundary_version))` | `01_gold_dim_region.ipynb`, cell 10, lines 620 to 622 |
| `project_key` | BIGINT | `PROJECT` | `XXHASH64(CONCAT_WS('\|', 'PROJECT', source_system, contract_id))` | `04_gold_dim_project.ipynb`, cell 8, line 380 |
| `status_key` | INT | `PROJECT_STATUS` | `HASH(CONCAT_WS('\|', 'PROJECT_STATUS', source_system, source_status, status_mapping_version))` | `03_gold_dim_project_status.ipynb`, cell 6, lines 342 to 344 |
| `flood_susceptibility_key` | INT | `FLOOD_SUSCEPTIBILITY` | `HASH(CONCAT_WS('\|', 'FLOOD_SUSCEPTIBILITY', source_system, flood_susceptibility_level, source_version))` | `02_gold_dim_flood_susceptibility.ipynb`, cell 6, lines 294 to 296 |

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
| `dim_project_status` | `Missing or conflicting status` | The source status is missing or its rows disagree. A Silver status without its own active row stops the fact load instead. |
| `dim_flood_susceptibility` | `Unknown` with `severity_rank = 0` | Silver published no single approved level |
| `dim_project` | None | Never. Every fact row comes from a real Silver project. |

Central Office uses `region_key = 0`. Its `region_match_status` stays `NON_GEOGRAPHIC`, the value Silver publishes. Gold copies Silver statuses and never relabels them.

Flood key `0` never means low or zero risk. It means the point fell outside every approved polygon, inside polygons of more than one level, or had no usable coordinate.

Silver keeps the real mapping result. Gold only resolves it to a key. See [Silver project-to-region mapping](../silver/silver_project_region_mapping.md#gold-handoff).

## Unmapped values stay visible

The category taxonomy is approved and lives in Silver (D-39). The DPWH status mapping `dpwh-status-2026-10-v1` is approved in configuration (D-40). So:

- `dim_project` copies `source_infra_type`, `standardized_sector`, `taxonomy_version` and `is_dpwh_flood_related` from `silver_project`. A project with no usable `componentCategories` value keeps a `NULL` sector and flag.
- `dim_project.infra_type_mapping_status` copies Silver's `category_classification_status`, so it says why a sector is `NULL`. See D-37.
- `dim_project_status` has one row per observed DPWH status. The five approved statuses carry `standardized_status` and `status_group`. Shifted or malformed statuses keep `NULL` values. Gold reads configuration with the config key `source_system = 'dpwh_projects'`, while its own rows keep the Silver label `DPWH`.

Gold never adds its own `CASE` rule for a category or a status. See [Silver configuration mappings](../silver/silver_config_mappings.md).

About 30 projects have a status that is really another field, such as `0.00` or a place name. Those rows were shifted in the source CSV. They stay as their own status members, and the Gold validator flags them.

`implementing_office` copies `silver_project.implementing_office`, which Silver resolves from the DPWH `deo` field since #95. It is `NULL` when a project has no single office, and Silver's `implementing_office_resolution_status` says why.

## Project delivery rules

`fact_project_snapshot` applies two rules. Both are versioned in `delivery_rule_version`.

- **Long-running ([D-32](../decisions.md)):** true when more than 24 months pass from the start date to the completion date. A project without a completion date is measured to its snapshot date instead. A completion date later than the snapshot date is capped at the snapshot date, so the flag never counts time the snapshot has not reached. The snapshot date is the file date of the DPWH snapshot, never the current date. The flag is `NULL` without a start date. It is also `NULL` when the completion date is before the start date, because that span cannot be measured ([D-49](../decisions.md)). A start date after the snapshot date gives `FALSE`. This is the only published long-running flag. `silver_project` has none (D-44).
- **Progress range:** `physical_progress_pct` is published only when Silver's `progress_quality_status` is `VALID`. Silver checks the 0 to 100 range once and marks values outside it `OUT_OF_RANGE`. Those are shifted source values, such as `2026`. They become `NULL` in Gold, stay visible in Silver, and the Gold validator counts them. This follows the analytical check in [Data model](data-model.md#required-analytical-validation).

`zero_progress_flag` comes unchanged from Silver. Gold has no stalled flag, because stalled is out of scope for the capstone (D-46). A zero-progress count must filter out `For Procurement` projects or say that it includes them.

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
| `dim_province_reporting_area` | `01a_gold_dim_province_reporting_area` | `02-silver.silver_province_reporting_area`, `02-silver.silver_province_reporting_area_boundary`, `dim_region` |
| `dim_province_reporting_area_boundary` | `01a_gold_dim_province_reporting_area` | `02-silver.silver_province_reporting_area_boundary` |
| `fact_province_reporting_area_population` | `05a_gold_fact_province_reporting_area_population` | `02-silver.silver_province_reporting_area_population`, `dim_province_reporting_area` |
| `fact_project_snapshot` | `07_gold_fact_project_snapshot` | `02-silver.silver_project`, `02-silver.silver_project_region_map`, `02-silver.silver_project_province_map`, `02-silver.silver_project_flood_map` |

Gold runs no spatial matching, clipping, or area work. Region shapes are parsed only to store them for maps. The parser is the Table 13 rule. Its two patterns are written as raw literals, `r'...'`, and a test proves the rule is the same.

Gold SQL never uses `\\`. The VS Code `%sql` runner turns `\\` into `\` before Spark reads the statement. An escaped pattern then breaks, and the shapes silently become `NULL`. A test fails if Gold SQL contains `\\`.

For the details of each handoff, read the "Gold handoff" section in these docs:

- [Silver geography and population](../silver/silver_geography_population.md#gold-handoff)
- [Silver project foundation](../silver/silver_project_cleaning.md#gold-handoff)
- [Silver source reconciliation](../silver/silver_source_reconciliation.md)
- [Silver project-to-region mapping](../silver/silver_project_region_mapping.md#gold-handoff)
- [Silver regional flood exposure](../silver/silver_region_flood_exposure.md#gold-handoff)
- [Silver project flood mapping](../silver/silver_project_flood_mapping.md#gold-handoff)

## Build order

Facts need dimension keys, so build the dimensions first. Run each notebook in Databricks with **Run File as Workflow**.

1. `notebooks/03_gold/00_gold_dim_date.ipynb`
2. `notebooks/03_gold/01_gold_dim_region.ipynb`, which builds `dim_region` and `dim_region_boundary`
3. `notebooks/03_gold/01a_gold_dim_province_reporting_area.ipynb`
4. `notebooks/03_gold/02_gold_dim_flood_susceptibility.ipynb`
5. `notebooks/03_gold/03_gold_dim_project_status.ipynb`
6. `notebooks/03_gold/04_gold_dim_project.ipynb`
7. `notebooks/03_gold/05_gold_fact_region_population.ipynb`
8. `notebooks/03_gold/05a_gold_fact_province_reporting_area_population.ipynb`
9. `notebooks/03_gold/06_gold_fact_region_flood_exposure.ipynb`
10. `notebooks/03_gold/07_gold_fact_project_snapshot.ipynb`
11. `notebooks/04_validation/09_validation_gold.ipynb`
12. `notebooks/04_validation/09a_validation_gold_province_reporting.ipynb`

## Validation

The analytical checks live in [Data model](data-model.md#required-analytical-validation). Keep them there.

`notebooks/04_validation/09_validation_gold.ipynb` retains the regional checks.
`09a_validation_gold_province_reporting.ipynb` then persists D-57 evidence to
the same `gold_dq_results` table before its STOP gate. See
[Gold validation](../validation/validation.md#gold-validation) and the
[Notebooks guide](../../notebooks/README.md).

`fact_region_population` and `fact_region_flood_exposure` have no current flag, and their `MERGE` never deletes. A new PSGC version, MGB snapshot, or boundary version leaves the old rows in place. The validator stops the run when Gold has more rows than Silver. Adding a current flag needs its own decision.

`tests/test_gold_dimensions.py` checks each dimension notebook against this doc. It fails when a column name, type, or order differs from the tables above. `tests/test_validation_gold.py` checks the Gold validator notebook.

Before you finish any Gold task, check that:

- [ ] Only the documented regional and D-57 tables in this doc were created or changed.
- [ ] Every table and column name matches this doc, in the listed order.
- [ ] Every data type, precision, and scale matches this doc.
- [ ] Every PK and FK matches the tables and the relationships above.
- [ ] Every table and column has a comment.
- [ ] Nothing was added that this doc does not list.
- [ ] Any doubt was raised with the team, not settled by guessing.

## Runtime evidence

### Province reporting area on October 16, 2026

The full pipeline ran on Databricks in job run `1077732256280159`. `09a_validation_gold_province_reporting` saved 24 checks under rule `gold-province-reporting-validation-v2`. Its validation run was `5a863b35c04a16aba4c76bbe652a69c927f61c26652d672c1ce419c3ea275f4e`. All 22 STOP checks passed, including three population reconciliations against `fact_region_population`. Key `0` held exactly the unresolved and non-geographic projects. One FLAG found 2,709 projects whose region differs from the parent region of their reporting area. Another found 64,974 projects with an official region but no reporting area. Before the status fix, these findings were saved as `FAIL` with action `flag`. They did not block the run.

The run needed two Gold fixes: `01a_gold_dim_province_reporting_area` now sets SRID 4326 on boundary geometry in its `MERGE`, and `07_gold_fact_project_snapshot` escapes quotes inside its dynamic `ALTER TABLE` string with `\'`. This evidence does not record the `09_validation_gold` check counts of that run. See the [Analytics evidence](../evidence/analytics-2026-10-16/README.md).

### Population refresh on October 13, 2026 (final Issue #113 run)

After the final Issue #113 Silver rerun, `05_gold_fact_region_population` updated all 18 existing regional rows. It inserted and deleted no rows. Gold and Silver both total 112,348,732, all 18 official regions have a population row, and no population fact uses region key `0`.

| Measure | Value |
| --- | --- |
| Gold population rows | 18 |
| Gold population total | 112,348,732 |
| Silver population total | 112,348,732 |
| Regions without population | 0 |
| Population rows on region key `0` | 0 |
| Gold `fact_region_population` `run_id` | `acb2edc2fa191058456240d51cdcb2d7067c18e70c8c939f8f27e11a49c7e7d3` |

`09_validation_gold` then saved 75 checks under validation run `4ec99da18177c198b1d9441a8ae74e5c8a3fc648d114ad9d26d14462e84245dc`. All 65 STOP checks passed, 9 FLAG checks had findings, 1 FLAG check found nothing, and no check failed. The current results are in [`docs/evidence/silver/issue-113-final-gold-validation-results-2026-10-13.csv`](../evidence/silver/issue-113-final-gold-validation-results-2026-10-13.csv).

### Run on October 13, 2026 (Silver audit fixes #109 to #115)

Gold `00` to `07` ran on Databricks serverless compute in the team workspace, on commit `dbd1824` of branch `fix/issue-109-stale-mgb-gate`. Before that, the Silver notebooks reran with the fixes for #109 to #115 (`silver_project_v7`, `silver-population-place-v4`), and every Silver validator passed every STOP check. Gold `00` started at about 06:38 UTC.

| Measure | Value |
| --- | --- |
| `dim_project` rows | 265,656, equal to Silver |
| Current `fact_project_snapshot` rows | 265,656, equal to Silver |
| Current reported budget (PHP) | 6,535,616,688,962.02, equal to Silver |
| `fact_region_population` primary total | 112,722,987, equal to Silver |
| `fact_region_flood_exposure` area | 44,218.7219 sq km, equal to Silver |
| `dim_region` rows | 19 (18 regions and key `0`) |
| `dim_region_boundary` rows | 17 |
| Current `fact_project_snapshot` `run_id` | `def31215c60484374b1bbe3c284d60cff77d2f0728753bde48c74cb1064d6286` |

`09_validation_gold` then ran once. All 65 STOP checks passed. 9 FLAG checks had findings, and 1 found nothing. Every FLAG count equals the October 12 run. The rows are in [`docs/evidence/silver/issue-109-115-gold-validation-2026-10-13.csv`](../evidence/silver/issue-109-115-gold-validation-2026-10-13.csv).

### Run on October 12, 2026 (issues #116 and #119)

Gold `03`, `04`, and `07` ran on Databricks serverless compute in the team workspace, on commit `ff7cacc` of branch `feature/issues-116-117-118-119-120-121`. Before that, `05_silver_project` ran on `silver_project_v6`, and the project-dependent Silver notebooks reran. Every Silver validator passed every STOP check. Gold `00`, `01`, `02`, `05`, and `06` did not rerun, because they do not read project data.

`07` ran twice. Times come from the Delta table history.

| Run | Delta version | Time (UTC) | Rows inserted | Rows updated | Rows set not current |
| --- | ---: | --- | ---: | ---: | ---: |
| `07` run 1 | 33 | 11:55:04 | 0 | 265,656 | 0 |
| `07` run 2 | 35 | 13:20:32 | 0 | 265,656 | 0 |

Both runs used the single `MERGE` from #116. Neither run inserted or deleted a row. No row was set not current, because the fact holds one snapshot. Both runs wrote the same number of bytes and gave the same values:

| Measure | Value |
| --- | --- |
| Fact rows | 265,656 |
| Current rows | 265,656 |
| Current reported budget (PHP) | 6,535,616,688,962.02, equal to Silver |
| `delivery_rule_version` | `gold-delivery-v3\|long-running=start-to-completion-or-snapshot>24-months\|completion-before-start=null\|progress=silver-quality-VALID` |
| Current `run_id` | `1dc106b9c825034bb2bf258a6145b8773ab2cb745f2d2e54eb515d4ec332cdd2` |

Long-running after D-49, for current projects:

| Result | Projects |
| --- | ---: |
| True | 15,209 |
| False | 230,402 |
| `NULL`, no start date | 20,039 |
| `NULL`, completion before start (D-49) | 6 |
| Start date after the snapshot date | 0 |

The October 11 run had 230,408 false. The 6 projects with a completion before the start moved from false to `NULL`. The true count did not change.

`09_validation_gold` then ran once. All 65 STOP checks passed. 9 FLAG checks had findings, and 1 found nothing.

### Run on October 11, 2026 (issues #93, #97, #98)

Gold `00` to `07` ran twice on Databricks serverless compute, on commit `3da7665` of branch `gold/issues-93-97-98`. Before that, the project-dependent Silver notebooks reran once on `silver_project_v5` and their validators passed every STOP check. Times come from the notebook run metadata.

| Run | Notebooks | Start (UTC) | End (UTC) |
| --- | --- | --- | --- |
| Silver rerun | `05`, `07`, `08`, `10` and their validators | 10:11 | 11:27 |
| Gold run 1 | `00` to `07` | 11:27 | 12:37 |
| Gold run 2 | `00` to `07` | 12:39 | 13:25 |

No STOP check failed in either Gold run. Both runs gave the same row counts, totals, and run IDs. Each exported `MERGE` result shows updated rows and no inserted or deleted rows. The row counts did not change, so the second run added no duplicates.

| Table | Rows, run 1 | Rows, run 2 |
| --- | ---: | ---: |
| `dim_date` | 13,150 | 13,150 |
| `dim_region` | 19 | 19 |
| `dim_region_boundary` | 17 | 17 |
| `dim_flood_susceptibility` | 5 | 5 |
| `dim_project_status` | 35 | 35 |
| `dim_project` | 265,656 | 265,656 |
| `fact_region_population` | 18 | 18 |
| `fact_region_flood_exposure` | 72 | 72 |
| `fact_project_snapshot`, current snapshot | 265,656 | 265,656 |

Silver run IDs in `dim_region` and `dim_region_boundary` (#93): every row carries one `psgc_run_id` and one `exposure_run_id`, and none is missing. Both equal the current Silver runs.

| Column | Value |
| --- | --- |
| `psgc_run_id` | `0b65c728d2436e0efe02825f2358c0eac765d5e76dc938518f519962a1f2aaa8` |
| `exposure_run_id` | `423a78d92beeeea9c36888d8fb27a43466a1f6c7ce16b9eb303b0aa645946afb` |

Project coverage (#97), with 265,656 projects as the denominator:

| Measure | Projects |
| --- | ---: |
| `infra_type_mapping_status = MAPPED_SINGLE` | 243,943 |
| `infra_type_mapping_status = MAPPED_MULTI` | 1,217 |
| `infra_type_mapping_status = MISSING_SOURCE_CATEGORY` | 20,496 |
| `is_dpwh_flood_related` true | 35,147 |
| `is_dpwh_flood_related` false | 210,013 |
| `is_dpwh_flood_related` `NULL` | 20,496 |
| `implementing_office` filled | 265,559 (221 offices) |
| `implementing_office` `NULL` | 97 |
| `implementing_office` different from Silver | 0 |

Projects by standardized status and group, current snapshot:

| Status | Group | Projects |
| --- | --- | ---: |
| Completed | `FINISHED` | 214,535 |
| Ongoing | `ACTIVE` | 49,095 |
| Inactive | `INACTIVE` | 1,924 |
| `NULL` | `NULL` | 102 |

The 102 projects without a status are 76 on `status_key` 0 (blank status) and 26 with a shifted source value.

Gold totals equal Silver:

| Measure | Gold | Silver |
| --- | ---: | ---: |
| Projects | 265,656 | 265,656 |
| Reported budget (PHP) | 6,535,616,688,962.02 | 6,535,616,688,962.02 |
| Population | 112,722,987 | 112,722,987 |
| Flood area (sq km) | 44,218.7219 | 44,218.7219 |

Long-running (#98): `silver_project` has no long-running column, and its rule version is `silver_project_v5`. `fact_project_snapshot.long_running_flag` is true for 15,209 current projects, false for 230,408, and `NULL` for 20,039. The true count equals the October 8 run.

Run IDs, the same in both runs:

| Table | `run_id` |
| --- | --- |
| `silver_project` | `704d8ed884b482f8c972d72bf27c4640f6121bfb6900d0a925ae617104d0f13e` |
| `dim_region` | `0e4a50bd17f0d38d46c35e1a6f636775e4c12e14c113b34147559209199f7f09` |
| `dim_project` | `43279e1e4b1d876819a9193873ef9dae915e819fb81872d45b4083ebe8ffc3a7` |
| `fact_project_snapshot`, current | `185190695a2153a9cd67c5055a5542993ef7280aadde3f77cf9cf4543b911ac4` |

## Settled questions

1. **How do we generate surrogate keys?** With deterministic hashes. See [Surrogate keys](#surrogate-keys) and D-33.
2. **What date range does `dim_date` cover?** January 1, 2000 to December 31, 2035. Key `0` stands for a missing date.
3. **Which dimensions get an unknown row?** `dim_date`, `dim_region`, `dim_project_status`, and `dim_flood_susceptibility`. `dim_project` does not need one. See [Unknown and non-geographic records](#unknown-and-non-geographic-records).
4. **How do we refresh `is_current_snapshot`?** The project fact merges each snapshot by `project_key` and `source_snapshot_id`. The same `MERGE` sets `is_current_snapshot` to false on every row outside the snapshot that Silver holds now. One `MERGE` is one commit, so a failed run cannot leave two current rows. Before it, the load stops when Silver holds an older snapshot than the fact, so the current snapshot is always the newest one. A rollback to an older snapshot needs its own decision (#116).
