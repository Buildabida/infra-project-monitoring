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
| `02-silver.silver_mgb_flood_area` | Selected MGB polygons parsed once, with raw codes, geometry statuses, and WKB geometry |
| `01-bronze.flood_susceptibility` | Lineage columns only, to prove the selected MGB snapshot and Bronze ingest run |
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
2. Run `notebooks/02_silver/08a_silver_mgb_flood_area.ipynb` and
   `notebooks/04_validation/06a_validation_silver_mgb_flood_area.ipynb`, unless
   they already ran for the current MGB snapshot and Bronze ingest run.
3. Run `notebooks/02_silver/10_silver_project_flood_map.ipynb`.
4. Run `notebooks/04_validation/08_validation_silver_project_flood_map.ipynb`.

After a Bronze MGB force reload with the same snapshot ID, rerun `08a` and its
validator before Table 15. The parsed table must carry both the current MGB
snapshot ID and the current Bronze ingest run ID. A matching snapshot alone is
not enough. Table 15 and its validator stop on stale parsed lineage. See
[Parsed MGB freshness](#parsed-mgb-freshness).

When upstream inputs changed, use this dependency-aware order:

1. Bronze pipeline and Bronze validation, when DPWH or MGB changed
2. `notebooks/02_silver/00_config_mappings.ipynb`, when the MGB mapping changed
3. `notebooks/04_validation/02_validation_silver_config.ipynb`, after step 2
4. `notebooks/02_silver/04_silver_dpwh_project_component.ipynb`, when DPWH changed
5. `notebooks/02_silver/05_silver_project.ipynb`, after step 4
6. `notebooks/04_validation/04_validation_silver_projects.ipynb`, after step 5
7. `notebooks/02_silver/08a_silver_mgb_flood_area.ipynb`, when MGB changed
8. `notebooks/04_validation/06a_validation_silver_mgb_flood_area.ipynb`, after step 7
9. `notebooks/02_silver/10_silver_project_flood_map.ipynb`
10. `notebooks/04_validation/08_validation_silver_project_flood_map.ipynb`

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
- MGB parse run of `silver_mgb_flood_area` (`mgb_flood_area_run_id`)
- MGB mapping version and mapping source contract
- `classification_rule` and `classification_rule_version`

No date, timestamp, UUID, or random value enters logical identity. An exact
rerun of the same inputs reproduces the same run ID and keys.

`classification_rule_version` is
`silver-project-flood-map-v2|predicate=ST_INTERSECTS` followed by the
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

Table 15 reads parsed geometry from `02-silver.silver_mgb_flood_area`, the same
table Table 14 reads. It never parses `geometry_json` itself. See
[Silver MGB flood areas](silver_mgb_flood_area.md) for the parser contract,
including Esri holes, and its validation.

Each row carries one geometry status from that table: `BLANK_GEOMETRY`,
`UNPARSEABLE_GEOMETRY`, `EMPTY_GEOMETRY`, `UNSUPPORTED_GEOMETRY_TYPE`,
`INVALID_GEOMETRY`, `REPAIRED_GEOMETRY`, or `USABLE_GEOMETRY`. Table 15 reads only the parsed run
whose `run_id` it hashes into `project_flood_run_id`, and it stops when the
`06a` validation is missing or has a blocking failure.

Only rows with `susceptibility_mapping_status = 'MAPPED_APPROVED'` and usable
geometry take part in classification. Usable geometry includes
`REPAIRED_GEOMETRY`, an invalid polygon repaired under D-43 in
`silver_mgb_flood_area`; `is_repaired_geometry` keeps it visible, and the
validator flags matched projects that depend on a repaired polygon. Geometry
that stays `INVALID_GEOMETRY` is excluded and flagged. Table 15 applies no
repair, buffer, or other hidden rule of its own.

`silver_mgb_flood_area` identifies each polygon by its MGB `object_id` within one
snapshot (D-42). Table 15 does not publish polygon IDs. It keeps snapshot and run
lineage plus candidate counts per project.

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

Decision governance: the Buildabida team owns any future severity-precedence
decision. D-29 and D-30 establish the project's traceability and versioned
mapping pattern. D-45 keeps this rule for the capstone: ambiguous projects
stay `AMBIGUOUS`, and the dashboard shows them as their own group.

Any future precedence must receive a new decision ID in `docs/decisions.md`
and a new `silver-project-flood-map` rule version before implementation.
Version `silver-project-flood-map-v2` must not change silently.

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
- The transformation reads parsed WKB from `silver_mgb_flood_area`. It never
  parses MGB geometry text. Since D-42, Tables 14 and 15 and their validators
  share that one parsed table.

## Validation

`notebooks/04_validation/08_validation_silver_project_flood_map.ipynb`
persists results to `04-validation.silver_dq_results` before its STOP gate.
The gate then reads the persisted rows. See
[Data-quality checks](validation.md#silver-project-flood-mapping-validation)
for the full list.

The validator does not trust the transformation's intermediate results:

- It declares the coordinate screen independently and recomputes every
  project's coordinate status.
- It reads MGB from the independently validated `silver_mgb_flood_area` and recomputes source accounting.
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
  run, historical reference comparison, and parsed MGB lineage that matches the
  current Bronze MGB rows

## Parsed MGB freshness

`silver_mgb_flood_area` is current only when it carries the latest accepted MGB
snapshot ID and the `_ingest_run_id` of the current `01-bronze.flood_susceptibility`
rows. Notebook 10 checks both before it classifies any project. Validator 08
repeats the check as the STOP check `Parsed MGB lineage matches current accepted
Bronze MGB ingest`.

The expected ingest run comes from the Bronze rows, not from `load_log.run_id`.
A `SKIPPED_IDEMPOTENT` load writes a new `load_log` run ID but keeps the Bronze
rows and their `_ingest_run_id`. Comparing with `load_log` would stop every
routine Bronze rerun even when nothing changed. Only a load that rewrites Bronze,
such as a force reload, changes `_ingest_run_id`. That change makes the next
`08a` run parse again, because its run ID hashes the ingest run.

The October 12, 2026 run is in the
[Silver validation evidence](evidence/silver/README.md#october-12-2026-parsed-mgb-lineage-check-issue-109).

## STOP and FLAG

STOP protects correctness. Examples:

- unsafe or stale MGB, DPWH, project, or CONFIG upstream state
- stale `silver_mgb_flood_area` lineage, where the parsed snapshot or ingest
  run differs from the current Bronze MGB rows
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

### Rerun on project rule version 2

Table 15 was rerun after the project foundation moved to `silver_project_v2`.

| Input | Value |
| --- | --- |
| Project run | `add5661e4e762ac48a270a437356933bc499a130186cc1f664561364face3449` |
| Table 15 run ID | `dc10d49cb327609eaa35fd97edc39b34b357d82b7fbf3d42fc12a343aaa208b7` |

The DPWH snapshot, MGB snapshot, and mapping version did not change. The
validator again wrote 53 checks. All 37 STOP checks passed, and the selected
project validation it checks had 29 checks with no blocking failure.

### Rerun after the Esri hole fix (issue #92)

Table 15 was rerun on 2026-10-09 with rule version `silver-project-flood-map-v2`,
which reads Esri polygon holes as holes.

| Input | Value |
| --- | --- |
| Project run | `c99563fa560b94dfc40139d4f6ece1d6f625cc9efd7e93228d70904b0683a17a` |
| Table 15 run ID | `2425d8a112a3852faf653ffecd73135ab8e2033237bc08478b2560750f89cea3` |

The DPWH snapshot, MGB snapshot, and mapping version did not change. The
validator wrote 53 checks with no blocking failure. The tables below are from
this run.

### Project classification

| Outcome | Projects | Share of all projects |
| --- | ---: | ---: |
| `MATCHED` Low | 10,095 | 3.80% |
| `MATCHED` Moderate | 9,656 | 3.63% |
| `MATCHED` High | 6,010 | 2.26% |
| `MATCHED` Very High | 2,002 | 0.75% |
| `AMBIGUOUS` across approved levels | 18 | 0.01% |
| `UNMATCHED`, usable point without an approved polygon | 187,357 | 70.53% |
| `UNMATCHED`, missing coordinate pair | 50,518 | 19.02% |
| Total | 265,656 | 100% |

- 215,138 projects have a `VALID_PAIR` coordinate. No project had a partial
  or out-of-range pair, and no project had an invalid identity.
- 27,763 projects received a final level. That is 10.45% of all projects and
  12.90% of projects with a usable coordinate. Before the fix, 20,398 did
  (9.48% of projects with a usable coordinate).
- 156 matched projects sit inside more than one polygon of the same level.

### MGB source accounting

The 63,684 selected MGB rows equal the audited Bronze `rows_loaded`:

| Bucket | Rows |
| --- | ---: |
| Mapped and usable | 61,678 |
| Mapped and unusable | 168 |
| Unmapped and usable | 23 |
| Unmapped and unusable | 1,815 |

- Unusable mapped rows are 140 OGC-invalid, 14 empty, and 14 unparseable
  geometries. Before the fix, 2,340 were OGC-invalid.
- Unmapped rows are 1,822 blank codes and 16 `No rating` codes. All 1,815 blank
  geometries also have a blank code.
- All parsed geometries used the Esri `rings` path.

### Interpretation note

Most usable project points, 87.1%, fall outside every approved MGB polygon.
These results must not be read as Low or zero flood risk.

Issue #92 found one cause of the low match rate. Before the fix, the Esri parser
read a polygon's holes as separate polygons, which made the whole feature
invalid and excluded it. A diagnostic run on 2026-10-09 found that 2,232 of the
2,340 invalid MGB polygons had holes. The live MGB layer reports 63,684
features, the same as the Bronze extract, so the extract is not missing
features.

The fix raised the match rate from 9.48% to 12.90% of projects with a usable
coordinate. That is still well below the 52% that the issue #92 spot check
found against the live layer, so a further cause may remain.

### Rerun after the Bronze reload and one-time parsing (issue #92)

The October 9 run still missed 1,815 MGB polygons. The October 4 Bronze load
had replaced every row with a geometry field longer than 131,072 characters with
an all-null row, so those polygons reached Silver with no code and no geometry.
The October 10 Bronze reload restored them. The live MGB layer and the reloaded
Bronze table now agree on every code count.

Table 15 was rerun on 2026-10-11. It reads parsed geometry from
`silver_mgb_flood_area` instead of parsing `geometry_json` itself.

| Input | Value |
| --- | --- |
| Project run | `c99563fa560b94dfc40139d4f6ece1d6f625cc9efd7e93228d70904b0683a17a` |
| MGB snapshot | `metadata-17bf5e65e1838a2f7be9`, ingest run `07bfbee8-62ba-4b45-976f-10e51c4ab9f3` |
| Table 15 run ID | `97a8cf5ccf2cba8e34cb739e35e1026b37a7b91102439a3292e0d5cbf2c01961` |

The DPWH snapshot, project run, and mapping version did not change. The
validator wrote 53 checks: all 37 STOP checks passed, with 13 FLAG and 3 PASS
review checks.

| Outcome | Projects | Share of all projects |
| --- | ---: | ---: |
| `MATCHED` | 62,302 | 23.45% |
| `AMBIGUOUS` across approved levels | 52 | 0.02% |
| `UNMATCHED`, usable point without an approved polygon | 152,784 | 57.51% |
| `UNMATCHED`, missing coordinate pair | 50,518 | 19.02% |
| Total | 265,656 | 100% |

- 62,302 projects received a final level. That is 28.96% of the 215,138
  projects with a usable coordinate, up from 12.90% on October 9.
- 269 matched projects sit inside more than one polygon of the same level.
- The validator output does not split matched projects by level, so this
  section does not report a per-level count.

MGB source accounting for this run:

| Bucket | Rows |
| --- | ---: |
| Mapped and usable | 63,335 |
| Mapped and unusable | 326 |
| Unmapped and usable | 23 |
| Unmapped and unusable | 0 |
| Total, equal to the audited Bronze `rows_loaded` | 63,684 |

- Unusable mapped rows are 297 OGC-invalid, 15 unparseable, and 14 empty
  geometries.
- Unmapped rows are 7 blank codes and 16 `No rating` codes. No geometry is blank.
- 63,669 geometries used the Esri `rings` path.
- The `Runtime MGB counts are compared with historical Bronze references` FLAG
  reports 0 blank geometries against the old reference of 1,815. The reference
  predates the Bronze fix; the difference is expected.

71.02% of usable project points still fall outside every approved MGB polygon.
These results must not be read as Low or zero flood risk. The match rate is
still below the 52% from the issue #92 spot check. The next section explains
the remaining gap.

### Rerun after the invalid polygon repair (D-43)

A diagnostic on 2026-10-11 found the remaining gap. In a deterministic sample of
50 unmatched projects with a usable coordinate, 17 sat inside an MGB polygon,
and all 17 polygons were `INVALID_GEOMETRY`. The 297 invalid polygons cover
about 22,739 sq km in Web Mercator. Most have rings that touch or cross
themselves, which Esri allows and OGC does not. Decision D-43 repairs them with
a zero-distance buffer, `ST_BUFFER(geometry, 0)`, in `silver_mgb_flood_area` when the repaired area stays within
1% or 0.01 sq km of the MGB `Shape__Area`.

Table 15 was rerun on 2026-10-11 after `silver_mgb_flood_area` was rebuilt with
parse rule v2.

| Input | Value |
| --- | --- |
| Project run | `c99563fa560b94dfc40139d4f6ece1d6f625cc9efd7e93228d70904b0683a17a` |
| MGB parse run | `12765b9cc50d7f107298ab18de2f6bafd8ab10f04bc2a9bee06800c9d984969c` |

The validator wrote 54 checks: all 37 STOP checks passed, with 13 FLAG and 4
PASS review checks.

| Outcome | Projects | Share of all projects |
| --- | ---: | ---: |
| `MATCHED` Low | 35,146 | 13.23% |
| `MATCHED` Moderate | 27,467 | 10.34% |
| `MATCHED` High | 35,672 | 13.43% |
| `MATCHED` Very High | 14,425 | 5.43% |
| `AMBIGUOUS` across approved levels | 250 | 0.09% |
| `UNMATCHED`, usable point without an approved polygon | 102,178 | 38.46% |
| `UNMATCHED`, missing coordinate pair | 50,518 | 19.02% |
| Total | 265,656 | 100% |

- 112,710 projects received a final level. That is 52.39% of the 215,138
  projects with a usable coordinate, which matches the 52% from the issue #92
  spot check. The rate was 28.96% before the repair and 9.48% before any
  issue #92 fix.
- 50,475 matched projects, 44.8% of all matched projects, sit inside at least
  one repaired polygon.
- 285 matched projects sit inside more than one polygon of the same level.
- Ambiguous projects rose from 52 to 250, because repaired polygons of
  different levels can overlap the same point.

MGB source accounting: 63,632 mapped and usable, including 297 repaired; 29
mapped and unusable (15 unparseable and 14 empty); 23 unmapped and usable. No
polygon stays `INVALID_GEOMETRY`.

47.49% of usable project points still fall outside every approved MGB polygon.
These results must not be read as Low or zero flood risk.

### Unmatched project spot-check

To investigate the low project-flood match coverage, the validator selects a
deterministic sample of `UNMATCHED` projects with usable coordinates.

The sample is limited to projects that:

- have a `VALID_PAIR` coordinate
- have a safely matched PSGC region
- are in a region where Table 14 calculated nonzero High or Very High flood exposure
- have an exact Contract ID match to the official flood-control source
- still have no approved usable MGB polygon intersecting the project point

| Contract ID | PSGC region code | Latitude | Longitude | Region mapping | Flood result | Flood-control source |
| --- | --- | ---: | ---: | --- | --- | --- |
| `23DN0050` | `0400000000` | 14.659331 | 121.274275 | `COORDINATE_BOUNDARY` | `UNMATCHED` | `MATCHED_EXACT_CONTRACT_ID` |
| `22IJ0084` | `0800000000` | 12.014647 | 124.812286 | `COORDINATE_BOUNDARY` | `UNMATCHED` | `MATCHED_EXACT_CONTRACT_ID` |
| `24MF0015` | `1200000000` | 6.675582 | 124.568240 | `COORDINATE_BOUNDARY` | `UNMATCHED` | `MATCHED_EXACT_CONTRACT_ID` |
| `22OB0338` | `1300000000` | 14.637775 | 121.116908 | `COORDINATE_BOUNDARY` | `UNMATCHED` | `MATCHED_EXACT_CONTRACT_ID` |
| `24CH0065` | `0300000000` | 14.980733 | 120.535408 | `COORDINATE_BOUNDARY` | `UNMATCHED` | `MATCHED_EXACT_CONTRACT_ID` |

These samples confirm that the low project-flood match rate is not caused by
projects being dropped from the mapping pipeline. Each project remains present,
has a valid coordinate, has a trusted region assignment, and is independently
confirmed in the official flood-control source.

The result still does not prove that the exact project point should intersect an
MGB susceptibility polygon. Flood-control project membership and regional flood
exposure provide useful review context, but they are not substitutes for the
point-in-polygon rule.

Table 15 therefore keeps these projects `UNMATCHED` and does not introduce a
nearest-polygon rule, buffer, manual flood classification, or severity fallback.

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
  `AMBIGUOUS` (D-45). A precedence rule needs a new decision.
- Esri holes are read as holes only when the first reading is invalid. A
  geometry that is still invalid after that is repaired under D-43 when the
  repair passes its checks. Otherwise it stays `INVALID_GEOMETRY` and is
  excluded, so a point inside it cannot match it. After the October 11 run, no
  polygon stays invalid.
- Table 15 keeps per-polygon evidence as counts and levels, not polygon IDs.
  `silver_mgb_flood_area` keys each polygon by its MGB `object_id` (D-42).
- The optional MGB and DPWH publisher versions may be unavailable.
- The spatial join is the most expensive step. Its runtime cost must be
  monitored when future MGB or DPWH snapshots grow.

## Analytical interpretation limits

Table 15 describes the flood-susceptibility context at project locations. It
does not prove that flood-control investment is sufficient or that flood
protection is adequate. It does not show that flooding was caused by
infrastructure gaps, or that any wrongdoing occurred.

Describe results as patterns and areas for further investigation.
