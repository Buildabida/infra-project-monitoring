# Silver Project Foundation

This milestone implements the DPWH project foundation layer.

It creates a row-preserving project component table and a project-level consolidation table.

These tables support implemented geographic matching and source reconciliation,
plus future delivery analysis, portfolio analytics, and Gold project facts.

This milestone does not implement:

- flood-control reconciliation
- project-region assignment within this foundation milestone. It is implemented
  by the follow-up Table 13 milestone
- flood-risk analysis
- Gold dimensions
- Gold facts
- population-adjusted metrics

## Source authority

DPWH Projects remains the authoritative source for:

- Contract IDs
- project descriptions
- project status
- project progress
- reported project budget
- source dates
- contractor information
- project coordinates

The production path remains:

```text
DPWH API
    ↓
Bronze
    ↓
Silver
```

Local files may support profiling and schema review, but the production notebooks do not depend on developer-specific file paths.

## Implementation status

| Item | Status |
| --- | --- |
| Five Silver configuration tables | Implemented |
| `silver_psgc_place` | Implemented |
| `silver_population_place_reconciliation` | Implemented |
| `silver_region_population` | Implemented |
| `silver_dpwh_project_component` | Implemented. Runtime-validated in Databricks on rule version v6 on Oct 12. |
| `silver_project` | Implemented. Runtime-validated in Databricks on rule version `silver_project_v7` (#110). See the [#110 evidence](evidence/silver/README.md#october-13-2026-coordinate-pairs-and-status-resolution-issue-110). |
| Silver project validation | Implemented. Validation version `silver_project_validation_v6` adds the #110 checks, for 43 checks, 27 of them STOP. All 27 STOP checks passed on the v7 run. All 25 STOP checks passed on the v6 run on Oct 12. |
| Flood-control component and source-match outputs | Implemented. Runtime-validated in Databricks on the v6 run on Oct 12. All 13 STOP checks passed. |
| `silver_project_region_map` and its validator | Implemented. Runtime-validated in Databricks on the v6 run on Oct 12. All 18 STOP checks passed. |
| `silver_project_flood_map` and its validator | Implemented in the follow-up project-flood milestone. Runtime-validated in Databricks for the selected snapshots. |
| Gold dimensions and facts | Implemented in `notebooks/03_gold`. See the [Gold model](gold_model.md). |

## Dependency order

Run the notebooks in this order:

1. `02_silver/00_config_mappings.ipynb`
2. `04_validation/02_validation_silver_config.ipynb`
3. `02_silver/04_silver_dpwh_project_component.ipynb`
4. `02_silver/05_silver_project.ipynb`
5. `04_validation/04_validation_silver_projects.ipynb`

When project or geography inputs changed and the foundation validator passes,
continue with:

1. `02_silver/07_silver_project_source_match.ipynb`
2. `04_validation/05_validation_silver_source_reconciliation.ipynb`
3. `02_silver/08_silver_project_region_map.ipynb`
4. `04_validation/06_validation_silver_project_region_map.ipynb`
5. `02_silver/10_silver_project_flood_map.ipynb`
6. `04_validation/08_validation_silver_project_flood_map.ipynb`

The flood-control component does not need a rerun when its selected source and
rule identity are unchanged. Its project match does need a rerun because it
stores the current `silver_project.run_id`.

Do not run a dependent notebook after a blocking failure.

## Bronze safety gate

Before Silver reads DPWH projects, it validates the latest terminal Bronze load.

The selected load must have:

- `SUCCESS` or `SKIPPED_IDEMPOTENT`
- a nonblank snapshot identifier
- positive loaded rows

The validator also confirms that the latest blocking Bronze validation contains no `FAIL` or `ERROR` results.

The gate reads audit evidence and validation outputs rather than rescanning source systems.

## `silver_dpwh_project_component`

Purpose: preserve every selected Bronze DPWH source row while safely parsing supported project fields and retaining source lineage.

Grain: one DPWH source record per selected source snapshot.

Primary key: `component_key`.

Source-row identity:

- `_source_snapshot_id`
- `source_row_hash`, a SHA-256 of every Bronze business field that Silver reads
- `source_row_ordinal`, which numbers rows that are identical on all of those fields

Bronze has no DPWH source row number. Identical rows are interchangeable, so the ordinal is the same on every run. `component_key` hashes the snapshot, the row hash, and the ordinal. It needs no random ID and no file order.

The component table preserves source evidence before project-level consolidation.

Repeated Contract IDs remain visible. The table does not use undocumented deduplication, `DISTINCT`, `dropDuplicates`, or arbitrary row-selection logic.

### Supported parsing

The component table preserves raw values and creates parsed values where possible.

Fields include:

- project description
- raw DPWH category
- `componentCategories` from `source_record_json`
- status
- reported budget
- physical progress
- start date
- completion date
- latitude
- longitude

Safe parsing uses `TRY_CAST`.

Invalid values remain visible and are not automatically corrected.

### Coordinate handling

The component table creates:

- `VALID_PAIR`
- `MISSING_PAIR`
- `PARTIAL_PAIR`
- `UNPARSEABLE`

Coordinate status is diagnostic only.

The table does not assign PSGC geography or perform spatial matching.

### Quality statuses

Each parsed field has a status, so a reader can tell why a value is `NULL` or suspect. Values stay as parsed. Silver flags them but does not change them.

| Column | Values |
| --- | --- |
| `budget_quality_status` | `VALID`, `MISSING`, `UNPARSEABLE`, `NEGATIVE` |
| `progress_quality_status` | `VALID`, `MISSING`, `UNPARSEABLE`, `OUT_OF_RANGE` |
| `infra_year_quality_status` | `VALID`, `MISSING`, `UNPARSEABLE` |

The progress range is 0 to 100, from the required analytical validation in [Data model](data-model.md#required-analytical-validation). It is declared once in the notebook's parameter view.

`infra_year` keeps the raw string. `infra_year_parsed` adds the integer, so Gold does not need to cast it.

`deo`, the District Engineering Office, is carried as raw text. It is part of `source_row_hash`, because the hash covers every Bronze field Silver reads. Adding it changes every `component_key` once, which is one reason the rule version moved to `silver_dpwh_component_v4`.

### Governed mapping join

Category and status rules join on the complete key values in
[Silver configuration mappings](silver_config_mappings.md#key-values-for-dpwh-rules).
The category join keeps the safeguards from PR #90 and uses
`source_system = 'dpwh_projects'`, `raw_category = ''`, and one normalized
`source_infra_type` token.

The component notebook extracts `componentCategories` once with
`GET_JSON_OBJECT(source_record_json, '$.componentCategories')`. It trims and
splits comma-separated values, removes blanks and duplicate tokens, and sorts
the remaining set. A temporary explode joins atomic tokens to the governed
config. The next aggregation returns immediately to one component row.

Classification rules are:

- one approved category becomes its approved sector,
- more than one approved category becomes `Multi-sector`,
- missing or unapproved categories remain `NULL` and unmapped,
- `is_dpwh_flood_related` is true when any approved component is
  `Flood Control and Drainage`, false when all usable categories are approved
  and non-flood, and `NULL` when classification is missing or unresolved.

The DPWH taxonomy flag is separate from official flood-list membership. Silver
does not infer one from the other.

`category_mapping_state` and `status_mapping_state` are `MAPPED` or `UNMAPPED`. An unmapped row keeps its raw value and a `NULL` standardized value.

### Component lineage

The table retains:

- `_source_snapshot_id`
- `_ingest_run_id`
- `_source_modified_at`
- `run_id`, a SHA-256 of the snapshot, taxonomy version, status-config version,
  and rule version
- `taxonomy_version`
- `transformation_rule_version`, now `silver_dpwh_component_v4`

These fields preserve traceability back to the selected Bronze snapshot.

## `silver_project`

Purpose: create one canonical project-level record suitable for downstream matching, portfolio analysis, delivery analysis, and future Gold project facts.

Grain: one project per Contract ID.

Natural key:

- `project_key`

The project table is built only from `silver_dpwh_project_component`.

It does not reread and independently clean Bronze data.

### Project consolidation

Component-level evidence is evaluated before a canonical value is published.

Resolution rules are:

| Distinct values | Outcome |
| --- | --- |
| 0 | Missing |
| 1 | Resolved |
| More than 1 | Conflict |

Conflicting values remain visible rather than being silently resolved.

### Coordinates resolve as one pair

Latitude and longitude resolve together, as one pair, from `VALID_PAIR`
component rows only. Both values publish, or neither does. Rows with a missing,
partial, or unparseable pair do not take part.

| Distinct valid pairs | `coordinate_resolution_status` | Published values |
| --- | --- | --- |
| 0 | `MISSING_OR_INVALID` | Both `NULL` |
| 1 | `RESOLVED` | That pair |
| More than 1 | `CONFLICT` | Both `NULL` |

`distinct_coordinate_pair_count` holds the number of distinct valid pairs.

Before issue #110, each value resolved on its own. Components (14.5, `NULL`)
and (`NULL`, 121.0) published (14.5, 121.0), a point that no source row
reported. Tables 13 and 15 then treated it as a valid pair. When the components
agreed on latitude but not longitude, the project published half a pair.

### Status publishes only when the raw status resolves

`standardized_status`, `status_group`, and `status_mapping_version` come only
from rows that report a raw status. They publish only when both are true:

- `status_resolution_status` is `RESOLVED`
- every row with that raw status carries the same approved mapping

Then `status_mapping_state` is `MAPPED`. Otherwise it is `UNMAPPED`, and the
three values are `NULL`.

Before issue #110, these values resolved on their own, and unmapped rows added
`NULL`, which a distinct count ignores. One `Completed` row and one malformed
row gave a `CONFLICT` raw status but still published `Completed`.
`status_mapping_state` could also be `NULL`, which is not a controlled value.

### Budget double-count protection

Repeated component rows must not inflate project investment values.

The table supports:

- resolved single budgets
- resolved repeated identical budgets
- conflicting budgets
- missing or invalid budgets

Multiple distinct budgets do not automatically become a summed project total.

### Same expression for count and value

Each attribute's distinct count and published value use the same expression. Before this change, `reported_region`, `contractor`, and `source_of_funds` counted untrimmed values but published trimmed ones. A value that differed only by spaces showed a count of 2 and still resolved.

Columns added for downstream use:

- `reported_region_resolution_status`, so Table 13 can tell a missing region from conflicting ones
- `infra_year_parsed` and `infra_year_resolution_status`
- `progress_quality_status` and `budget_quality_status`, carried from the component that holds the resolved value
- sorted source and approved category arrays
- `source_infra_type` and `standardized_sector`
- `taxonomy_version`, `category_mapping_state`, and
  `category_classification_status`
- `is_dpwh_flood_related`
- `source_system` and `component_run_id`
- `implementing_office`, `implementing_office_resolution_status`, and `distinct_implementing_office_count`, resolved from the DPWH `deo` field with the same missing, resolved, or conflict rule. Gold `dim_project.implementing_office` can read this column.
- `contractor_resolution_status`, beside `contractor` and `distinct_contractor_count`, with the same rule (#119). It tells a missing contractor from conflicting ones.

`project_key` uses the same recipe, so keys do not change.

Columns removed by D-44 (issue #98):

- `long_running_flag` and `long_running_rule_status`. The flag was always `NULL`, and no table read either column. Gold `fact_project_snapshot.long_running_flag` applies D-32 and is the only long-running flag. An empty Silver column could be read as "not long-running".

### Delivery-rule fields

The project table currently supports:

- `zero_progress_flag`

The project table leaves `stalled_flag` as `NULL`. Stalled is out of scope for the capstone (D-46).

The project table has no long-running flag. See D-44 and the [Gold model](gold_model.md#project-delivery-rules).

### Project lineage

The table retains:

- source snapshot identity
- source ingest identity
- deterministic project key
- deterministic run identity
- transformation rule version, now `silver_project_v7`. It moved from v5 to v6 when `contractor_resolution_status` was added (#119), and from v6 to v7 when coordinates and status resolution changed (#110).
- the component run it was built from

The rule version moved to `silver_project_v7` for issue #110, so `run_id` changed. Tables 13 and 15 check that they were built from the current project run. Rerun them and their validators after this notebook.

## Idempotency and cost

Stable identities use deterministic hashes and preserved lineage.

The implementation does not use:

- random UUID values
- streaming
- Python UDFs
- spatial functions
- cache or repartition operations
- unnecessary source scans

Tables are rebuilt using:

```sql
CREATE OR REPLACE TABLE
```

to avoid duplicate logical rows.

## Validation

`04_validation_silver_projects.ipynb` validates:

- Bronze-to-component row preservation
- component-to-project accounting
- project uniqueness
- budget resolution
- deterministic component-category extraction and classification
- taxonomy mapping coverage by project and resolved reported budget
- single-sector, multi-sector, missing-category, and flood-related counts
- lineage completeness
- source-quality findings

The validator covers all seven data-quality attributes. Each check shows its failed rows and its denominator. The full list is in [Data-quality checks](validation.md#silver-project-validation).

### Stop checks

Stop conditions include:

- empty component table
- Bronze-to-component and component-to-project row accounting
- duplicate component keys, Contract IDs, or project keys
- blank Contract IDs
- quality or mapping states outside the controlled values
- quality statuses that disagree with their values
- budgets that break the no-double-count rule
- category arrays or classification states that disagree
- project reported-budget totals that differ from the component resolution rule
- zero-progress flags that disagree with progress
- coordinates that are not one complete pair, or that differ from a component recount
- a standardized status published for an unresolved or unmapped raw status
- implementing office or contractor statuses that break the missing, resolved, or conflict rule
- mapped rows without a mapping version
- missing or non-reproducible keys, run IDs, and lineage
- more than one snapshot or run, or a snapshot that differs from the latest Bronze load

### Flag checks

Flag conditions include:

- missing or unapproved component categories and unmapped statuses
- coordinate exceptions
- projects whose components report more than one valid coordinate pair
- repeated identical source rows, kept and counted
- unparseable or negative budgets
- unparseable or out-of-range progress
- unparseable infrastructure years and dates
- conflicting project attributes

Flag findings remain visible for review.

## Runtime evidence

### Run on rule version 6

The code with `contractor_resolution_status` (#119) ran on Databricks on
October 12, 2026, on commit `ff7cacc`.

| Input | Value |
| --- | --- |
| Project rule version | `silver_project_v6` |
| Projects | 265,656 from 265,661 component rows |
| Projects without a usable budget | 87 |
| Resolved reported budget (PHP) | 6,535,616,688,962.02 |
| Projects with an approved status mapping | 265,554 |

Row accounting, budgets, and taxonomy coverage are the same as in the v5 run.

The resolution split that #119 asked for:

| Field | `MISSING` | `CONFLICT` |
| --- | ---: | ---: |
| Implementing office | 97 | 0 |
| Contractor | 19,142 | 0 |

All 97 projects without an office have no `deo` value at all. No project has
conflicting offices or conflicting contractors.

The validator and the project-dependent tables passed every STOP check:

| Table | Checks | STOP passed | FLAG with findings |
| --- | ---: | ---: | ---: |
| `silver_dpwh_project_component` and `silver_project` | 40 | 25 of 25 | 13 |
| `silver_project_source_match` and `silver_flood_control_component` | 23 | 13 of 13 | 6 |
| `silver_project_region_map` (Table 13) | 37 | 18 of 18 | 13 |
| `silver_project_flood_map` (Table 15) | 54 | 37 of 37 | 13 |

The project validator has one more STOP check than in v5: "Contractor follows
the resolution rule".

### Run on rule version 5

The current code, without the long-running columns (D-44), ran on Databricks on
October 11, 2026, on commit `3da7665`.

| Input | Value |
| --- | --- |
| DPWH snapshot | `metadata-6321c7aa6f2a14e12f4c` |
| Bronze load status | `SKIPPED_IDEMPOTENT`, 265,661 rows loaded |
| Component run ID | `2a62271eabc092b5938f42c2b8e0ea730df08a6f5491ff76d329a097122808e2` |
| Project rule version | `silver_project_v5` |
| Project run ID | `704d8ed884b482f8c972d72bf27c4640f6121bfb6900d0a925ae617104d0f13e` |

The project validator gate passed, so no STOP check failed. Row accounting,
budgets, taxonomy coverage, and implementing-office coverage are the same as in
the v4 run below. 265,554 projects now have an approved status mapping
(`dpwh-status-2026-10-v1`).

The project-dependent tables reran on this run, and their validators passed
every STOP check:

| Table | Checks | STOP passed | FLAG with findings |
| --- | ---: | ---: | ---: |
| `silver_project_source_match` and `silver_flood_control_component` | 23 | 13 of 13 | 6 |
| `silver_project_region_map` (Table 13) | 37 | 18 of 18 | 13 |
| `silver_project_flood_map` (Table 15) | 54 | 37 of 37 | 13 |

Table 13 and Table 15 results did not change. Table 13 has 266 unmatched and 306
non-geographic projects. Table 15 matched 112,710 of 215,138 projects with a
usable coordinate.

### Run on rule version 4

The current code, with the `dpwh-component-categories-2026-10-v1` taxonomy and
the implementing office, ran on Databricks on October 9, 2026.

| Input | Value |
| --- | --- |
| DPWH snapshot | `metadata-6321c7aa6f2a14e12f4c` |
| Bronze load status | `SKIPPED_IDEMPOTENT`, 265,661 rows loaded |
| Approved taxonomy versions | 1 |
| Approved status rules | 0 |
| Component run ID | `acc2632ac9afecbb1d4d36dd8e2ecc1a91928e91668fed37c5faf946c9a2e8bb` |
| Project rule version | `silver_project_v4` |
| Project run ID | `534df0f8a40784195e6932378cce725107b8b7d60b0ac4102ad05f154404468d` |

The validator wrote 39 checks to `04-validation.silver_dq_results`. All 24
STOP checks passed. Of the 15 FLAG checks, 13 reported findings and 2
(unexpected category tokens and negative budgets) found none.

Row accounting and every source-quality count are the same as in the v2 run
below: 265,661 component rows, 265,656 projects, 2 repeated identical rows,
2 projects with a conflicting attribute, 87 projects without a usable budget,
and PHP 6,535,616,688,962.02 resolved reported budget.

Taxonomy coverage, with 265,656 projects as the denominator:

| Measure | Projects | Reported budget (PHP) |
| --- | ---: | ---: |
| Mapped | 245,160 (92.28%) | 6,487,566,542,904.27 (99.26%) |
| Unmapped, missing `componentCategories` | 20,496 | 48,050,146,057.75 |
| Unmapped, unapproved category token | 0 | 0 |
| Single sector | 243,943 | |
| `Multi-sector` | 1,217 | |
| DPWH flood-related | 35,147 | 1,739,575,865,716.19 |

At the component level, 20,501 of 265,661 rows have no usable
`componentCategories` value, and every one of them is unmapped.

Implementing office, with 265,656 projects as the denominator:

| Measure | Projects |
| --- | ---: |
| One implementing office | 265,559 (99.96%) |
| No single implementing office (`MISSING` or `CONFLICT`) | 97 |
| Office breaks the resolution rule | 0 |

The pre-merge run found 100 component rows with a blank or missing `deo`. The
v4 component coverage query was not exported, so that count is not repeated
here.

### Earlier v2 run

The first Databricks run of the hardened foundation used these inputs:

| Input | Value |
| --- | --- |
| DPWH snapshot | `metadata-6321c7aa6f2a14e12f4c` |
| Bronze load status | `SKIPPED_IDEMPOTENT`, 265,661 rows loaded |
| Approved category and status rules | 0 and 0 |
| Component rule version | `silver_dpwh_component_v2` |
| Component run ID | `915af77484fcdb363d8a74146ab3e4ae8ed1d827c508241d0bd618e8ec0172cd` |
| Project rule version | `silver_project_v2` |
| Project run ID | `add5661e4e762ac48a270a437356933bc499a130186cc1f664561364face3449` |

The validator wrote 29 checks to `04-validation.silver_dq_results`. All 19
STOP checks passed. Of the 10 FLAG checks, 9 reported findings and 1 found
none.

### Row accounting

| Measure | Rows |
| --- | ---: |
| Bronze DPWH rows | 265,661 |
| Component rows | 265,661 |
| Distinct Contract IDs | 265,656 |
| Project rows | 265,656 |
| Component rows accounted for by projects | 265,661 |

- Two component rows are identical to an earlier row on every Silver field. They stay in the table and are counted.
- Two projects have at least one conflicting attribute.
- No project has conflicting budgets. 87 projects have no usable budget.
- The resolved reported budget across projects is PHP 6,535,616,688,962.02. It is a reported budget, not a payment.

### Component findings

The denominator is 265,661 component rows.

| Finding | Rows |
| --- | ---: |
| No approved category rule | 265,661 |
| No approved status rule | 265,661 |
| Missing, partial, or unparseable coordinate pair | 50,523 |
| Missing budget | 79 |
| Unparseable budget | 10 |
| Negative budget | 0 |
| Missing progress | 79 |
| Unparseable progress | 5 |
| Progress outside 0 to 100 | 17 |
| Missing infrastructure year | 94 |
| Unparseable infrastructure year | 11 |
| Unparseable start or completion date | 16 |

The missing counts are derived from the coverage query. They equal each
field's non-`VALID` rows minus its unparseable, negative, or out-of-range rows.

At the project level, 16 projects resolve to progress outside 0 to 100, and
255 projects have no single reported region.

The 50,523 coordinate exceptions include missing, partial, and unparseable
pairs. D-28 records 50,522 rows without coordinate pairs. This run does not
split the 50,523 by type, so the difference of one row is not yet explained.

The v2 run had no approved category rule, so every row was unmapped. The v4
run above replaces those category counts.

## Known limitations

- Projects with missing `componentCategories` remain unmapped. New source tokens
  remain unmapped until a reviewed taxonomy version approves them.
- Status uses approved mapping `dpwh-status-2026-10-v1` (D-40). Blank or malformed statuses stay `UNMAPPED`. The v5 run maps 265,554 projects. The v4 run predates the mapping.
- Project-region assignment is implemented separately. See
  [Silver project-to-region mapping](silver_project_region_mapping.md).
- Flood-control reconciliation is implemented separately. See [Silver source reconciliation](silver_source_reconciliation.md).
- Long-running classification lives in Gold only (D-44). Moving it to Silver, as D-38 intends over time, needs the DPWH snapshot date in Silver.
- Stalled is out of scope for the capstone (D-46). `stalled_flag` stays `NULL`, and `stalled_rule_status` is `STALLED_RULE_REQUIRED`, which means no rule is approved.
- 97 projects have no single implementing office. They stay visible with a `NULL` office and a `MISSING` or `CONFLICT` status. The v6 run on October 12 shows all 97 are `MISSING` and none is `CONFLICT`.
- Tables 13 and 15 reran on the `silver_project_v5` run on October 11, 2026, and both validators passed every STOP check. See [Run on rule version 5](#run-on-rule-version-5).
- The v6 run on October 12 changed the project `run_id`. The project validator, the source match, Tables 13 and 15 with their validators, and Gold `03`, `04`, and `07` reran after it, and every STOP check passed. See [Run on rule version 6](#run-on-rule-version-6).
- `silver_project_v7` (#110) changed the project `run_id` again. The project validator, the source match, and Tables 13 and 15 with their validators reran on it, and every STOP check passed. See the [#110 evidence](evidence/silver/README.md#october-13-2026-coordinate-pairs-and-status-resolution-issue-110). Gold `03`, `04`, and `07` have not rerun on v7.

## Open questions for the team

1. **Long-running rule location.** Resolved. D-32 computes the flag in Gold, and D-44 dropped the empty Silver column.
2. **Implementing office.** Resolved. DPWH Bronze has `deo`. The component table carries it, and `silver_project` publishes it as `implementing_office`.

## Gold handoff

`silver_dpwh_project_component` supports project reconciliation.

`silver_project` supports:

- implemented `silver_project_source_match`
- implemented `silver_project_region_map`
- implemented `silver_project_flood_map`
- future `dim_project`
- future `fact_project_snapshot`

Gold should not need to repeat:

- safe parsing
- project accounting
- repeated Contract-ID handling
- budget protection
- project conflict detection
- project lineage
- `componentCategories` JSON parsing or category-token normalization
- sector taxonomy or flood-related classification

After PRs #85 and #86 rebase, `dim_project` must consume these Silver-owned
fields directly:

- `source_infra_type`
- `standardized_sector`
- `taxonomy_version`
- `is_dpwh_flood_related`

Gold must keep `is_dpwh_flood_related` separate from
`is_in_official_flood_list`. It must not add a temporary `CASE` taxonomy. The
Gold `MAPPED` acceptance criterion remains pending until the rebased Gold
notebooks run and validate against this Silver output.
