# Silver project-to-region mapping

This milestone implements Silver Table 13:
`02-silver.silver_project_region_map`.

It assigns canonical DPWH projects to official PSGC regions for regional
investment analysis. It also preserves projects that cannot safely receive a
region. Gold can consume the result without repeating geographic matching.

Runtime-validated in Databricks for the selected snapshots. See [runtime evidence](#runtime-evidence).

## Business purpose

The project questions compare reported infrastructure budgets, project counts,
delivery status, population, and flood-related context by region. Table 13
provides the governed project-to-region relationship needed for those
comparisons.

The table does not decide whether a region is underfunded or adequately served.
It supplies traceable geography and coverage evidence for later analysis.

## Source authority

The mapping reads these existing contracts:

| Input | Authority in this milestone |
| --- | --- |
| `02-silver.silver_project` | Canonical project identity, reported region, coordinates, and project lineage |
| `02-silver.silver_psgc_place` | Current official region codes, names, hierarchy, and PSGC lineage |
| `02-silver.config_place_name_alias` | Reviewed region-name aliases |
| `02-silver.config_manual_geographic_match` | Reviewed project-specific geographic exceptions |
| `01-bronze.boundaries` | Selected region polygon geometry and boundary lineage |
| `01-bronze.load_log` | DPWH load timestamp and optional publisher version |
| Bronze and Silver validation results | Upstream safety evidence |

Table 13 does not reread Bronze DPWH business rows, Census Table C,
flood-control records, MGB data, or Gold tables.

## Dependency order

Use this dependency-aware order. Rerun an upstream group only when its source or
rules changed.

1. `notebooks/02_silver/00_config_mappings.ipynb`
2. `notebooks/04_validation/02_validation_silver_config.ipynb`
3. `notebooks/02_silver/01_silver_psgc_place.ipynb` when PSGC changed
4. `notebooks/04_validation/03_validation_silver_geography_population.ipynb`
   after a geography or PSGC rebuild
5. `notebooks/02_silver/04_silver_dpwh_project_component.ipynb` when DPWH changed
6. `notebooks/02_silver/05_silver_project.ipynb` after a component rebuild
7. `notebooks/04_validation/04_validation_silver_projects.ipynb`
8. `notebooks/02_silver/08_silver_project_region_map.ipynb`
9. `notebooks/04_validation/06_validation_silver_project_region_map.ipynb`

Tables 11 and 12 are not dependencies of Table 13.

## D-03 resolution

[D-31](decisions.md) resolves D-03 with a region-first, evidence-preserving
waterfall. The implementation uses project identity and reviewed configuration
before spatial fallback. It does not choose between a map point and office name
by hiding one source of evidence. It retains both and records conflicts.

## Table grain and key

Grain: one canonical `silver_project` mapping result per deterministic
geographic mapping run.

Every project produces exactly one final row, including projects with these
outcomes:

- matched
- matched with a name-versus-coordinate conflict
- non-geographic
- ambiguous
- unmatched
- invalid source identity

Primary key: `project_region_map_key`.

The key is a SHA-256 hash of source system, canonical `project_key`, and the
deterministic mapping run ID. Random UUIDs and processing time are not part of
logical identity.

## Project identity

`project_key` and `contract_id` come from `silver_project`. The source system is
the existing DPWH project contract. Table 13 does not invent a new project grain
or consolidate project components again.

The current project contract has no legitimate project-level PSGC code. The
output therefore records `PROJECT_PSGC_CODE_NOT_AVAILABLE` for that matching
stage. It does not add an empty placeholder code or infer one from another field.

## Matching waterfall

The final precedence is:

0. Exact `Central Office` non-geographic rule
1. Active, approved project-specific manual exception
2. Exact verified project PSGC code when a legitimate source field becomes
   available. This stage is currently not applicable.
3. Exact standardized official region name
4. Active, approved region alias
5. Coordinate and selected region-boundary fallback
6. Unresolved result

An ambiguous higher-priority stage does not fall through to a lower stage.
This prevents lower-quality evidence from selecting a convenient target.

## Manual exception path

Manual exceptions come only from
`config_manual_geographic_match` rows where:

- `source_system = 'DPWH'`
- `record_type = 'PROJECT'`
- `approval_status = 'APPROVED'`
- `is_active = TRUE`
- the selected mapping version is singular
- the canonical target exists in the selected PSGC hierarchy
- a lower-level target resolves through that hierarchy to exactly one current
  official region

An empty table is valid and receives the deterministic
`NO_APPROVED_MANUAL_VERSION` sentinel. Multiple active approved versions stop
the run.

## Central Office

Local source profiling found the exact reported-region value `Central Office`.
The implementation checks that normalized value exactly. It does not use a
substring such as `%CENTRAL%`.

Central Office rows receive:

- `mapping_method = 'NON_GEOGRAPHIC_RULE'`
- `match_status = 'NON_GEOGRAPHIC'`
- no PSGC region code
- no Gold `region_key`

They are removed before name, alias, and spatial candidate generation. Approved
manual evidence is still inspected so a conflicting Central Office override is
visible, but the non-geographic rule remains authoritative. Gold may later
represent these records with its governed non-geographic dimension member.

## Exact region-name standardization

The project and PSGC names use only:

- `TRIM`
- uppercase
- repeated-whitespace collapse

The implementation does not remove `REGION`, Roman numerals, hyphens,
punctuation, or directional words. It does not embed a `Region IV-B` to
`MIMAROPA` correction or any Negros Island Region correction.

## Alias behavior

Aliases are optional governed data. Only active `APPROVED` DPWH region aliases
from one selected version may participate. Each canonical target must exist in
the selected official PSGC region set.

No alias is manufactured from observed values inside the notebook. When the
table is empty, exact and spatial methods still run and the absence remains
visible in validation.

## Spatial fallback and cross-check

The current local boundary artifact was inspected. It contains 43,760 shapes,
including 17 rows whose `administrative_level` is `region`. Table 13 selects
only that small region set. It does not compare every project with all barangay
or municipality shapes.

The boundary `geometry_json` field contains Polygon and MultiPolygon GeoJSON.
Its coordinate numbers are represented as quoted strings. Native SQL removes
quotes only around numeric coordinate tokens, parses with `TRY_TO_GEOMETRY`,
and creates project points with:

```sql
ST_POINT(longitude, latitude, 4326)
```

`ST_COVERS` supports both fallback assignment and diagnostic cross-checks.
There is no Python, Pandas, GeoPandas, spatial UDF, fuzzy match, nearest-region
assignment, or arbitrary candidate selection.

The screening bounds are copied once from the repository's `src/config.py`
contract into a parameter view. They are not repeated across spatial stages.
Execution requires a Databricks runtime or SQL warehouse that supports the
native `GEOMETRY`, `TRY_TO_GEOMETRY`, `ST_POINT`, and `ST_COVERS` functions.

The 17-row region set is broadcast. This bounds the spatial comparison and
avoids a naive project-by-43,760-feature join.

## Boundary version mismatch

The locally inspected boundary artifact reports PSGC version `2023-10-24` and
boundary version `2023-11-06`. The current local PSGC artifact reports
`2Q 2026 as of 2026-06-30` and includes 18 regions.

The notebook joins boundary codes to the selected current official regions and
retains both versions. It publishes `VERSION_MISMATCH_VISIBLE` when versions do
not agree. It never relabels an old polygon to a new region without evidence.

## Negros Island Region

The current PSGC source includes Negros Island Region. The inspected boundary
artifact predates that current 18-region set and contains 17 region polygons.

Table 13 does not hardcode a Negros correction. An exact name or approved alias
may assign a current PSGC region. Coordinate evidence from an older polygon set
may disagree. That disagreement remains visible rather than silently changing
the accepted higher-priority match.

## Name and coordinate conflicts

When one reviewed, exact-name, or approved-alias region is accepted and one
spatial region disagrees:

- the higher-priority region stays in `psgc_region_code`
- the coordinate region stays in `coordinate_region_code`
- `coordinate_crosscheck_status = 'REGION_MISMATCH'`
- `match_status = 'MATCHED_WITH_CONFLICT'`

No evidence is discarded.

## Controlled output values

### Mapping methods

- `MANUAL_OVERRIDE`
- `EXACT_REGION_NAME`
- `APPROVED_REGION_ALIAS`
- `COORDINATE_BOUNDARY`
- `NON_GEOGRAPHIC_RULE`
- `NONE`

### Match statuses

- `MATCHED`
- `MATCHED_WITH_CONFLICT`
- `NON_GEOGRAPHIC`
- `AMBIGUOUS`
- `UNMATCHED`
- `INVALID_SOURCE`

### Match quality

- `REVIEWED`
- `EXACT`
- `APPROVED_ALIAS`
- `SPATIAL`
- `REVIEW_REQUIRED`
- `UNRESOLVED`

## Candidate and reason evidence

The table retains `candidate_count`, stage-specific candidate counts, and
candidate-code arrays for manual, exact, alias, and spatial stages. A region is
accepted only when the selected stage has exactly one distinct official code.
Multiple candidates remain ambiguous.

`mapping_reason` explains the selected path. `ambiguity_reason` and
`exception_reason` identify unsafe or unresolved outcomes. Coordinate status
and cross-check status explain whether spatial evidence was usable.

## Deterministic run identity

The mapping run ID hashes:

- project run and snapshot
- PSGC run, snapshot, and publisher version or explicit unavailable sentinel
- boundary snapshot, ingest run, and boundary version
- selected alias version or empty-table sentinel
- selected manual mapping version or empty-table sentinel
- mapping rule version

An exact rerun replaces the same logical output and produces the same keys.

## Lineage

Each output retains:

- project snapshot, ingest run, project run, rule version, and source-modified
  timestamp
- optional DPWH publisher version from `load_log`
- DPWH source load timestamp from terminal audit evidence
- PSGC snapshot, ingest run, run, publisher version, rule version, and load time
- boundary snapshot, ingest run, source system, PSGC version, and boundary
  source version and load time
- applied manual target, reason, source reference, and approval metadata
- alias and manual mapping versions or explicit empty-table sentinels
- mapping rule and run identity

Optional publisher version remains null when unavailable. It is never copied
from file modification metadata or fabricated.

## Validation

`06_validation_silver_project_region_map.ipynb` persists results to
`04-validation.silver_dq_results` before enforcing its STOP gate.

Blocking checks protect:

- source-to-map row preservation
- documented grain and key uniqueness
- deterministic key and run identity
- controlled methods, statuses, and quality
- precedence
- official PSGC target validity
- Central Office non-geographic behavior
- conflict-state consistency
- region geometry parsing
- current-PSGC resolution and uniqueness of selected region boundaries
- manual override decision evidence
- mandatory project, PSGC, boundary, configuration, rule, and load lineage

Nonblocking checks retain:

- match coverage with the complete project denominator
- missing reported regions and coordinates
- outside-range coordinates and no boundary match
- empty approved alias or manual-exception tables
- boundary coverage and version mismatch
- unresolved boundary PSGC codes
- name-versus-coordinate conflicts
- Central Office records with ignored override evidence
- ambiguous and unmatched projects
- optional project and boundary publisher-version gaps
- full boundary source-lineage duplicates

All seven data-quality attributes have executable checks: Consistency,
Accuracy, Completeness, Auditability, Validity, Uniqueness, and Timeliness.

## Local verification boundary

The developer-local files were accessible for schema and source-value
profiling. The local DPWH file contained 265,582 rows, 21 distinct trimmed
reported-region values, 215,138 coordinate pairs, and 306 exact
`Central Office` rows. The local boundary file contained 43,760 rows and 17
region polygons. The current PSGC file contained 18 official region rows.

These observations guided defensive code. They are not Databricks execution
evidence and do not prove that the selected Bronze snapshots have the same row
counts. The Databricks results are in [runtime evidence](#runtime-evidence).

## Runtime evidence

The first documented Databricks run used the hardened project foundation:

| Input | Value |
| --- | --- |
| Project run | `add5661e4e762ac48a270a437356933bc499a130186cc1f664561364face3449` (`silver_project_v2`) |
| DPWH snapshot | `metadata-6321c7aa6f2a14e12f4c` |
| Validation run ID | `aeac08e3306e8cf33d5dd2cc1ef472ee2dc87a41fa45923998300a52f0f24934` |
| Approved region aliases and manual overrides | 0 and 0 |
| Publisher versions | DPWH not available, so it stays `NULL`. Boundary version is present on every row. |

The validator wrote 37 checks to `04-validation.silver_dq_results`. All 18
STOP checks passed. Of the 19 FLAG checks, 15 reported findings and 4 found
none.

### Mapping outcome

| Method | Status | Projects | Share of all projects |
| --- | --- | ---: | ---: |
| `COORDINATE_BOUNDARY` | `MATCHED` | 201,611 | 75.89% |
| `NONE` | `UNMATCHED` | 52,951 | 19.93% |
| `EXACT_REGION_NAME` | `MATCHED` | 10,742 | 4.04% |
| `NON_GEOGRAPHIC_RULE` | `NON_GEOGRAPHIC` | 306 | 0.12% |
| `COORDINATE_BOUNDARY` | `AMBIGUOUS` | 32 | 0.01% |
| `EXACT_REGION_NAME` | `MATCHED_WITH_CONFLICT` | 14 | 0.01% |
| Total | | 265,656 | 100% |

- 212,367 projects have a region, 79.94% of all projects. That includes the 14
  name-versus-coordinate conflicts.
- 306 `Central Office` projects stay non-geographic with no PSGC region.
- 52,983 projects have no region: 52,951 unmatched and 32 ambiguous.

### Coverage detail

- **Reported region text.** 265,401 projects have a reported region. Only
  10,756 of them match an official PSGC region name exactly. The other 254,645
  have no exact or approved alias match, because no region alias is approved.
  255 projects have no reported region.
- **Coordinates.** 215,138 projects have a usable pair. 50,518 have no pair. No
  project has a partial or out-of-range pair.
- **Coordinate fallback.** 210,314 usable points fall inside exactly one region
  boundary. 4,539 fall inside none, and 32 fall inside more than one.
- **Name versus coordinate.** 210,300 projects agree, 14 conflict, and 55,036
  cannot be compared.
- **Boundaries.** 17 boundary regions cover 18 official PSGC regions. Every row
  shows a boundary-versus-PSGC version difference. The full boundary file has
  232 duplicate source-file and feature rows out of 43,760.

### Interpretation note

Most regions come from the coordinate fallback, not from names. The DPWH
`reported_region` labels rarely equal the official PSGC names. Approved region
aliases could move some projects to the higher-priority name stage. This run
does not measure how many.

## Cost and scalability

- The project table is scanned at its canonical one-row-per-project grain.
- Approved configuration tables are small and version-gated.
- The spatial set contains only selected region polygons.
- Candidate aggregation occurs before the final one-row-per-project write.
- The result uses `CREATE OR REPLACE TABLE` for idempotent batch rebuilding.
- Validation uses grouped metrics and compact audit evidence.

## Gold handoff

Gold can derive regional project facts from `project_key`, accepted
`psgc_region_code`, mapping status, and complete lineage. Gold remains
responsible for surrogate `region_key` values and population-ratio exclusions.

This milestone does not implement project-flood mapping, regional flood
exposure, Gold facts or dimensions, dashboard assets, or Genie logic.
