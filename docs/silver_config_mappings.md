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
| Category, status, and place decisions | Pending human review |
| Remaining Silver output tables | Planned |
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

The initial table is empty.
Observed categories remain review candidates rather than guessed taxonomy rules.

### Downstream readiness

`silver_project` may preserve raw project categories before the taxonomy is
complete, but category-standardized analytical outputs must not be published
until:

1. an approved taxonomy version exists,
2. applicable mappings are active,
3. mapping coverage has been reviewed and accepted by the team.

Downstream notebooks must not introduce temporary `CASE WHEN` category rules to
bypass this configuration.

Unmapped categories must remain visible as `Unknown` or unmapped according to
the downstream mapping contract and must remain included in coverage reporting.

### `config_project_status_mapping`

Grain: one source status per mapping version.

Natural key:

- `source_system`
- `source_status`
- `status_mapping_version`

The initial table is empty pending approval.

No canonical standardized-status vocabulary has been approved yet.
Downstream Silver transformations must consume only active, approved rows from
`config_project_status_mapping` and must not recreate temporary status mappings
independently.

Observed source statuses remain review candidates until the team approves their
standardized values and status groups.

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

It uses a separate table because the existing Bronze writer has a fixed result schema.
Changing that shared table now could break Bronze validation.

`stop` checks cover:

- required table presence
- natural-key uniqueness
- controlled approval values
- required mapping versions
- decision evidence for approved rows
- category source-field validity
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

This milestone does not implement place matching, category standardization, or status standardization.
It only provides their governed configuration boundary.

The local source folder was profiled during design.
Its project row counts differ from the accepted Bronze evidence.
Therefore, local values are not claimed to be the exact selected Bronze snapshots.

Run the notebooks against current Databricks Bronze tables before approving downstream use.
