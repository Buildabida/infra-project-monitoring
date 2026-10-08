# Silver configuration review summary

## Outcome

The repository now contains the first implemented Silver milestone.
It creates five governed mapping tables and a layer-specific validator.

The implementation is intentionally narrow.
It does not transform Bronze or build Gold outputs.

## Implemented tables

| Table | Initial state |
| --- | --- |
| `config_place_name_alias` | Empty pending approved context-specific aliases |
| `config_project_category_mapping` | Empty pending approved taxonomy decisions |
| `config_project_status_mapping` | Five approved DPWH status rules, version `dpwh-status-2026-10-v1` (D-40) |
| `config_mgb_susceptibility_mapping` | Four approved documented code mappings |
| `config_manual_geographic_match` | Empty pending approved exceptions |

All tables use deterministic composite natural keys.
No random mapping identifier is generated.

The MGB seed uses `MERGE` and a fixed mapping version.
An exact rerun does not append duplicate rules.

## Approved initial mapping

Only these source-supported MGB rules are seeded:

| Raw code | Standard level | Rank |
| --- | --- | ---: |
| `LF` | Low | 1 |
| `MF` | Moderate | 2 |
| `HF` | High | 3 |
| `VHF` | Very High | 4 |

Blank values and `No rating` remain unmapped.
The team must approve any future interpretation.

D-40 later approved DPWH status mapping `dpwh-status-2026-10-v1`. It seeds five rules:
`Completed` to `Completed` (`FINISHED`), `On-Going` and `For Procurement` to
`Ongoing` (`ACTIVE`), and `Not Yet Started` and `Terminated` to `Inactive`
(`INACTIVE`). Blank and malformed statuses remain unmapped.

No category, place, or manual geographic rule was invented.

## Validation design

The Silver config validator checks all seven project quality attributes:

- consistency
- accuracy limits
- completeness through mapping coverage
- auditability
- validity
- uniqueness
- timeliness through explicit versions

Structural errors produce blocking `FAIL` results.
Unmapped and pending source values produce review `FLAG` results.

The validator writes to `04-validation.silver_config_dq_results`.
This keeps Silver lineage without changing the fixed Bronze result writer.

An empty manual override table is valid.
Its flag confirms that no exception has been approved.

## Low-cost and scaling review

The five configuration tables are small Delta tables.
They do not use partitions, caching, `OPTIMIZE`, or `ZORDER`.

Coverage queries group only distinct mapping domains.
The large MGB source is grouped once per notebook run.

The implementation does not use streaming, Pandas, Python UDFs, or spatial functions.
Later Silver transformations can reuse these mappings by version.

This structure scales because rules are centralized and independently reviewable.
It also prevents transformation notebooks from accumulating hidden `CASE` expressions.

## Local dataset verification

`/Users/franziellenadinecanquin/datasets` was accessible during implementation review.

The six identified files were:

| Local file | Bronze source |
| --- | --- |
| `dpwh_projects.csv` | `01-bronze.dpwh_projects` |
| `flood_control_projects.csv` | `01-bronze.flood_control_projects` |
| `psgc.csv` | `01-bronze.psgc` |
| `population_2024_table_c_test.csv` | `01-bronze.census_2024_table_c` |
| `boundary_bettergov.csv` | `01-bronze.boundaries` |
| `flood_susceptibility.csv` | `01-bronze.flood_susceptibility` |

The following fields informed the five configuration contracts:

| Config | Profiled fields |
| --- | --- |
| Place aliases | DPWH `reported_region`, flood-control place fields, PSGC references, and Table C place name |
| Project categories | DPWH `category` plus flood-control `infra_type` and `type_of_work` |
| Project statuses | DPWH `status` |
| MGB susceptibility | MGB `flood_susceptibility_code` |
| Manual geographic matches | Source record IDs, reported place fields, coordinates, and PSGC reference fields |

The local project extracts do not match the accepted Bronze evidence exactly.
The local DPWH file had 265,582 rows, while accepted Bronze had 265,661.
The local flood-control file had 9,855 rows, while accepted Bronze had 9,861.

PSGC, Table C, boundary, and MGB row totals matched earlier references.
The local MGB content still differed from the accepted evidence profile.

Therefore, the local directory is not claimed as the selected Bronze snapshot set.

Observed source values supported only the four MGB code mappings.
The DPWH status values were also profiled as source candidates.
They included Completed, On-Going, For Procurement, Terminated, and Not Yet Started.

Those status values do not establish approved standardized targets.
The earlier profile also found 581 DPWH category values.
They still require taxonomy review.

Human approval is still required for:

- project category targets
- standardized project status targets
- context-specific place aliases
- `Region IV-B` and `MIMAROPA` handling
- ambiguous names such as `Poblacion`
- manual geographic overrides
- blank or `No rating` MGB values

## Verification completed locally

- Both notebooks parse as valid notebook JSON.
- All 30 repository tests pass under Python 3.12 and pytest 9.1.1.
- Ruff reports no issues.
- Ruff formatting passes.
- Extracted SQL passes SQLFluff 4.3.0 with the repository rules.
- Markdownlint reports no errors.
- Git whitespace checks pass.

## Required Databricks verification

The notebooks were not executed against Unity Catalog from this local task.

Before approval, run both notebooks in Databricks.
Confirm that all five tables exist and every `stop` check passes.
Review the expected coverage flags before another Silver notebook consumes the mappings.

## Review recommendation

The repository package is ready for a focused Silver configuration pull request.
Merge only after Databricks execution confirms the SQL against current Bronze tables.
