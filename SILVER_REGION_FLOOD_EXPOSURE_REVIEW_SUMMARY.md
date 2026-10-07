# Silver regional flood exposure review summary

## Outcome

The current `main` baseline now contains the complete static implementation for
Silver Table 14 and its validation gate.

Implemented output:

- `02-silver.silver_region_flood_exposure`
- Table 14 checks in `04-validation.silver_dq_results`

Requires Databricks execution. Databricks was not available in this
environment. No exposure area, coverage count, overlap finding, or validation
total is claimed.

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

The 2 GB MGB source is not in the repository, so its geometry encoding could
not be inspected locally. The transformation tries GeoJSON as published first.
It then tries the targeted quoted-number normalization proven on boundaries,
and records which path succeeded. Step 3 profiles declared types, quoted
numbers, and Esri `rings` keys from the real data.

Only nonempty, OGC-valid Polygon and MultiPolygon geometry is usable. Invalid
geometry is excluded and flagged without repair. A STOP fires if mapped rows
have geometry text but none parse, so a broken encoding cannot publish zeros.

## Region boundary strategy

Only `region` rows of the selected boundary snapshot are parsed. Their PSGC
codes match current official regions exactly. Each official region is assessed
once as valid, missing, ambiguous, or invalid. The safe set is broadcast. MGB is
never compared with province, municipality, or barangay shapes.

The boundary snapshot predates the current PSGC release. Negros Island Region is
expected to be `NO_SAFE_REGION_BOUNDARY` with `NULL` measures. No polygon is
fabricated and Regions VI and VII are not split. The validator flags
province-level territory differences between the boundary and current PSGC.

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

Not executed. Requires Databricks execution on Databricks Runtime 17.1 or later
for `ST_TRANSFORM`.

These values must come from the first Databricks run:

- selected MGB, boundary, and PSGC snapshots and versions
- MGB source accounting buckets and geometry findings
- safe and no-data regions
- expected and actual output rows
- contributing and non-intersecting MGB rows
- within-level and cross-level overlap
- total susceptible area by level
- PASS, FLAG, and FAIL totals

## Validation results

The validator defines 57 checks covering all seven attributes: 36 STOP and 21 FLAG. Blocking checks
use action `stop`. Review findings use action `flag`. Evidence is persisted
before the gate, and the gate reads the persisted rows.

Runtime PASS, FLAG, and FAIL totals require Databricks execution.

## Local verification

- notebook JSON parsing: passed
- SQLFluff 4.3.0 on the 20 new SQL cells with parse errors enabled: 0 unparsable
  segments and 0 rule findings
- CI SQLFluff command `sqlfluff lint notebooks`: passed
- Pytest: 224 tests passed, including 60 new Table 14 tests
- Ruff lint and format check: passed
- markdownlint-cli2: 0 issues
- local relative-link and anchor check: 0 broken links
- Vale 3.22.0 on changed Markdown: 0 errors, 0 warnings, and 0 suggestions

The repository CI runs SQLFluff on `.sql` files only. The SQL cell check above
was an additional local step.

## Runtime risks to watch on first execution

- `ST_TRANSFORM` must accept SRID 6933. A STOP proves the transformed SRID.
- `ST_UNION_AGG` on detailed MGB polygons is the most expensive step.
- Clipping may produce mixed geometry collections at region borders. These must
  be accepted by `ST_UNION_AGG`.
- MGB geometry validity rates are unknown until the first run.

## Unresolved limitations

- The boundary snapshot predates the current PSGC release.
- Negros Island Region is expected to have no safe boundary.
- Regions VI and VII are expected to reflect older territory. The team must
  decide how Gold presents them.
- Invalid MGB geometry is excluded rather than repaired.
- Blank and `No rating` MGB rows remain unresolved by design.
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
