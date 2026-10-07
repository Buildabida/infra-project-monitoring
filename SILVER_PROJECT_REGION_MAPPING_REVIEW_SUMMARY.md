# Silver project-region mapping review summary

## Outcome

The current `main` baseline now contains the complete static implementation for
Silver Table 13 and its validation gate.

Implemented output:

- `02-silver.silver_project_region_map`
- Table 13 checks in `04-validation.silver_dq_results`

Requires Databricks execution.

## Baseline reviewed

The supplied repository archive identifies commit
`a2e5ecabb80924f692236d6162e8eb0a3d640805`. A read-only remote check confirmed
that the same commit was the `main` branch head before implementation began.

Current main already contained Silver Tables 1 through 12. This milestone reads
their accepted contracts and does not redesign or recreate them.

## Files changed

The complete file list is in
`SILVER_PROJECT_REGION_MAPPING_CHANGE_MANIFEST.md`.

## D-03 resolution

D-31 resolves D-03 with a region-first, evidence-preserving waterfall:

0. exact Central Office non-geographic rule
1. active approved manual exception
2. exact verified project PSGC code when a legitimate field exists. It is currently
   unavailable
3. exact standardized official region name
4. active approved region alias
5. coordinate and region-boundary fallback
6. unresolved result

The historical D-03 question remains in the resolved-question log.

## Verified source contracts

The implementation verified these current contracts:

- `silver_project` is one canonical project per Contract ID and includes
  `project_key`, reported region, parsed coordinates, selected source lineage,
  deterministic run ID, and transformation rule version.
- `silver_psgc_place` exposes official `REGION` rows with code, raw and
  standardized names, hierarchy, snapshot, ingest, version, run, and rule
  lineage.
- the place-alias and manual-geographic configuration tables retain approval,
  active-state, version, and canonical PSGC target fields.
- the boundary source exposes `psgc_code`, `administrative_level`, GeoJSON,
  PSGC version, boundary version, and technical lineage.

The current project contract has no legitimate project-level PSGC code. The
stage is explicitly marked unavailable instead of using another field as a
substitute.

## Local dataset verification

`/Users/franziellenadinecanquin/datasets` was accessible. Six files were
identified:

| Local file | Bronze source |
| --- | --- |
| `dpwh_projects.csv` | `01-bronze.dpwh_projects` |
| `flood_control_projects.csv` | `01-bronze.flood_control_projects` |
| `psgc.csv` | `01-bronze.psgc` |
| `population_2024_table_c_test.csv` | `01-bronze.census_2024_table_c` |
| `boundary_bettergov.csv` | `01-bronze.boundaries` |
| `flood_susceptibility.csv` | `01-bronze.flood_susceptibility` |

Fields inspected for the governed configuration and Table 13 contracts included:

- project category, status, Contract ID, reported region, and coordinates
- flood source infrastructure type, work type, Contract ID, region, and source
  object identity
- PSGC code, place name, geographic level, publisher version, and population
  cross-check field
- Table C place name, population, file, sheet, and source row
- boundary PSGC code, administrative level, geometry, PSGC version, and boundary
  version
- MGB susceptibility code and geometry representation

Observed values support the existing four MGB code mappings and an exact
`Central Office` non-geographic project rule. Observed project region variants
do not authorize hidden aliases. Region aliases, manual project exceptions, and
any current treatment of older boundary polygons around Negros still require
human approval.

The local DPWH file had 265,582 rows, while older documentation refers to a
different accepted snapshot size. The local files therefore support defensive
schema and value verification only. They are not claimed to match the selected
Bronze tables.

## Grain and identity

Table 13 has one canonical `silver_project` mapping result per deterministic
geographic mapping run. Every project remains present, including non-geographic,
ambiguous, unmatched, conflicting, and invalid outcomes.

`project_region_map_key` and `run_id` are deterministic SHA-256 identities.
They contain no UUID, random value, current date, or current timestamp.

## Central Office behavior

The local DPWH profile found 306 exact `Central Office` rows. Runtime count may
differ and is not claimed.

The notebook uses exact conservative normalization and excludes Central Office
before name, alias, and spatial stages. It inspects approved manual evidence so
conflicting overrides remain visible, but assigns no PSGC region and does not
manufacture Gold `region_key = 0` in Silver.

## Boundary strategy

The local boundary file contains 43,760 shapes but already includes 17 region
polygons. Table 13 uses only that region subset and broadcasts it. The spatial
comparison is therefore project by 17 regions, not project by all 43,760 shapes.

The source uses Polygon and MultiPolygon GeoJSON with numeric coordinate values
encoded as strings. Native Databricks SQL safely normalizes numeric tokens,
parses geometry, and uses longitude-first WGS84 points with `ST_COVERS`.

The boundary source reports PSGC version `2023-10-24` and boundary version
`2023-11-06`. The current local PSGC file reports `2Q 2026 as of 2026-06-30` and
18 regions. Table 13 retains both versions and exposes mismatch status. No NIR
correction is hardcoded.

## Conflict behavior

A reviewed, exact-name, or approved-alias target remains authoritative when one
coordinate region disagrees. The coordinate region remains in diagnostic
columns, and the final state becomes `MATCHED_WITH_CONFLICT` with
`REGION_MISMATCH`.

Multiple candidates remain `AMBIGUOUS`. No fuzzy, nearest-neighbor, broad
substring, arbitrary `MIN` or `MAX`, or hidden alias rule selects a target.

## Lineage

The output retains project, PSGC, boundary, alias, manual mapping, rule, run,
snapshot, ingest, version, source-load, and source-modification context. Applied
manual exceptions also retain target, reason, source reference, and approval
metadata. Unavailable optional publisher versions remain null and are flagged.

## Validation review

The validator covers all seven project data-quality attributes:

- Consistency
- Accuracy
- Completeness
- Auditability
- Validity
- Uniqueness
- Timeliness

It persists evidence before the blocking gate. STOP checks protect row
preservation, documented grain, deterministic identities, precedence, official
targets, Central Office, conflict state, geometry, and mandatory lineage. FLAG
checks retain source and configuration limits with denominators.

### Databricks runtime verification

The Table 13 transformation and validator were executed successfully in
Databricks against the selected Unity Catalog tables.

Runtime results:

- canonical `silver_project` rows: 265,656
- `silver_project_region_map` rows: 265,656
- row-preservation difference: 0
- blocking STOP checks: 18 PASS, 0 FAIL
- `MATCHED`: 212,353
- `MATCHED_WITH_CONFLICT`: 14
- `NON_GEOGRAPHIC`: 306
- `AMBIGUOUS`: 32
- `UNMATCHED`: 52,951
- `INVALID_SOURCE`: 0

Validation evidence was persisted to
`04-validation.silver_dq_results` before the blocking gate.

## Local verification

- notebook JSON parsing: passed
- Pytest: 164 tests passed
- Ruff lint and format check: passed
- SQLFluff notebook lint: passed
- Markdown layout: passed
- offline local-link check: 0 errors
- Vale: 0 errors, 0 warnings, and 0 suggestions

## Unresolved limitations

- The current project contract has no legitimate project-level PSGC code.
- No approved DPWH region aliases were available for this run.
- No approved manual project-region overrides were available for this run.
- The selected boundary set contains 17 regions while current PSGC contains 18.
- The boundary and PSGC versions differ, so the mismatch remains visible.
- 52,951 projects remain unmatched and 32 remain ambiguous.
- Tables 14 and 15, Gold, dashboards, and Genie remain outside this milestone.

## Runtime handoff

Use this order in Databricks:

1. `notebooks/02_silver/00_config_mappings.ipynb`
2. `notebooks/04_validation/02_validation_silver_config.ipynb`
3. `notebooks/02_silver/01_silver_psgc_place.ipynb` when PSGC changed
4. `notebooks/04_validation/03_validation_silver_geography_population.ipynb`
5. `notebooks/02_silver/04_silver_dpwh_project_component.ipynb` when DPWH changed
6. `notebooks/02_silver/05_silver_project.ipynb`
7. `notebooks/04_validation/04_validation_silver_projects.ipynb`
8. `notebooks/02_silver/08_silver_project_region_map.ipynb`
9. `notebooks/04_validation/06_validation_silver_project_region_map.ipynb`

Record every numerator and denominator, review every FLAG, and retain the
executed evidence before downstream promotion.
