# Silver regional flood exposure

This milestone implements Silver Table 14:
`02-silver.silver_region_flood_exposure`.

It performs the expensive MGB-to-region spatial work once in Silver. Future
Gold `fact_region_flood_exposure` reuses the result and assigns serving keys
only.

Requires Databricks execution. No runtime exposure area, coverage count, or
validation total is claimed in this document.

## Business purpose

The main question asks where infrastructure investment is concentrated and
which areas have relatively low investment compared with population and needs.
Analysis pillar E asks how flood-control investment and project coverage
compare with flood-risk exposure across regions.

Table 14 supplies only the regional flood-exposure input for that comparison.
It does not combine exposure with investment. It does not judge whether
flood-control spending is enough, fair, effective, or caused by any factor.

## Source authority

| Input | Role in Table 14 |
| --- | --- |
| `01-bronze.flood_susceptibility` | Selected MGB flood-area rows, raw `flood_susceptibility_code`, and `geometry_json` |
| `02-silver.config_mgb_susceptibility_mapping` | The only authority for code-to-level and severity-rank standardization |
| `02-silver.silver_psgc_place` | Current official region set and PSGC lineage |
| `01-bronze.boundaries` | Region boundary geometry, boundary versions, and boundary lineage |
| `01-bronze.load_log` | Newest terminal load state, audited row count, and optional MGB publisher version |
| `04-validation.dq_results` | Latest Bronze MGB and boundary validation evidence |
| `04-validation.silver_config_dq_results` | Latest Silver CONFIG validation evidence |
| `04-validation.silver_dq_results` | Selected Silver PSGC validation evidence |

Table 14 does not read DPWH projects, flood-control projects, Census Table C,
`silver_region_population`, `silver_project`, `silver_project_source_match`,
`silver_project_region_map`, or Gold. Table 13 runs earlier in the milestone
sequence but is not a data dependency. Table 14 never rereads R2 directly.

## Dependency order

If Bronze, CONFIG, and PSGC are accepted and unchanged:

1. Review the existing accepted upstream evidence.
2. Run `notebooks/02_silver/09_silver_region_flood_exposure.ipynb`.
3. Run `notebooks/04_validation/07_validation_silver_region_flood_exposure.ipynb`.

If MGB or boundary Bronze changed, run the Bronze pipeline and Bronze validation
first.

If the MGB mapping configuration changed, run these first:

1. `notebooks/02_silver/00_config_mappings.ipynb`
2. `notebooks/04_validation/02_validation_silver_config.ipynb`

If PSGC changed, also run these before Table 14:

1. `notebooks/02_silver/01_silver_psgc_place.ipynb`
2. `notebooks/04_validation/03_validation_silver_geography_population.ipynb`

Project foundation, flood-control reconciliation, and Table 13 do not need to
rerun for Table 14.

## Table grain and key

Grain: one official PSGC region × one active `APPROVED` standardized MGB
susceptibility level × the selected MGB snapshot × the selected boundary
snapshot × one deterministic flood-exposure run.

The expected row count is official region count × approved level count. Both
counts are derived at runtime from `silver_psgc_place` and the configuration
table. Neither count is hardcoded.

Primary key: `region_flood_exposure_key`.

The key is `SHA2(psgc_region_code | flood_susceptibility_level | run_id, 256)`.
It follows the current Silver SHA-256 convention. It is not the future Gold
BIGINT surrogate key. Gold owns serving-layer surrogate keys.

## MGB source grain

One Bronze row is one source flood-area row in the approved trimmed extract.
The repository does not claim a stable business key for each MGB polygon.
Table 14 does not invent one.

MGB lineage is the selected snapshot, ingest run, optional publisher version,
mapping version, boundary version, PSGC version, area rule version, and
deterministic Silver run.

## Susceptibility mapping governance

Only active `APPROVED` rows with source system `DENR MGB flood susceptibility`
are read. Exactly one active approved `mapping_version` and one `source_version`
must exist, or the run stops.

Each raw code must map to one level and rank. Levels and ranks must be
one-to-one. The notebook contains no `CASE` mapping of `LF`, `MF`, `HF`, or
`VHF`. The current configuration maps them to Low, Moderate, High, and Very
High with ranks 1 to 4.

The mapping table `source_version` is `unversioned-official-code-contract`.
It describes the code-to-label contract. It is not the MGB Bronze snapshot and
not a publisher release. Table 14 keeps it in `mgb_mapping_source_version`.

## Unmapped and No rating behavior

Blank codes, `No rating`, and any other unapproved code are `UNMAPPED`. They
never contribute to Low, Moderate, High, or Very High area. They are never
converted to `Unknown` or any other level.

They stay in source accounting and appear as FLAG findings. Gold may later
route unresolved relationships through a governed unknown member. That Gold
behavior does not permit a Silver `Unknown` mapping.

The accepted October 6 profile recorded 7 blank-rating rows with geometry,
16 `No rating` rows with geometry, and 1,815 rows with both fields blank. These
are reference findings only. Runtime counts decide the actual values.

## Geometry parsing

Databricks parses GeoJSON as SRID 4326 longitude and latitude. The parser first
tries `TRY_TO_GEOMETRY` on the text as published. When that fails, it applies
the targeted normalization already used for boundaries. That normalization
removes quotes only around numeric tokens and bracketed coordinate strings. It
never strips JSON quotes globally.

The MGB encoding was not verified from the 2 GB source during development
because the file is not in the repository. The notebook therefore verifies it
at runtime. Step 3 counts declared GeoJSON types, quoted numbers, and Esri
`rings` keys. Each row records the parse path that succeeded. The run stops if
mapped rows have geometry text but none parse.

Each row receives one geometry status:

- `BLANK_GEOMETRY`
- `UNPARSEABLE_GEOMETRY`
- `EMPTY_GEOMETRY`
- `UNSUPPORTED_GEOMETRY_TYPE`
- `INVALID_GEOMETRY`
- `USABLE_GEOMETRY`

Only a nonempty, OGC-valid Polygon or MultiPolygon is usable. Invalid geometry
is excluded and flagged. It is not repaired with `ST_BUFFER` or any other hidden
rule. A future repair rule would need its own version and documentation.

## Region boundary strategy

Table 14 is region-first. It parses only boundary rows whose
`administrative_level` is `region` in the selected snapshot. It matches their
`psgc_code` exactly to current official regions. It never compares MGB polygons
with province, municipality, or barangay shapes.

Each official region receives one boundary status:

| Status | Meaning |
| --- | --- |
| `VALID_REGION_BOUNDARY` | Exactly one parseable, nonempty, valid Polygon or MultiPolygon |
| `NO_SAFE_REGION_BOUNDARY` | No region feature exists for the current PSGC code |
| `AMBIGUOUS_REGION_BOUNDARY` | More than one region feature has the code. Nothing is deduplicated. |
| `INVALID_REGION_GEOMETRY` | The single feature is unparseable, empty, invalid, or not polygonal |

The safe set is small enough to broadcast. The run stops when no official
region has a safe boundary.

## PSGC and boundary version mismatch

Table 13 documents that the inspected boundary artifact reports PSGC version
`2023-10-24` and boundary version `2023-11-06`. The current PSGC source reports
`2Q 2026 as of 2026-06-30` and includes 18 regions. The boundary artifact has
17 region polygons.

Table 14 keeps the boundary snapshot, boundary version, and boundary PSGC
version separate from PSGC lineage. `boundary_version_status` publishes
`VERSION_MISMATCH_VISIBLE` when the versions differ.

## Negros Island Region limitation

The current PSGC includes Negros Island Region. The selected boundary snapshot
predates it, so no boundary feature is expected for that code. Its rows keep
`NULL` measures with `NO_SAFE_REGION_BOUNDARY`. This is no data, not zero
exposure.

The older Region VI and Region VII polygons are expected to include territory
that the current PSGC assigns to Negros Island Region. This is inferred from
the boundary and PSGC version dates. It is not yet measured. The validator
reports it at runtime as a territory-difference FLAG. That check compares
province-level boundary codes with the current PSGC hierarchy.

Table 14 does not hardcode a Negros polygon. It does not split Regions VI or
VII or apply a name-based repair. No approved mapping from old boundary codes
to current PSGC geography exists. A lower-level boundary rebuild is therefore
out of scope. The table recovers naturally when a newer boundary snapshot adds
the missing region.

How Gold presents Region VI and VII exposure under this limitation is a team
decision. It is not resolved by this milestone.

## BARMM and NCR

BARMM is not excluded. The DPWH BARMM coverage gap belongs to later investment
comparison, not to the hazard layer. If BARMM has a safe boundary, its exposure
is calculated like any other region.

NCR remains its own official region. Table 14 is region-level, so no province
hierarchy is needed or invented for NCR.

## Spatial intersection rule

Mapped usable MGB rows join the safe region set with `ST_INTERSECTS`.
`ST_INTERSECTION` runs only for intersecting pairs. A polygon that crosses a
regional border yields one clipped fragment per region. Its area is split
between regions rather than assigned wholly to one region.

Fragments with zero projected area are border touches. They do not count as
exposure or as contributing polygons.

## Within-level dissolve

MGB polygons of the same level may overlap. Clipped fragments for each region
and level are dissolved with `ST_UNION_AGG` before area is measured. Summing
raw polygon areas would double-count overlap.

`within_level_overlap_sqkm` records the area removed by the dissolve:

```text
within_level_overlap_sqkm = sum of clipped fragment areas - dissolved level area
```

`source_polygon_count` counts contributing source rows before dissolve.
`intersection_fragment_count` counts region-by-polygon intersection results
before dissolve. They are equal by construction because each safe region has
exactly one boundary feature. The validator proves the equality.

A polygon crossing two regions contributes to both regional counts. Do not sum
`source_polygon_count` across regions as a national unique-polygon total.

## Cross-level overlap

Low, Moderate, High, and Very High polygons may overlap one another. Table 14
does not assume a severity precedence such as Very High overriding High. No
approved business rule supports one.

The same `GROUPING SETS` pass that dissolves each level also dissolves all
levels together for each region. This avoids running the intersection twice.

```text
region_cross_level_overlap_sqkm = sum of level areas in region - area of all-level union in region
```

`level_area_additivity_status` tells Gold whether level areas may be summed:

- `ADDITIVE_WITHIN_TOLERANCE`
- `NON_ADDITIVE_CROSS_LEVEL_OVERLAP`
- `NOT_EVALUATED` when no safe boundary exists

Each published level area remains a correct per-level measure, so overlap does
not block publication. Summed level exposure is unsafe for a non-additive
region. Gold must not present that sum as unique total area.

The only numeric topology tolerance is `overlap_tolerance_sqkm = 0.01`. It
decides overlap materiality and absorbs floating-point noise. It is declared
once and recorded in `transformation_rule_version`.

## CRS choice and area formula

Source geometry stays in SRID 4326 for parsing, predicates, clipping, and
dissolve. Area is never read in SRID 4326 because its units are square degrees.

Area uses EPSG:6933, WGS 84 / NSIDC EASE-Grid 2.0 Global. It is an equal-area
cylindrical projection in metres. One CRS covers the whole Philippines,
including Palawan and the Kalayaan area.

UTM zone 51N and the PRS92 zones are conformal, not equal-area. They also split
the country across zones. A local developer comparison found EPSG:6933 within
about 0.003% of geodesic area for one-degree cells between 4 and 21 degrees
north. UTM 51N differed by up to about 0.8% at the western edge. These were
local checks, not Databricks results.

```text
region_area_sqkm = ST_AREA(ST_TRANSFORM(region boundary, 6933)) / 1,000,000
susceptible_area_sqkm = ST_AREA(ST_TRANSFORM(dissolved level geometry, 6933)) / 1,000,000
share_of_region_area_pct = 100 * susceptible_area_sqkm / region_area_sqkm
```

The SRID is declared once as a SQL session variable. `area_calculation_crs`
publishes `EPSG:6933`. `area_rule_version` publishes
`silver-region-flood-exposure-area-v1|clip-dissolve-equal-area|EPSG:6933`.

Execution requires a runtime with native spatial SQL. `ST_TRANSFORM` requires
Databricks Runtime 17.1 or later. A STOP check proves the transformed region
geometry carries the approved SRID. A runtime that cannot transform therefore
fails visibly instead of producing square degrees.

## Region area denominator

`region_area_sqkm` is the projected area of the one safe region boundary used
for clipping. Every level row for a region carries the same denominator. The
validator recalculates it independently and checks that the square-kilometre
to square-degree ratio is plausible for Philippine latitudes.

Intermediate values keep full double precision. Publication rounds once to
`DECIMAL(18,4)` for areas and `DECIMAL(7,4)` for the share. No `ABS`, `LEAST`,
or `GREATEST` clamping hides an invalid value.

## Zero versus no data

| Region boundary | Exposure found | `spatial_match_status` | Measures |
| --- | --- | --- | --- |
| Safe | Yes | `CALCULATED` | Calculated values |
| Safe | No | `NO_MAPPED_EXPOSURE` | Real zero area, share, and counts |
| Missing, ambiguous, or invalid | Not evaluated | `NO_SAFE_REGION_BOUNDARY` | `NULL` area, share, counts, and overlap |

Missing geography is never published as zero exposure.

## Full region × level grid

The output starts from every official region cross joined with every approved
level. Calculated exposure is then left joined. Every current region therefore
appears for every approved level, even when its boundary is missing.

## Source row accounting

The transformation and validator both enforce this reconciliation:

```text
selected MGB rows
= mapped approved + usable geometry
+ mapped approved + unusable geometry
+ unmapped or unrated + usable geometry
+ unmapped or unrated + unusable geometry
```

The total must also equal the audited `rows_loaded`. The expected difference is
zero. The 63,684-row historical total is a reference, not an invariant.

## Snapshot, mapping, and rule lineage

Each row retains these separate concepts:

- MGB snapshot, Bronze ingest run, optional publisher version, and load time
- mapping version, mapping source contract, and mapping rule
- boundary snapshot, ingest run, source system, boundary version, boundary
  PSGC version, load time, and feature count
- PSGC snapshot, ingest run, publisher version, Silver run, and load time
- `area_calculation_crs`, `area_rule_version`, and `transformation_rule_version`
- deterministic `run_id` and `source_load_ts`

`source_load_ts` is the latest of the MGB, boundary, and PSGC load timestamps.
The optional publisher version comes only from `load_log`. It is never inferred
from file metadata.

Boundary snapshot columns describe the boundary snapshot that was searched.
They are therefore present on no-data rows too. `boundary_feature_count` shows
whether a feature existed for that region.

## Deterministic run and idempotency

The run ID hashes these contracts:

- MGB snapshot, ingest run, and publisher version or `NO_PUBLISHER_VERSION`
- mapping version and mapping source contract
- boundary snapshot, ingest run, and boundary version
- PSGC snapshot, Silver run, and PSGC version
- area CRS, area rule version, and transformation rule version

No date, timestamp, UUID, or random value enters logical identity. The table is
rebuilt with `CREATE OR REPLACE TABLE`. An exact rerun reproduces the same run
ID and keys and never appends duplicates.

## Low-cost design

- The spatial join is MGB rows × the small safe region set, broadcast.
- It is never MGB rows × all boundary shapes, and never MGB rows × projects.
- Only lineage columns are read for the upstream gates.
- The transformation reads MGB geometry text three times: profile, accounting
  gate, and publish. Only the gate and the publish step parse geometry.
- The dissolve and the cross-level union share one aggregation pass.
- Intermediate geometry uses temporary views, not permanent tables.
- No cache, repartition, `OPTIMIZE`, `ZORDER`, Python, UDF, or spatial library is used.
- The validator parses MGB once and tests each row against one safe-region union.

## Validation

`notebooks/04_validation/07_validation_silver_region_flood_exposure.ipynb`
persists results to `04-validation.silver_dq_results` before its STOP gate.
The gate then reads the persisted rows. See
[Data-quality checks](validation.md#silver-regional-flood-exposure-validation)
for the full list.

All seven data-quality attributes have executable checks:

- Consistency: CONFIG and PSGC validation, mapping one-to-one rules, status
  agreement, boundary-status reproduction, denominators, additivity, dissolve,
  counts, and version visibility
- Accuracy: approved-only levels, equal-area CRS, square-kilometre units,
  independent area recalculation, clipping, source SRID, and territory evidence
- Completeness: source accounting, the full grid, unmapped rows, unusable
  geometry, non-intersecting rows, and no-data regions
- Auditability: lineage, key and run reproduction, version gaps, and parse paths
- Validity: controlled statuses, zero versus no data, area and share ranges,
  and geometry findings
- Uniqueness: keys, grain, and boundary lineage duplicates
- Timeliness: newest loads and validation, current snapshots, current mapping
  version, one run, and historical reference comparison

## STOP and FLAG

STOP examples:

- unsafe MGB, boundary, PSGC, or CONFIG upstream state
- source accounting that does not reconcile
- ambiguous approved mapping
- incomplete grid or duplicated grain
- negative area or a share outside 0 to 100
- missing geography published as zero
- area not in the approved equal-area CRS, or in square degrees
- missing mandatory lineage or a broken deterministic identity

FLAG examples:

- blank MGB geometry, blank codes, and `No rating`
- invalid geometry excluded from area
- boundary version mismatch and territory differences
- a missing current region boundary such as Negros Island Region
- the 232-row historical boundary lineage duplicate reference
- an unavailable optional publisher version
- mapped polygons that do not intersect a safe region
- within-level and cross-level overlap findings
- runtime counts that differ from historical references

A FLAG is a visible source limitation, not a failure.

## Known limitations

- The MGB geometry encoding is verified at runtime, not from a local file.
- The boundary snapshot predates the current PSGC release.
- Negros Island Region is expected to be no data until a newer boundary arrives.
- Region VI and VII areas are expected to reflect their older territory.
- Invalid MGB geometry is excluded rather than repaired.
- `ST_UNION_AGG` on detailed polygons is the most expensive step. Runtime cost is
  not yet measured.
- No Databricks runtime result is recorded for this milestone yet.

## Gold handoff

Gold `03-gold.fact_region_flood_exposure` maps `psgc_region_code` to
`region_key` and `flood_susceptibility_level` to `flood_susceptibility_key`. It
can copy these fields directly:

- `susceptible_area_sqkm`, `share_of_region_area_pct`, and `source_polygon_count`
- `mgb_source_version`, `boundary_version`, and `spatial_match_status`
- `area_calculation_crs`, `area_rule_version`, `run_id`, and `source_load_ts`

When `mgb_source_version` is null, Gold should keep its uniqueness grain
traceable through `mgb_source_snapshot_id`. Gold must use
`level_area_additivity_status` before adding level areas together.

Gold must not redo MGB code mapping, geometry parsing, region clipping, area
calculation, overlap handling, boundary-version reconciliation, or coverage
calculation. If Gold needs another spatial intersection, Table 14 is incomplete.

## Analytical interpretation limits

Table 14 measures spatial exposure patterns. It does not prove that
flood-control investment is sufficient or that flood protection is adequate. It
does not show that flooding was caused by infrastructure gaps. It does not show
that a region deserves a specific amount, or that any wrongdoing occurred.

Describe results as regional patterns, relative exposure, and areas for further
investigation.
