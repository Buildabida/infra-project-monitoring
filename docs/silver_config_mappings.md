# Silver configuration mappings

This document covers the first implemented Silver milestone.
It creates controlled mapping tables without transforming Bronze rows.

## Why configuration is separate

Mapping decisions change at a different pace from transformation code.
Versioned tables make those decisions reviewable, reusable, and traceable.

Silver transformations must consume active `APPROVED` rows only.
They must not treat `PENDING_REVIEW` rows as accepted rules.
`DEPRECATED` rows remain as history but are not active inputs.

## Implementation status

| Item | Status |
| --- | --- |
| Five configuration tables | Implemented by the Silver config notebook |
| Configuration validation | Implemented by the Silver config validator |
| DPWH component-category taxonomy | Implemented as approved taxonomy `dpwh-component-categories-2026-10-v1`. Databricks rerun required. |
| DPWH status mapping | Implemented as approved mapping `dpwh-status-2026-10-v1` (D-40). Databricks rerun required. |
| Place decisions | Pending human review |
| PSGC and population Silver outputs | Implemented in separate notebooks. Databricks execution is required. |
| Project, source-reconciliation, project-region, and regional flood-exposure Silver outputs | Implemented in separate notebooks. Databricks execution is required. |
| Project-flood Silver mapping | Implemented in a separate notebook and runtime-validated in Databricks for the selected snapshots. |
| Gold facts and dimensions | Planned |

## Run order

1. Run `notebooks/00_setup/00_setup_workspace.sql` if the schemas do not exist.
2. Run `notebooks/02_silver/00_config_mappings.ipynb`.
3. Review the mapping coverage output.
4. Run `notebooks/04_validation/02_validation_silver_config.ipynb`.
5. Resolve every failed `stop` check before another Silver notebook uses these tables.

The notebooks require Databricks and Unity Catalog.
Local tests validate their structure but do not create Delta tables.

## Table contracts

### `config_place_name_alias`

Grain: one context-specific source alias per alias version.

Natural key:

- `source_system`
- `raw_place_name`
- `raw_region_name`
- `raw_province_name`
- `raw_city_municipality_name`
- `place_type`
- `alias_version`

An approved row must point to a valid Bronze PSGC code.
Blank context fields mean that the context was not supplied.
They do not authorize global name-only matching.

`Poblacion` is ambiguous without geographic context.
No global `Poblacion` alias is seeded.
`Region IV-B` to `MIMAROPA` also remains unseeded until the team approves it.

### `config_project_category_mapping`

Grain: one source category and infrastructure-type pair per taxonomy version.

Natural key:

- `source_system`
- `raw_category`
- `source_infra_type`
- `taxonomy_version`

At least one raw classification field must contain a value.
Approved targets require a documented mapping rule and source reference.

The `is_flood_related` field records whether an approved atomic source
classification is flood-related.

The approved DPWH taxonomy uses `componentCategories` extracted from the
preserved Bronze `source_record_json`. It does not require a Bronze reload or a
new top-level source column. The raw DPWH `category` remains source evidence
because it mixes infrastructure types with funding and program classifications.

Taxonomy `dpwh-component-categories-2026-10-v1` contains these approved atomic
values:

| Source infrastructure type | Standardized sector | Flood-related |
| --- | --- | --- |
| `Bridges` | Bridges | No |
| `Buildings and Facilities` | Buildings and Facilities | No |
| `Consultancy` | Consultancy | No |
| `Flood Control and Drainage` | Flood Control and Drainage | Yes |
| `Roads` | Roads | No |
| `Septage and Sewerage Plants` | Septage and Sewerage Plants | No |
| `Water Provision and Storage` | Water Provision and Storage | No |

Future values are not approved automatically. They remain unmapped until the
team reviews and versions the taxonomy.

### Key values for DPWH rules

Write DPWH category and status rules with these key values. The config validator checks coverage with them, and the DPWH component notebook joins on them.

| Field | Value for DPWH | Why |
| --- | --- | --- |
| `source_system` | `dpwh_projects` | It is the Bronze table name that the coverage check uses. |
| `raw_category` | `''`, an empty string | The mixed DPWH `category` value is not the taxonomy input. |
| `source_infra_type` | One trimmed atomic `componentCategories` token | Coverage and the component join use the same normalized token. |
| `source_status` | The Bronze status after `TRIM` | A blank status is `''`. |

Each active approved version may hold only one rule per complete category key or
source status. The component notebook stops if it finds two. This prevents a
mapping from copying a project row.

Silver output tables still label DPWH rows `source_system = 'DPWH'`. That label is for joins between Silver tables. It is not a config key.

### Downstream readiness

`silver_project` preserves the raw DPWH category and the normalized
`componentCategories` evidence. Category-standardized analytical outputs may be
published only when:

1. an approved taxonomy version exists,
2. applicable mappings are active,
3. mapping coverage has been reviewed and accepted by the team.

Downstream notebooks must not introduce temporary `CASE WHEN` category rules to
bypass this configuration.

Unmapped categories remain `NULL` with an explicit unmapped state. Gold may use
its reserved unknown key without replacing the Silver evidence. Coverage must
include mapped and unmapped projects and reported budgets.

### `config_project_status_mapping`

Grain: one source status per mapping version.

Natural key:

- `source_system`
- `source_status`
- `status_mapping_version`

Decision D-40 approves mapping version `dpwh-status-2026-10-v1`. The config notebook seeds it
with a deterministic `MERGE`:

| Source status | Standardized status | Status group |
| --- | --- | --- |
| `Completed` | `Completed` | `FINISHED` |
| `On-Going` | `Ongoing` | `ACTIVE` |
| `For Procurement` | `Ongoing` | `ACTIVE` |
| `Not Yet Started` | `Inactive` | `INACTIVE` |
| `Terminated` | `Inactive` | `INACTIVE` |

Blank, shifted, or malformed source statuses, such as numbers or place names,
get no rule. They stay `UNMAPPED` with `NULL` standardized values and remain in
coverage reporting as a review flag.

Project-level profiling for the decision found 265,656 projects: 265,580 with
one source status, 76 with a blank status, and 0 with conflicting statuses.

Downstream Silver transformations must consume only active, approved rows from
`config_project_status_mapping` and must not recreate temporary status mappings
independently. A change to any rule needs a new `status_mapping_version`.

`Delayed` is not a supported standardized status because the current sources
lack a reliable target completion date.

Long-running and stalled are future derived measures.
They do not belong in this mapping table.

### `config_mgb_susceptibility_mapping`

Grain: one raw MGB code per source-contract and mapping version.

Natural key:

- `source_system`
- `raw_susceptibility_code`
- `source_version`
- `mapping_version`

The initial approved rules are:

| Raw code | Standard level | Rank |
| --- | --- | ---: |
| `LF` | Low | 1 |
| `MF` | Moderate | 2 |
| `HF` | High | 3 |
| `VHF` | Very High | 4 |

The source did not publish a release identifier in the approved extract.
The value `unversioned-official-code-contract` makes that limitation explicit.

Blank values and `NO RATING` are not approved automatically.

The accepted Bronze snapshot currently exposes 6 observed susceptibility values.
Four have approved mappings (`LF`, `MF`, `HF`, and `VHF`), while 2 remain
unmapped: blank and `NO RATING`.

Until an approved mapping exists, downstream Silver must:

- preserve the original raw susceptibility value,
- leave the standardized susceptibility level unresolved (`NULL`),
- classify the mapping result as unmapped,
- and retain the condition as a non-blocking validation FLAG.

Do not silently convert blank or `NO RATING` to `Unknown`.

Gold may later resolve unknown or unmapped dimension relationships to the
reserved key `0`, following the dimensional-model contract.

### `config_manual_geographic_match`

Grain: one source-record override per mapping version.

Natural key:

- `source_system`
- `record_type`
- `source_record_id`
- `mapping_version`

This table is an exception path, not the default matcher.
It may remain empty.

Every approved row needs a stable source record identifier.
It also needs a PSGC target, reason, approver, version, and reference.

Example structure only. This is not an approved production mapping:

| source_system | record_type | source_record_id | original_location | target_psgc_code | target_place_name | match_reason | mapping_version |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `<source>` | `<record_type>` | `<stable_source_id>` | `<raw_location>` | `<approved_psgc_code>` | `<approved_place>` | `<reviewed_reason>` | `<mapping_version>` |

Actual overrides must be supported by reviewed evidence before
`approval_status = 'APPROVED'` and `is_active = true`.

## Approval workflow

1. Review distinct source values in the coverage output.
2. Confirm the intended target with the team or an authoritative source.
3. Add one controlled row to the configuration notebook.
4. Set a new version when the rule set changes.
5. Record `approved_by`, `approved_at`, and `source_reference` when available.
6. Rerun the configuration notebook and validator.
7. Keep old versions as history instead of silently rewriting decisions.

An active downstream join must include the intended version.
It must also require `approval_status = 'APPROVED'` and `is_active = true`.

## Validation behavior

The Silver config validator writes to
`04-validation.silver_config_dq_results`.

Its deterministic run ID includes the selected source snapshots, config
versions, and complete check result set. Exact reruns merge the same logical
evidence instead of appending duplicates.

It uses a separate table because the existing Bronze writer has a fixed result schema.
Changing that shared table now could break Bronze validation.

`stop` checks cover:

- required table presence
- natural-key uniqueness
- controlled approval values
- required mapping versions
- decision evidence for approved rows
- category source-field validity
- exactly one active approved DPWH taxonomy version
- no active approved category-rule fan-out at the complete mapping grain
- complete approved sector targets and flood markers
- the unsupported `Delayed` target
- MGB levels, ranks, and approved-row count
- PSGC target existence for approved geographic rules

`flag` checks cover:

- unmapped or pending Bronze categories
- unmapped or pending Bronze statuses
- unmapped or pending MGB codes
- an empty manual geographic override table

An empty manual table is valid.
Its flag only confirms that no exception has been approved.

## Cost controls

The mapping tables are small Delta tables.
They do not need partitions, caching, `OPTIMIZE`, or `ZORDER`.

Coverage queries group only the fields needed for review.
The large MGB table is grouped once per notebook run.
No Python UDF, Pandas conversion, streaming job, or spatial operation is used.

## Current limitations

This configuration notebook does not itself transform source rows.
The [Silver project foundation](silver_project_cleaning.md) consumes the approved
DPWH component-category taxonomy and status mapping `dpwh-status-2026-10-v1`.

The local source folder was profiled during design.
Its project row counts differ from the accepted Bronze evidence.
Therefore, local values are not claimed to be the exact selected Bronze snapshots.

Run the notebooks against current Databricks Bronze tables before approving downstream use.
