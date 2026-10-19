# Silver project-to-reporting-area mapping

## Purpose and name

`02-silver.silver_project_province_map` publishes one D-57 reporting-area result
for every canonical DPWH project. The table keeps `province_map` in its name for
discoverability, but its target can be an official province, an independent
city, NCR, or Unknown. It must not be described as a strict province map.

## Grain

One canonical project per selected project snapshot, PSGC version, boundary
version, approved configuration version, and mapping-rule version.

The final table contains exactly one row per `project_key`. Candidate views may
fan out temporarily, but each candidate stage counts distinct targets and
aggregates back to the project before the final join. The publication assertion
requires:

- final rows equal `silver_project` rows;
- final rows equal distinct `project_key` values;
- mapping keys are unique and reproduce from their documented recipe;
- the joined reported-budget total equals `silver_project` with NULL-safe
  equality.

`project_key` is never changed.

## Approved reporting areas

`silver_province_reporting_area` contains:

- official PSGC provinces as `PROVINCE`;
- PSGC cities with no province parent, excluding NCR, as `INDEPENDENT_CITY`;
- NCR as one `NCR` member;
- key `0` as `UNKNOWN`.

Every geographic member keeps its PSGC parent region. Region remains available
for reconciliation, BARMM checks, and existing consumers.

## Matching precedence

1. Explicit non-geographic classification.
2. Active approved manual exception.
3. Valid, uniquely resolved project PSGC evidence, when available. The current
   canonical project contract has no legitimate project PSGC field, so this
   stage is unavailable rather than guessed.
4. Active approved exact source-name alias whose `match_rule` is
   `DPWH_PROVINCE_REPORTING_AREA`.
5. Unique coordinate containment in one valid reporting-area boundary.
6. Unknown, unmapped, invalid, or ambiguous.

Raw `location.province` is preserved and normalized with uppercase, trim, and
repeated-whitespace collapse for exact comparison. It never authorizes a target
by itself. A District Engineering Office value therefore remains unresolved
unless a reviewed config row explicitly maps that exact source value.

There is no fuzzy, substring, nearest-boundary, first-candidate, or arbitrary
allocation rule.

## Spatial contract

The one project-to-boundary join uses only `VALID_BOUNDARY` rows. It constructs
`ST_POINT(longitude, latitude, 4326)` and applies `ST_COVERS`. Zero candidates
stay unmapped. More than one distinct candidate stays ambiguous. A selected name
or manual result that disagrees with a unique coordinate candidate remains
selected by precedence but publishes `MATCHED_WITH_CONFLICT` and
`conflict_flag = true`.

## Configuration contract

The implementation reuses `config_place_name_alias` and
`config_manual_geographic_match`; it does not seed aliases from profiling.
Existing DPWH region aliases do not participate because province aliases require
the distinct match rule `DPWH_PROVINCE_REPORTING_AREA`.

Before mapping, assertions require:

- no more than one active approved alias or manual version;
- unique source values and project IDs at the governed version grain;
- nonblank, nongeneric source identifiers;
- every target code to exist in the selected reporting-area reference;
- province aliases to target `PROVINCE`, city aliases to target
  `INDEPENDENT_CITY`, and region aliases to target `NCR`;
- only `APPROVED` and active rows to participate.

An empty approved alias set is safe. Coordinate evidence and manual exceptions
can still operate, and all other projects remain visible under key `0`.

## Outputs and lineage

The table publishes the source province value, normalized value, coordinate and
candidate counts, selected area and parent region, method, status, quality,
reason, conflict flag, project snapshot and run lineage, PSGC and boundary
versions and runs, config and rule versions, deterministic `run_id`, and source
load timestamp.

The mapping run ID is SHA-256 over the selected project snapshot, project run,
project ingest run, PSGC version and run, reporting-area boundary run, boundary
version and ingest run, approved alias version, approved manual version, and
mapping-rule version. The mapping key is `XXHASH64` of the fixed mapping label,
`project_key`, and the mapping run ID. An exact rerun preserves both; any
governed input or rule-version change changes the run identity.

## Validation and evidence

`03b_validation_silver_province_reporting` persists evidence before its STOP
gate. STOP checks cover final grain, key uniqueness, target integrity, lineage,
project count, reported budget, reporting-area reference and boundary grain, and
population reconciliation. FLAG checks retain missing coordinates, zero or
multiple spatial candidates, conflicts, unresolved areas, NCR,
independent-city, and BARMM findings.

Databricks runtime evidence passed on October 15 and October 16, 2026. See the
[province-reporting evidence](../evidence/province-reporting/README.md) and the
[six Analytics views evidence](../evidence/six-analytics-views/README.md). Coverage
does not need to be 100%; it must reconcile to the national project and
reported-budget totals.

## Gold handoff

Gold joins this table once by `project_key` and carries `reporting_area_key` plus
the match status, method, and quality into `fact_project_snapshot`. The existing
`region_key` remains. Gold asserts one current fact row per canonical project
and equality of the reported-budget total before its `MERGE`.
