# Silver project flood mapping

This milestone implements Silver Table 15:
`02-silver.silver_project_flood_map`.

It classifies every canonical DPWH project against the governed MGB
flood-susceptibility polygons once in Silver. Future Gold
`fact_project_snapshot` reuses the result and assigns serving keys only.

Databricks execution has been completed for the selected snapshots. The
transformation published one row for each of the 265,656 canonical projects.
All 37 blocking validation checks passed.

Runtime findings in [Runtime evidence](#runtime-evidence) describe the selected
snapshots only. They are evidence for this execution, not hardcoded
expectations for future runs.

## Business purpose

The main question asks where infrastructure investment is concentrated and
which areas have relatively low investment compared with population and needs.
Analysis pillar E compares flood-control investment and project coverage with
flood-risk exposure.

Table 15 answers one narrow question for each project:

> What flood susceptibility is present at this project's mapped point?

It supplies flood-risk context at project grain. Table 14 supplies regional
exposure. The two tables share the same MGB source, mapping, and geometry
contract. Neither table is derived from the other.

## What this table does not mean

- It does not say whether a project is a flood-control project. That identity
  comes from project classification and the flood-list reconciliation in
  [Silver source reconciliation](silver_source_reconciliation.md).
- It does not say whether investment is sufficient, fair, effective, or
  adequate.
- `UNMATCHED` does not mean Low risk, zero risk, or `Unknown` susceptibility.
  It means only that the selected approved MGB polygons did not produce a
  classification at that point.
- It does not infer susceptibility from a project category, description,
  reported region, or regional exposure aggregate.

## Source authority

| Input | Role in Table 15 |
| --- | --- |
| `02-silver.silver_project` | Canonical project identity, parsed coordinates, and project lineage |
| `01-bronze.flood_susceptibility` | Selected MGB flood-area rows, raw `flood_susceptibility_code`, and `geometry_json` |
| `02-silver.config_mgb_susceptibility_mapping` | The only authority for code-to-level and severity-rank standardization |
| `01-bronze.load_log` | Newest terminal MGB and DPWH load state, audited row count, load time, and optional publisher versions |
| `04-validation.dq_results` | Latest Bronze MGB and DPWH validation evidence |
| `04-validation.silver_config_dq_results` | Latest Silver CONFIG validation evidence |
| `04-validation.silver_dq_results` | Selected Silver project validation evidence |

Table 15 does not reread Bronze DPWH business rows or redo project
consolidation. It does not read population, Census Table C, flood-control
components, `silver_project_source_match`, `silver_project_region_map`,
`silver_region_flood_exposure`, or Gold. It never rereads R2 directly.

Table 15 does not require a successful region assignment. Project-region
mapping and project-flood mapping are separate relationships.

## Dependency order

If Bronze, CONFIG, and the project foundation are accepted and unchanged:

1. Review the existing accepted upstream evidence.
2. Run `notebooks/02_silver/10_silver_project_flood_map.ipynb`.
3. Run `notebooks/04_validation/08_validation_silver_project_flood_map.ipynb`.

When upstream inputs changed, use this dependency-aware order:

1. Bronze pipeline and Bronze validation, when DPWH or MGB changed
2. `notebooks/02_silver/00_config_mappings.ipynb`, when the MGB mapping changed
3. `notebooks/04_validation/02_validation_silver_config.ipynb`, after step 2
4. `notebooks/02_silver/04_silver_dpwh_project_component.ipynb`, when DPWH changed
5. `notebooks/02_silver/05_silver_project.ipynb`, after step 4
6. `notebooks/04_validation/04_validation_silver_projects.ipynb`, after step 5
7. `notebooks/02_silver/10_silver_project_flood_map.ipynb`
8. `notebooks/04_validation/08_validation_silver_project_flood_map.ipynb`

Tables 11 to 14 do not need to rerun for Table 15.

## Table grain and key

Grain: one final project-to-flood classification result per canonical
`silver_project` row per deterministic project-flood mapping run.

Every canonical project produces exactly one row. This includes projects that:

- have a usable coordinate and one approved level
- have a usable coordinate but no approved MGB polygon
- have no usable coordinate
- fall inside several polygons of the same approved level
- fall inside polygons of more than one approved level
- lack a stable source identity

Required uniqueness: `UNIQUE(source_system, contract_id, run_id)`. The
validator also checks that `project_key` never fans out into two rows.

Primary key: `project_flood_map_key`.

```text
project_flood_map_key = SHA2(source_system | project_key | run_id, 256)
```

This follows the Table 13 Silver SHA-256 convention. It is not the future Gold
BIGINT surrogate key. Gold owns serving-layer surrogate keys.

## Deterministic run identity

The run ID hashes these contracts:

- project run, project snapshot, and project ingest run
- MGB snapshot, MGB ingest run, and MGB publisher version or
  `NO_PUBLISHER_VERSION`
- MGB mapping version and mapping source contract
- `classification_rule` and `classification_rule_version`

No date, timestamp, UUID, or random value enters logical identity. An exact
rerun of the same inputs reproduces the same run ID and keys.

`classification_rule_version` is
`silver-project-flood-map-v1|predicate=ST_INTERSECTS` followed by the
coordinate screen. A changed screen therefore changes the run ID.

The candidate grid size is a performance setting only. It never changes which
polygons match, so it is not part of the rule version or the run ID.

## Coordinate contract

Table 15 starts from the parsed coordinates already published by
`silver_project`. It never cleans Bronze coordinates again.

`silver_project` has no coordinate-status column. Table 15 therefore applies
the exact Table 13 rule. The screen comes from `PH_LAT` and `PH_LON` in
`src/config.py` and is declared once in the notebook.

| Status | Rule |
| --- | --- |
| `MISSING_PAIR` | Latitude and longitude are both null |
| `PARTIAL_PAIR` | Exactly one of the two values is null |
| `OUT_OF_RANGE` | Latitude is outside 4.2 to 21.3, or longitude is outside 116.0 to 127.0 |
| `VALID_PAIR` | Both values are present and inside the screen |

Only a `VALID_PAIR` with a stable project identity becomes a point:
`ST_POINT(longitude, latitude, 4326)`. Unsafe pairs never become points, and
their projects keep their rows.

`silver_project` publishes a coordinate only when every component agrees on it.
A project whose components disagree has a null coordinate and appears as
`MISSING_PAIR`. This is the same behavior as Table 13.

## MGB mapping governance

Only active `APPROVED` rows with source system `DENR MGB flood susceptibility`
are read. Exactly one active approved `mapping_version` and one
`source_version` must exist, or the run stops. Each raw code must map to one
level and rank, and levels and ranks must be one-to-one.

The notebook contains no `CASE` mapping of `LF`, `MF`, `HF`, or `VHF`. Level
names and ranks come only from configuration.

Blank codes, `No rating`, and any other unapproved code remain `UNMAPPED`.
They never become an approved level or `Unknown`. Gold may later route
unresolved relationships through its governed unknown member. That Gold
behavior does not permit a Silver `Unknown` classification.

## Geometry parsing reuse

Table 15 reuses the Table 14 parser without change. See
[Silver regional flood exposure](silver_region_flood_exposure.md#geometry-parsing)
for the parser contract. The parser tries three governed paths:

1. parse the geometry as published
2. apply the targeted quoted-number normalization
3. convert supported Esri `rings` JSON

The first successful parse wins. Each row receives one Table 14 geometry
status: `BLANK_GEOMETRY`, `UNPARSEABLE_GEOMETRY`, `EMPTY_GEOMETRY`,
`UNSUPPORTED_GEOMETRY_TYPE`, `INVALID_GEOMETRY`, or `USABLE_GEOMETRY`.

The parser SQL is copied into the Table 15 notebook and its validator. Two
regression tests prove that both copies match Table 14 exactly. The only
differences allowed are the selected-version view name and the added severity
rank. If Table 14's parser changes, these tests fail until Table 15 is updated
in the same pull request.

Only rows with `susceptibility_mapping_status = 'MAPPED_APPROVED'` and
`source_geometry_status = 'USABLE_GEOMETRY'` take part in classification.
Invalid geometry is excluded and flagged. It is never repaired with
`ST_BUFFER` or any other hidden rule.

The MGB extract has no stable polygon business key. Table 15 does not invent
one. It keeps snapshot and run lineage plus candidate counts per project.

## Spatial predicate

Usable project points join mapped, usable MGB polygons with:

```sql
ST_INTERSECTS(polygon.mgb_geometry, point.project_point)
```

This follows Table 14. A point on a polygon boundary counts as inside. There is
no nearest polygon, no distance threshold, no buffer, and no fuzzy geography.

### Candidate grid

A spatial predicate alone gives the join no equality key. Without spatial
indexing in the engine, Spark could compare every project with every polygon.
Table 15 adds an exact bounding-box grid to prevent that cross join:

1. Each polygon is listed under every grid cell its bounding box touches.
2. Each point is listed under the single cell that contains it.
3. The join requires an equal cell, then tests `ST_INTERSECTS`.

The grid never removes a true match. A polygon's bounding box contains every
point the polygon intersects. `FLOOR(value / cell size)` keeps the point's cell
inside the box's cell range. A point sits in one cell, and a polygon appears at
most once per cell, so no project-polygon pair is counted twice.

The transformation uses 0.1-degree cells. The validator rebuilds every
candidate with 0.25-degree cells, so a defect in either grid shows up as a
mismatch.

## Classification rule

Candidates are aggregated to project grain before publication. The complete
project universe is then left joined to the candidates.

| Case | Evidence | `match_status` | `match_method` | `match_quality` | Level and rank | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| One level | Usable point, one or more polygons, exactly one distinct approved level | `MATCHED` | `COORDINATE_MGB_POLYGON` | `SPATIAL` | That level and its configured rank | None |
| Several levels | Usable point, polygons from more than one distinct approved level | `AMBIGUOUS` | `COORDINATE_MGB_POLYGON` | `REVIEW_REQUIRED` | `NULL` | `MULTIPLE_APPROVED_FLOOD_LEVELS` |
| No match | Usable point, no approved usable polygon | `UNMATCHED` | `NONE` | `UNRESOLVED` | `NULL` | `NO_APPROVED_MGB_INTERSECTION` |
| No usable point | `MISSING_PAIR`, `PARTIAL_PAIR`, or `OUT_OF_RANGE` | `UNMATCHED` | `NONE` | `UNRESOLVED` | `NULL` | `MISSING_COORDINATE_PAIR`, `PARTIAL_COORDINATE_PAIR`, or `COORDINATE_OUT_OF_RANGE` |
| Invalid identity | Null project key or blank Contract ID | `INVALID_SOURCE` | `NONE` | `UNRESOLVED` | `NULL` | `MISSING_STABLE_SOURCE_IDENTITY` |

`ambiguity_reason` is `MULTIPLE_APPROVED_FLOOD_LEVELS` on `AMBIGUOUS` rows and
`NULL` elsewhere.

### Same-level overlap

A point inside several polygons of the same approved level stays `MATCHED`.
The final level is not ambiguous. `matched_polygon_count` keeps the real number
of source rows, and `matched_level_count` is 1.

### Cross-level overlap

Table 14 showed that approved levels can overlap. No approved business rule
says Very High overrides High or that the highest severity wins. Table 15
therefore applies no severity precedence. A point inside polygons of more than
one approved level is `AMBIGUOUS`. Its level and rank stay `NULL`, and it keeps
`matched_polygon_count`, `matched_level_count`, and `candidate_levels`.

The notebook never uses `MAX(severity_rank)`, a severity sort, polygon order, or
any other tie-breaker. `candidate_levels` is sorted as text for display only.
The order never implies precedence.

If the team later approves a precedence rule, it must be recorded as a decision
and released as a new rule version. Version `silver-project-flood-map-v1` must
not change silently.

## Output columns

| Group | Columns |
| --- | --- |
| Identity | `project_flood_map_key`, `source_system`, `project_key`, `contract_id` |
| Coordinate evidence | `latitude`, `longitude`, `coordinate_status` |
| Classification | `flood_susceptibility_level`, `severity_rank`, `match_status`, `match_method`, `match_quality` |
| Candidate evidence | `matched_polygon_count INT`, `matched_level_count INT`, `candidate_levels ARRAY<STRING>`, `ambiguity_reason`, `exception_reason` |
| Rule lineage | `classification_rule`, `classification_rule_version` |
| Project lineage | `project_source_snapshot_id`, `project_source_ingest_run_id`, `project_source_version`, `project_run_id`, `project_rule_version`, `project_source_load_ts` |
| MGB lineage | `mgb_source_snapshot_id`, `mgb_source_ingest_run_id`, `mgb_source_version`, `mgb_source_load_ts`, `susceptibility_mapping_version`, `mgb_mapping_source_version` |
| Run | `run_id`, `source_load_ts` |

The columns include the full minimum contract from the fact-constellation
design. The added columns support audit and the Gold handoff.

## Source accounting

The transformation and validator both enforce this reconciliation:

```text
selected MGB rows
= mapped approved + usable geometry
+ mapped approved + unusable geometry
+ unmapped or unrated + usable geometry
+ unmapped or unrated + unusable geometry
```

The total must also equal the audited `rows_loaded` of the newest terminal MGB
load. Both totals are derived at runtime. The 63,684-row and 1,815-blank-geometry
historical counts are reference evidence only. They never decide correctness.

## Lineage

- Project load time and optional DPWH publisher version come from the `load_log`
  event of the project's ingest run, as in Table 13.
- MGB load time comes from Bronze `_ingested_at`, as in Table 14.
- The optional MGB publisher version comes only from `load_log`.
- `source_load_ts` is the later of the project and MGB load times.

Optional publisher versions stay `NULL` when unavailable. They are never copied
from file metadata or fabricated. The validator proves that each published
version equals the `load_log` value.

## Idempotency

The table is rebuilt with `CREATE OR REPLACE TABLE`. An exact rerun reproduces
the same run ID, keys, and rows and never appends duplicates. The validator uses
`MERGE` with a deterministic validation run ID, so its evidence is updated in
place on an exact rerun.

## Cost and scalability

- `silver_project` is scanned at its canonical one-row-per-project grain.
- Only `VALID_PAIR` points and only mapped, usable polygons enter the join.
- One native spatial join uses the exact bounding-box grid as an equality key.
  It is never a project × all-MGB cross join.
- Candidates are aggregated once to project grain, then left joined back.
- Expensive intermediate views are each consumed once in the publish path.
- Intermediate results use temporary views, not permanent staging tables.
- No cache, repartition, collect, Python, UDF, or spatial library is used.
- The transformation parses MGB geometry twice. One parse feeds the accounting
  gate before publication, and one feeds the spatial join. This matches the
  accepted Table 14 pattern.

A shared persisted layer of parsed MGB polygons could remove repeated parsing
across Tables 14 and 15 and their validators. It would also add a new governed
table and a new dependency. It is not created until runtime evidence shows the
repeated parse is a material cost.

## Validation

`notebooks/04_validation/08_validation_silver_project_flood_map.ipynb`
persists results to `04-validation.silver_dq_results` before its STOP gate.
The gate then reads the persisted rows. See
[Data-quality checks](validation.md#silver-project-flood-mapping-validation)
for the full list.

The validator does not trust the transformation's intermediate results:

- It declares the coordinate screen independently and recomputes every
  project's coordinate status.
- It reparses MGB with the governed parser and recomputes source accounting.
- It rebuilds every project's candidates with a different grid size and
  compares polygon counts, level counts, and candidate levels row by row.

All seven data-quality attributes have executable checks:

- Consistency: CONFIG validation, one run and version set, approved one-to-one
  mapping, level and rank agreement, status accounting, ambiguous and
  unresolved status rules, and the coordinate screen
- Accuracy: independent spatial recomputation, matched points that really
  intersect, no severity collapse, same-level overlap, approved-only levels,
  and the source SRID
- Completeness: every project exactly once, MGB source accounting, coverage
  against both denominators, and visible coordinate and MGB gaps
- Auditability: mandatory lineage, key and run reproduction, publisher
  versions from `load_log` only, version gaps, and parse paths
- Validity: controlled vocabulary, candidate counts, matched-row rules,
  reasons that follow the coordinate contract, safe coordinates only, and
  geometry findings
- Uniqueness: keys, grain, and no project fan-out
- Timeliness: newest safe loads and Bronze validation, current MGB and DPWH
  snapshots, current project run and validation, current mapping version, one
  run, and historical reference comparison

## STOP and FLAG

STOP protects correctness. Examples:

- unsafe or stale MGB, DPWH, project, or CONFIG upstream state
- source accounting that does not reconcile
- ambiguous approved mapping
- a missing, extra, or duplicated project
- a level published for an ambiguous or unmatched row
- a matched row without exactly one distinct level
- candidate evidence that differs from the independent recomputation
- a match from an unsafe coordinate
- a broken deterministic identity or missing mandatory lineage

FLAG keeps limitations visible with a denominator. Examples:

- projects without usable coordinates
- usable points without an approved MGB intersection
- projects across multiple approved levels
- projects inside several same-level polygons
- unmapped, blank, and `No rating` MGB rows
- blank, unparseable, empty, unsupported, and invalid MGB geometry
- optional MGB and DPWH publisher-version gaps
- runtime counts that differ from historical references

A FLAG is a visible source limitation, not a pipeline failure.

## Runtime evidence

The first Databricks execution used these inputs:

| Input | Value |
| --- | --- |
| Project run | `9fd532e99666ca6b3c3411311c58a773bae6eed2f2c7a09401216bc8f91f844e` |
| DPWH snapshot | `metadata-6321c7aa6f2a14e12f4c` |
| MGB snapshot | `metadata-17bf5e65e1838a2f7be9` |
| MGB mapping version | `2026-10-v1` with source contract `unversioned-official-code-contract` |
| Publisher versions | Not available for DPWH or MGB, so both stay `NULL` |
| Table 15 run ID | `ee7f53bc2885afcda6adfe5423f363ee084b4cb728880a5a7497556ad64b18e6` |

The validator wrote 53 checks to `04-validation.silver_dq_results`. All 37
STOP checks passed. Of the 16 FLAG checks, 13 reported findings and 3 found
none.

### Project classification

| Outcome | Projects | Share of all projects |
| --- | ---: | ---: |
| `MATCHED` Low | 7,486 | 2.82% |
| `MATCHED` Moderate | 7,037 | 2.65% |
| `MATCHED` High | 4,574 | 1.72% |
| `MATCHED` Very High | 1,301 | 0.49% |
| `AMBIGUOUS` across approved levels | 15 | 0.01% |
| `UNMATCHED`, usable point without an approved polygon | 194,725 | 73.30% |
| `UNMATCHED`, missing coordinate pair | 50,518 | 19.02% |
| Total | 265,656 | 100% |

- 215,138 projects have a `VALID_PAIR` coordinate. No project had a partial
  or out-of-range pair, and no project had an invalid identity.
- 20,398 projects received a final level. That is 7.68% of all projects and
  9.48% of projects with a usable coordinate.
- 116 matched projects sit inside more than one polygon of the same level.
- The independent recomputation matched the published candidate evidence for
  every project.

### MGB source accounting

The 63,684 selected MGB rows equal the audited Bronze `rows_loaded`:

| Bucket | Rows |
| --- | ---: |
| Mapped and usable | 59,478 |
| Mapped and unusable | 2,368 |
| Unmapped and usable | 23 |
| Unmapped and unusable | 1,815 |

- Unusable mapped rows are 2,340 OGC-invalid, 14 empty, and 14 unparseable
  geometries.
- Unmapped rows are 1,822 blank codes and 16 `No rating` codes. All 1,815 blank
  geometries also have a blank code.
- All 61,855 parsed geometries used the Esri `rings` path.

### Interpretation note

Most usable project points, 90.5%, fall outside every approved MGB polygon.
This run does not explain why. The selected extract may not cover every area,
or many projects may sit outside mapped susceptibility zones. Excluded invalid
polygons also remove some coverage. These results must not be read as Low or
zero flood risk.

## Gold handoff

Future Gold `03-gold.fact_project_snapshot` needs project, region, status, and
flood-susceptibility relationships plus `flood_match_status`. Table 15 supplies
the governed project-to-flood relationship.

- For `MATCHED` rows, Gold resolves `flood_susceptibility_level` with
  `susceptibility_mapping_version` and `mgb_mapping_source_version` to
  `dim_flood_susceptibility`.
- For `AMBIGUOUS`, `UNMATCHED`, and `INVALID_SOURCE` rows, Gold may use its
  governed unknown key 0. Silver does not create that key.
- Gold can copy `match_status` as the source of `flood_match_status`, along
  with `matched_polygon_count`, `exception_reason`, `run_id`, and
  `source_load_ts`.

Gold must not redo MGB code mapping, geometry parsing, project point creation,
project-to-MGB spatial matching, or ambiguity resolution. If Gold needs another
spatial match, Table 15 is incomplete.

## Known limitations

- Projects without a usable coordinate cannot be classified. They stay visible
  as `UNMATCHED` with a coordinate reason.
- A usable point without an approved polygon is `UNMATCHED`. The selected MGB
  extract may not cover every area, and unrated MGB rows never drive a level.
- Points inside overlapping polygons of different approved levels stay
  `AMBIGUOUS` until the team approves a precedence rule.
- Invalid MGB geometry is excluded rather than repaired, so a point inside an
  excluded polygon cannot match it.
- The MGB extract has no stable polygon key, so per-polygon evidence is kept as
  counts and levels rather than polygon identifiers.
- The optional MGB and DPWH publisher versions may be unavailable.
- The spatial join is the most expensive step. Its runtime cost must be
  monitored when future MGB or DPWH snapshots grow.

## Analytical interpretation limits

Table 15 describes the flood-susceptibility context at project locations. It
does not prove that flood-control investment is sufficient or that flood
protection is adequate. It does not show that flooding was caused by
infrastructure gaps, or that any wrongdoing occurred.

Describe results as patterns and areas for further investigation.
