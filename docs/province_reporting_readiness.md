# Province reporting readiness and production status

## Decision status

Option B is approved as D-55 on October 14, 2026. D-34 remains approved for the
regional model and its existing consumers, but D-55 supersedes D-34's earlier
restriction against building a province drill-down.

The governed reporting areas are:

- official PSGC provinces;
- cities with no province parent in the selected PSGC hierarchy, classified as
  `INDEPENDENT_CITY`;
- NCR as one `NCR` reporting area;
- reserved key `0` as `UNKNOWN`.

Region remains the parent, reconciliation level, fallback for existing regional
consumers, and the level used for national, BARMM, and lineage checks. The new
name is deliberately `province_reporting_area`: not every member is a province.

## Runtime status

Production notebooks and local contract tests are implemented. Databricks runtime evidence
is still pending. No project coverage, reported-budget
coverage, population coverage, row count, or runtime success is claimed by this
document.

The retained readiness profiler is
`notebooks/02_silver/08b_profile_project_province_readiness.ipynb`. It remains a
read-only diagnostic. It creates temporary views only and is useful before a
production rerun for reviewing source values, boundary compatibility, NCR,
BARMM, and cities without province parents.

## Source findings carried into production

- DPWH `location.province` is preserved source evidence. It can hold District
  Engineering Office text and is never trusted as a PSGC key.
- Exact official-name evidence is diagnostic until an active approved alias
  authorizes the source value.
- No fuzzy, substring, nearest-boundary, first-candidate, or proportional rule
  is allowed.
- Spatial matching uses longitude-first EPSG:4326 points and `ST_COVERS` over
  selected valid reporting-area boundaries.
- Zero boundary candidates remain unmapped. Multiple candidates remain
  ambiguous. Name-coordinate disagreement remains a conflict.
- Pending and inactive configuration never participates.

## Approved matching precedence

1. Explicit non-geographic classification.
2. Approved manual exception.
3. Valid and uniquely resolved project PSGC evidence, when a legitimate source
   field exists. The current canonical project contract has none.
4. Approved exact source-name alias.
5. Unique coordinate containment in one approved reporting-area boundary.
6. Unknown, unmapped, or ambiguous.

Every candidate path aggregates back to one project before publication.
`silver_project_province_map` asserts that project count, unique project count,
mapping-key count, and reported-budget total reconcile to `silver_project`.

## Population contract

`silver_province_reporting_area_population` aggregates only positive Table C
rows whose reconciliation disposition is `ACCEPTED_PRIMARY` and whose matched
place type is `BARANGAY`. Province, city, municipality, region, and other
subtotal rows never enter the measure.

NCR barangays roll to NCR. Barangays with a province parent roll to that
province. A barangay whose city has no province parent rolls to that independent
city. Accepted rows that cannot resolve remain under key `0`. Missing population
stays `NULL`; it is never converted to zero. Accepted population is reconciled
before and after aggregation, and excluded or unresolved diagnostics remain
visible.

## Production outputs

Silver:

- `silver_province_reporting_area`
- `silver_province_reporting_area_boundary`
- `silver_province_reporting_area_population`
- `silver_project_province_map`

Gold:

- `dim_province_reporting_area`
- `dim_province_reporting_area_boundary`
- `fact_province_reporting_area_population`
- `fact_project_snapshot.reporting_area_key`, while retaining `region_key`

Analytics:

- `analytics_reporting_area_investment`
- `analytics_reporting_area_category`
- `analytics_reporting_area_delivery_status`
- `analytics_reporting_area_population_equity`
- `analytics_reporting_area_project_size_concentration`

The regional views remain unchanged for reconciliation and backward
compatibility. Reporting-area Analytics includes Unknown where national totals
must reconcile. Population equity uses one disclosed comparable-area set for
both investment and population denominators; it is descriptive and is not a
fairness judgment.

## Deterministic lineage and reruns

The project mapping run ID includes the selected project snapshot, project run,
project ingest run, PSGC version and run, boundary version and run, approved
alias and manual-config versions, and mapping-rule version. The mapping key is
an `XXHASH64` of the fixed mapping label, unchanged `project_key`, and that run
ID. An exact rerun therefore produces the same key and run ID; any governed
input or rule change changes the run identity.

Gold uses deterministic keys and idempotent `MERGE`. Analytics uses `CREATE OR
REPLACE VIEW`. Each validator merges deterministic evidence before its STOP
gate, so a failure remains reviewable.

## Province flood exposure

Province-level flood exposure is deferred. The readiness package contains no
Databricks evidence that the province-boundary and MGB intersection is safe and
affordable on Free Edition. The implementation does not allocate regional flood
exposure to reporting areas and does not reparse MGB geometry merely to claim
feature parity. A later implementation must reuse `silver_mgb_flood_area`, use
only valid selected reporting-area boundaries, intersect once, dissolve to the
final grain, and validate additivity and lineage.

## Evidence required from Databricks

After the documented rerun, capture persisted Silver, Gold, and Analytics DQ
rows plus:

- total, mapped, and unmapped projects and their percentage;
- total, mapped, and unmapped reported budget and its percentage;
- mappings by method, conflicts, ambiguity, and missing coordinates;
- NCR, independent-city, and BARMM totals;
- population coverage and excluded or unresolved population;
- selected PSGC, boundary, config, and rule versions;
- exact rerun results proving stable keys and run IDs.

Coverage does not need to be 100%. It must be honest, reconciled, and visible.
