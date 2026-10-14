# Province reporting readiness

## Status

Runtime status: not run in Databricks.

D-34 remains approved. It keeps the capstone at regional level and leaves
province drill-down unbuilt. The proposed D-55 in `docs/decisions.md` does not
supersede D-34 until the team approves it.

This change is a pre-decision evidence package. It adds one read-only profiler
and no persistent Silver, Gold, Analytics, or validation table.

## Current architecture reviewed

The current pipeline keeps one canonical DPWH project in
`02-silver.silver_project`, maps it once to a governed region, and carries the
region key into Gold. Region also owns population reconciliation and safe flood
exposure. The project fact keeps one row per canonical project snapshot and
protects the reported-budget total.

The province extension must preserve that architecture:

```text
Bronze source evidence
    -> canonical Silver project
    -> governed project-to-province or reporting-area map
    -> Gold geography dimension and project fact key
    -> validated provincial Analytics views
```

Region remains the parent geography, national reconciliation level, unresolved
project fallback, and existing consumer contract.

## Problem found

The current contracts cannot safely publish provincial Analytics yet:

- D-34 explicitly keeps the capstone at region level.
- DPWH `location.province` is inside preserved source JSON, but it is not a
  canonical Silver field and may contain a District Engineering Office.
- `silver_psgc_place` identifies official provinces and cities, but it does not
  classify cities as highly urbanized or independent component cities.
- NCR has no official province.
- The boundary snapshot can differ from the selected PSGC hierarchy.
- No approved province alias, manual exception, precedence, reporting-area
  policy, or unknown-member contract exists.
- No provincial project or reported-budget coverage evidence has been run.

These are governance and source-contract gaps, not reasons to guess a province.

## Reporting-grain decision

### Option A: strict official provinces

The dimension contains only official PSGC provinces plus the repository's
governed unknown member.

Tradeoffs:

- simple and administratively precise.
- NCR has no province.
- HUC and independent-city projects may remain outside comparisons.
- national project, budget, and population coverage will be incomplete.
- comparisons need explicit exclusions and denominators.

### Option B: governed province reporting areas

Recommended when the analytical goal is nationally comparable coverage.

The dimension may contain official provinces, explicitly approved independent
city areas, NCR, and one unknown member. It must be named
`dim_province_reporting_area`, not `dim_province`, because not every member is a
province. A governed `reporting_area_type` distinguishes `PROVINCE`,
`INDEPENDENT_CITY`, `NCR`, and `UNKNOWN`.

Tradeoffs:

- supports a clearer national comparison.
- requires an approved HUC and independent-city classification source.
- requires explicit population and boundary aggregation rules.
- is a reporting construct and must not be described as the official province
  hierarchy.

Expected project, reported-budget, and population coverage remain unknown until
the profiler runs and the selected policy is applied. Do not insert an estimated
or target percentage.

## Proposed decision text

The exact proposed text is also recorded as proposed D-55:

> Use governed province reporting areas as the primary province-level analytical
> grain. The dimension contains official PSGC provinces, NCR, explicitly
> approved highly urbanized or independent-city reporting areas, and one unknown
> member. `reporting_area_type` states which contract each member follows.
> Region remains the parent, reconciliation, fallback, and backwards-compatible
> analytical geography. DPWH province text is source evidence only. Production
> matching uses approved exact evidence and unique `ST_COVERS` containment. It
> never uses fuzzy, substring, nearest-place, or arbitrary allocation. This
> extends D-34 only after the readiness profile, coverage review, and team
> approval are complete.

Approval must record the reviewer, date, profile run ID, selected PSGC and
boundary versions, and accepted coverage limitations.

## Read-only profiling contract

Run `notebooks/02_silver/08b_profile_project_province_readiness.ipynb` only after
the current Bronze, Silver project, PSGC, boundary, and project-region checks
pass.

The final temporary view has this grain:

```text
one canonical project
per selected project run
per selected PSGC snapshot
per selected boundary snapshot
```

The profiler:

- extracts DPWH `location.province` from preserved source JSON.
- normalizes case and repeated whitespace for exact comparison only.
- keeps missing and conflicting source values visible.
- matches exact official province names as candidate evidence only.
- parses the selected province boundaries once.
- constructs points longitude-first with SRID 4326.
- uses `ST_COVERS` without nearest-place or fuzzy matching.
- counts zero, one, and multiple province candidates.
- compares exact-name and coordinate evidence.
- aggregates candidate fan-out back to one row per project.
- asserts project count and reported-budget totals are unchanged.
- reports NCR and BARMM separately.
- reports that HUC versus independent-city classification is unavailable in the
  current Silver contract.
- reports PSGC and boundary-version gaps.
- lists nonofficial source province values for human review.

It creates temporary views only. It does not write runtime evidence to the
repository or create a production map.

## Required result capture

Export these result sets with the Databricks workflow run ID and execution date:

1. overall project and reported-budget coverage.
2. evidence groups and their reported-budget totals.
3. NCR, BARMM, and other-region results.
4. boundary-versus-PSGC gaps.
5. city rows without an official province parent.
6. nonofficial DPWH province text values.

Record unexpected values without converting them into rules. In particular,
District Engineering Office names, blank text, generic labels, and conflicting
name-coordinate evidence stay unresolved until a reviewed rule exists.

## Recommended governed rules after approval

The production mapping should apply this precedence only after each applicable
stage has an approved contract:

1. explicit non-geographic classification.
2. approved manual exception.
3. verified project PSGC evidence, if a legitimate field becomes available.
4. approved exact province or reporting-area alias.
5. unique coordinate containment in one approved boundary.
6. unknown, unmapped, or ambiguous.

Raw source province text must not act as a foreign key. A name-coordinate
conflict must preserve both candidates and publish a conflict status. Multiple
spatial candidates must remain ambiguous. Zero candidates must remain unmapped.

## Deferred production scope

Until D-55 or an alternative decision is approved, do not add:

- `silver_project_province_map`.
- province or reporting-area population aggregation.
- province flood-exposure intersections.
- a province or reporting-area Gold dimension.
- a province key on `fact_project_snapshot`.
- provincial Analytics views.
- production province STOP gates.

Province flood exposure should remain a later phase unless the team explicitly
requires it. It is the highest-cost part of the design and must reuse parsed MGB
geometry rather than parse it again.

## Databricks execution checklist

1. Confirm latest Bronze and Silver validation evidence has no failed STOP check.
2. Run the readiness notebook as a workflow on Serverless compute.
3. Export all six required result sets and note the workflow run ID.
4. Verify the project total equals `silver_project`.
5. Verify the reported-budget total equals `silver_project` with NULL-safe
   equality.
6. Review zero and multiple spatial candidates.
7. Review exact-name and coordinate conflicts.
8. Review NCR, BARMM, and no-province city evidence.
9. Review boundary-versus-PSGC version gaps.
10. Choose Option A or Option B and approve the exact decision text.
11. Only then design the production Silver, Gold, Analytics, and validation
    notebooks.

## Readiness conclusion

Provincial Analytics is not ready for use. The repository now has deterministic
profiling SQL and local contract tests, but it has no Databricks runtime results
and no approved reporting grain.
