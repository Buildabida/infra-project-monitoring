# Silver regional flood exposure review summary

## Outcome

The current pull-request branch contains the complete implementation for Silver
Table 14 and its validation gate.

Implemented output:

- `02-silver.silver_region_flood_exposure`
- Table 14 checks in `04-validation.silver_dq_results`

The transformation and validation notebooks were executed successfully in
Databricks against the selected snapshots.

Runtime evidence confirmed the expected 72-row grain, complete MGB source-row
reconciliation, deterministic keys, zero duplicate grain rows, governed
territory-mismatch handling, and no blocking validation failures.

## Baseline reviewed

Implementation started from `main` at commit
`bca73cb6547669b6159a063e2e0323d2f7082ddb`. The supplied repository archive had
no file differences from that commit.

Current main already contained Silver Tables 1 through 13:

- CONFIG 1 to 5: the five configuration tables
- geography and population 6 to 8: `silver_psgc_place`,
  `silver_population_place_reconciliation`, and `silver_region_population`
- project foundation 9 and 10: `silver_dpwh_project_component` and
  `silver_project`
- source reconciliation 11 and 12: `silver_flood_control_component` and
  `silver_project_source_match`
- geographic mapping 13: `silver_project_region_map`

This milestone reads only the accepted contracts it needs. It does not redesign
or recreate Tables 1 through 13.

## Files changed

The complete file list is in
`SILVER_REGION_FLOOD_EXPOSURE_CHANGE_MANIFEST.md`.

## Table grain

One official PSGC region × one active `APPROVED` standardized MGB
susceptibility level × the selected MGB snapshot × the selected boundary
snapshot × one deterministic flood-exposure run.

The expected row count is official region count × approved level count. Both
come from the current inputs at runtime. Neither is hardcoded.

`region_flood_exposure_key` and `run_id` are deterministic SHA-256 identities.
They contain no UUID, random value, current date, or current timestamp.

## Verified source contracts

- `01-bronze.flood_susceptibility` exposes `flood_susceptibility_code`,
  `geometry_json`, and the standard Bronze lineage columns.
- `01-bronze.boundaries` exposes `psgc_code`, `administrative_level`,
  `geometry_json`, `source_psgc_version`, `source_boundary_version`,
  `source_file`, `source_feature_id`, and lineage. Table 13 has already parsed
  its region rows successfully in Databricks.
- `02-silver.silver_psgc_place` exposes `REGION` rows with code, raw name,
  version, snapshot, ingest run, Silver run, and load time.
- `02-silver.config_mgb_susceptibility_mapping` holds four active approved rows
  in version `2026-10-v1`: `LF` Low 1, `MF` Moderate 2, `HF` High 3, and `VHF`
  Very High 4. The source contract is `unversioned-official-code-contract`.
- `04-validation.dq_results`, `silver_config_dq_results`, and
  `silver_dq_results` provide the upstream safety evidence.

## MGB mapping contract

Only active `APPROVED` rows of one selected mapping version are consumed.
Multiple active versions, duplicate raw codes, or a level and rank that are not
one-to-one stop the run. The notebooks contain no `CASE` mapping of MGB codes.

Blank codes, `No rating`, and other unapproved values remain `UNMAPPED`. They
never contribute to an approved level and are never mapped to `Unknown`.

## Geometry strategy

The 2 GB MGB source is not stored in the repository, so geometry encoding is
verified during Databricks execution.

The transformation and validator use the same controlled parsing sequence:

1. geometry as published
2. targeted quoted-number normalization
3. supported Esri `rings` conversion

Runtime execution confirmed that Esri `rings` is the dominant path for the
selected snapshot. A total of 61,855 rows were converted through the Esri path.

The final validation classified 59,501 geometries as usable. It reported zero
usable rows with an unexpected SRID and zero usable rows outside the configured
longitude-latitude screen.

Only nonempty, OGC-valid Polygon and MultiPolygon geometry is usable. Invalid,
empty, unsupported, blank, and unparseable geometry remains visible through
validation and source accounting rather than being silently repaired.

## Region boundary strategy

Only `region` rows of the selected boundary snapshot are parsed. Their PSGC
codes match current official regions exactly. Each official region is assessed
once as valid, missing, ambiguous, or invalid. The safe set is broadcast. MGB is
never compared with province, municipality, or barangay shapes.

The boundary snapshot predates the current PSGC release.

Runtime comparison with current PSGC territory evidence identified:

- Region VI as `BOUNDARY_TERRITORY_MISMATCH`
- Region VII as `BOUNDARY_TERRITORY_MISMATCH`
- Negros Island Region as `NO_SAFE_REGION_BOUNDARY`
- BARMM as `BOUNDARY_TERRITORY_MISMATCH`

Only `VALID_REGION_BOUNDARY` rows enter the safe spatial set.

The four affected regions publish `NULL` exposure measures rather than false
zeros. No polygon is fabricated, no region is manually split, and no hidden
territorial correction is applied.

## CRS and area rule

Source geometry stays in SRID 4326 for parsing, predicates, clipping, and
dissolve. Area uses EPSG:6933, WGS 84 / NSIDC EASE-Grid 2.0 Global, an
equal-area projection in metres. The SRID is declared once as a session
variable.

A local developer comparison with `pyproj` found EPSG:6933 within about 0.003%
of geodesic area across Philippine latitudes. UTM 51N differed by up to about
0.8% near Palawan. This comparison was a design check only. It is not shipped
code and not Databricks evidence.

`area_rule_version` is
`silver-region-flood-exposure-area-v1|clip-dissolve-equal-area|EPSG:6933`.

## Overlap handling

Within each region and level, clipped fragments are dissolved with
`ST_UNION_AGG` before area is measured. `within_level_overlap_sqkm` records the
area removed.

Cross-level overlap is measured by the same `GROUPING SETS` aggregation through
an all-level union per region. No severity precedence is applied.
`level_area_additivity_status` tells Gold when level areas must not be summed.
The tolerance `overlap_tolerance_sqkm = 0.01` is declared once and recorded in
`transformation_rule_version`.

## Source accounting

The transformation and validator both require this reconciliation:

```text
selected MGB rows
= mapped approved + usable geometry
+ mapped approved + unusable geometry
+ unmapped or unrated + usable geometry
+ unmapped or unrated + unusable geometry
```

The total must also equal the audited `rows_loaded`. Historical counts are
reference evidence only.

## Runtime coverage

Databricks execution completed successfully for the selected snapshots.

Output grain:

- official regions: 18
- approved susceptibility levels: 4
- expected rows: 72
- actual rows: 72
- duplicate exposure keys: 0
- duplicate region, level, and run rows: 0

MGB source accounting:

- selected rows: 63,684
- audited Bronze rows: 63,684
- mapped usable: 59,478
- mapped unusable: 2,368
- unmapped usable: 23
- unmapped unusable: 1,815

Geometry evidence:

- Esri `rings` conversions: 61,855
- usable geometry rows: 59,501
- blank geometry rows: 1,815
- unparseable geometry rows: 14
- invalid geometry rows: 2,340
- empty or unsupported geometry rows: 14

Spatial coverage:

- safe regions: 14
- no-data regions: 4
- contributing mapped MGB rows: 51,317
- mapped usable rows without a safe-region intersection: 8,161

Overlap findings:

- region-level rows with within-level overlap removed: 14
- total within-level overlap removed: 75.7871 sqkm
- regions with cross-level overlap: 4
- total cross-level overlap: 4.0820 sqkm

The runtime findings are evidence for this selected execution and are not
hardcoded as future input expectations.

## Validation results

The validator defines 58 checks covering all seven data-quality attributes:

- 37 blocking `STOP` checks
- 21 non-blocking `FLAG` checks

Runtime result:

- 44 `PASS`
- 14 `FLAG`
- 0 `FAIL`

All blocking checks passed.

The remaining FLAG results preserve source-quality, topology, lineage, and
coverage limitations for review. They do not silently modify or repair source
data.

Validation evidence is persisted before the blocking gate, and the gate reads
the persisted evidence.

## Repository and CI verification

- notebook JSON parsing: passed
- Pytest: 226 tests passed, including 62 Table 14 tests
- Ruff lint: passed
- Ruff format check: passed
- SQLFluff: passed
- markdownlint-cli2: passed
- relative-link check: passed
- Vale writing checks: passed
- latest GitHub Actions workflow: passed

## Runtime observations and follow-up

- `ST_TRANSFORM` executed successfully with the governed area CRS.
- `ST_UNION_AGG` completed successfully on the selected MGB snapshot.
- Invalid MGB geometry remains excluded rather than silently repaired.
- The selected MGB snapshot contains measurable within-level and cross-level
  overlap, which remains visible through validation.
- Performance was sufficient for this execution, but `ST_UNION_AGG` remains the
  main spatial operation to monitor if future MGB snapshots grow materially.
- Boundary-version differences remain the main geographic limitation for
  Regions VI, VII, NIR, and BARMM.

## Unresolved limitations

- The selected boundary snapshot predates the current PSGC release.
- Region VI is `BOUNDARY_TERRITORY_MISMATCH`.
- Region VII is `BOUNDARY_TERRITORY_MISMATCH`.
- Negros Island Region is `NO_SAFE_REGION_BOUNDARY`.
- BARMM is `BOUNDARY_TERRITORY_MISMATCH`.
- These geographic findings are source-version limitations, not pipeline
  failures. Their exposure measures remain `NULL` until safe geography is
  available.
- Invalid MGB geometry is excluded rather than repaired.
- Blank and `No rating` MGB rows remain unresolved by design.
- The optional MGB publisher version is unavailable for the selected snapshot.
- Cross-level overlap means susceptibility-level areas must not automatically
  be summed for every region.
- Table 15, Gold, dashboards, and Genie remain outside this milestone.

## Gold handoff

Gold `fact_region_flood_exposure` maps `psgc_region_code` to `region_key` and
`flood_susceptibility_level` to `flood_susceptibility_key`. It copies the
measures, statuses, versions, CRS, rule version, `run_id`, and
`source_load_ts`. Gold must check `level_area_additivity_status` before adding
level areas. It must not repeat any spatial processing.

## Runtime handoff

Use this order in Databricks when upstream inputs are accepted and unchanged:

1. `notebooks/02_silver/09_silver_region_flood_exposure.ipynb`
2. `notebooks/04_validation/07_validation_silver_region_flood_exposure.ipynb`

Rerun configuration, PSGC, or Bronze first only when those inputs changed.
Record every numerator and denominator, review every FLAG, and keep the executed
evidence before downstream promotion.
