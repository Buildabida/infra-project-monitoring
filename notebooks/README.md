# Pipeline notebooks

These Databricks notebooks present the Bronze batch as a documented sequence of
small, reviewable steps. Narrative cells explain each decision. Code cells delegate
shared mechanics to `src/bronze.py` and source contracts to `src/config.py`.

Silver uses SQL cells in Databricks notebooks.
Governed mappings remain separate from geography and population transformations.

## Bronze principles

- **Raw preserving:** Source business values and legitimate duplicate rows remain.
- **Batch-based:** One bounded CSV artifact is selected for each source.
- **Idempotent:** A skip is safe only when the current table and artifact identity agree.
- **Parameterized:** Widgets select snapshot, version, and path behavior without duplicating constants.
- **Snapshot-aware:** Rows and `load_log` link Bronze to the R2 artifact.
- **Low cost:** Metadata and header checks precede Spark. Strings avoid schema inference.
  Large-source validation uses grouped calculations.
- **Resilient:** Malformed artifacts fail before replacement. Delta writes are atomic.
  Conflicts are audited, and failures remain visible.

## Documented sequence

This table explains the Bronze batch and the first Silver milestones, steps 1 to 28.
For the complete current run order from setup to the dashboard, use the
[full production run order](#d-57-production-rerun-order) below, or simply run the
[pipeline job](../resources/README.md).

| Step | Notebook | Responsibility |
| --- | --- | --- |
| 1 | `00_setup/00_setup_workspace` | Define missing schemas and verify the existing R2-backed volume without destructive setup. |
| 2 | `00_setup/01_check_sources` | Check all six files, metadata, CSV headers, and required field groups without full Spark scans. |
| 3 | `01_bronze/01_bronze_dpwh_projects` | Preserve DPWH project rows and raw business values. |
| 4 | `01_bronze/02_bronze_flood_control` | Preserve source features and legitimate repeated Contract IDs. |
| 5 | `01_bronze/03_bronze_psgc` | Preserve the geographic reference. Keep population as a cross-check only. |
| 6 | `01_bronze/04_bronze_census_table_c` | Preserve authoritative Table C rows, including known BARMM copies. |
| 7 | `01_bronze/05_bronze_boundaries` | Preserve boundary geometry without project mapping or spatial joins. |
| 8 | `01_bronze/06_bronze_flood_susceptibility` | Preserve the approved trimmed MGB extract with low-compute mechanics. |
| 9 | `04_validation/01_validation_bronze` | Record grouped STOP and FLAG checks without changing Bronze. |
| 10 | `04_validation/02_bronze_acceptance_evidence` | Summarize the latest load and validation evidence without rescanning data. |
| 11 | `02_silver/00_config_mappings` | Create six versioned configuration tables and report mapping coverage. |
| 12 | `04_validation/02_validation_silver_config` | Validate Silver configuration structure, governance, and Bronze coverage. |
| 13 | `02_silver/01_silver_psgc_place` | Standardize the selected official PSGC hierarchy without dropping source rows. |
| 14 | `02_silver/02_silver_population_place_reconciliation` | Reconcile every current Table C row through fail-closed row roles, contextual PSGC matching, and approved aliases. |
| 15 | `02_silver/03_silver_region_population` | Aggregate only accepted matched barangay population to official PSGC regions. |
| 16 | `04_validation/03_validation_silver_geography_population` | Validate row accounting, matches, lineage, region coverage, and population totals. |
| 17 | `02_silver/04_silver_dpwh_project_component` | Preserve every selected DPWH row, extract `componentCategories`, and apply the governed atomic taxonomy without row multiplication. |
| 18 | `02_silver/05_silver_project` | Consolidate one project, classify approved category sets, and protect reported budgets. |
| 19 | `04_validation/04_validation_silver_projects` | Validate row accounting, taxonomy coverage, grain, budget protection, and lineage. |
| 20 | `02_silver/06_silver_flood_control_component` | Preserve every selected flood-control source feature using its real Object ID. |
| 21 | `02_silver/07_silver_project_source_match` | Record exact Contract-ID reconciliation evidence without changing projects. |
| 22 | `04_validation/05_validation_silver_source_reconciliation` | Validate source preservation, exact matching, cost protection, and lineage. |
| 23 | `02_silver/08_silver_project_region_map` | Publish one governed region-mapping result for every canonical project. |
| 24 | `04_validation/06_validation_silver_project_region_map` | Validate project preservation, precedence, targets, conflicts, boundary quality, lineage, and coverage. |
| 25 | `02_silver/08a_silver_mgb_flood_area` | Parse every selected MGB polygon once into `silver_mgb_flood_area`; skip the parse when the snapshot and parse rule are unchanged. |
| 26 | `04_validation/06a_validation_silver_mgb_flood_area` | Validate one-to-one accounting against Bronze, raw codes, keys, lineage, and usable geometry rebuilt from WKB. |
| 27 | `02_silver/09_silver_region_flood_exposure` | Clip approved MGB polygons to safe official region boundaries once and publish equal-area regional exposure. |
| 28 | `04_validation/07_validation_silver_region_flood_exposure` | Validate source accounting, the region × level grid, CRS, zero versus no data, overlap, lineage, and coverage. |
| Bronze coordinator | `run_all.py` | Enforce order, require six safe results, and validate only after the complete Bronze batch. Bronze only. The pipeline job is the orchestrator for every layer. |

## Load Bronze

### Before running

Confirm that you can access the `buildabida-capstone` catalog and this R2-backed
volume directory:

```text
/Volumes/buildabida-capstone/00-source/cloudflare-r2/buildabida/
```

The directory must contain the six files configured in `src/config.py`:

```text
dpwh_projects.csv
flood_control_projects.csv
psgc.csv
population_2024_table_c_test.csv
boundary_bettergov.csv
flood_susceptibility.csv
```

Run these setup notebooks first:

1. `00_setup/00_setup_workspace.sql` defines missing schemas and verifies the
   existing source volume.
2. `00_setup/01_check_sources.py` checks file access, metadata, CSV headers, and
   required field groups without scanning each complete dataset.

Resolve any setup or source-precheck failure before loading Bronze.

### Run the complete Bronze batch

Open `run_all.py` in Databricks, select Serverless compute, and run all cells. This
file is the current Source-to-Bronze coordinator. It does not run Silver or Gold.

The coordinator runs the six source notebooks in order. It starts grouped Bronze
validation only after every source returns a safe status.

The coordinator accepts these optional parameters:

- `snapshot_id`: Leave blank to derive a deterministic ID from each file's metadata.
- `source_version`: Supply a publisher or release label when one is available.
- `force_reload`: Keep `false` for a normal run. Use `true` only for an intentional
  replacement of an otherwise identical selected snapshot.

Use each source notebook directly only for a controlled test that needs the
`source_path` override.

### Expected result

Each source must return one of these statuses:

- `SUCCESS`: The selected snapshot was committed and audited.
- `SKIPPED_IDEMPOTENT`: The current table already contains the exact snapshot,
  matching artifact identity, and expected row count.

Any other source result blocks validation. A successful coordinated run also
finishes `04_validation/01_validation_bronze` without a blocking check failure.

Review the stored results here:

- `buildabida-capstone.01-bronze.load_log` contains ingestion audit records.
- `buildabida-capstone.04-validation.dq_results` contains grouped validation results.
- `04_validation/02_bronze_acceptance_evidence.sql` summarizes the latest accepted
  load and validation evidence without rescanning the Bronze tables.

## Load Silver

Silver currently implements:

- six configuration tables
- three geography and population outputs
- silver_dpwh_project_component
- silver_project
- silver project validation
- silver_flood_control_component
- silver_project_source_match
- Silver source-reconciliation validation
- silver_project_region_map
- Silver project-region mapping validation
- retained read-only provincial reporting readiness profile
- Silver province reporting-area reference and selected boundaries
- Silver province reporting-area population
- Silver one-row-per-project reporting-area mapping
- Silver province-reporting validation
- silver_mgb_flood_area
- Silver MGB flood-area validation
- silver_region_flood_exposure
- Silver regional flood-exposure validation
- silver_project_flood_map
- Silver project flood-mapping validation

Gold dimensions and facts are in [Load Gold](#load-gold).

Run these notebooks after Bronze has passed its blocking checks:

1. `02_silver/00_config_mappings.ipynb`
2. `04_validation/02_validation_silver_config.ipynb`

The configuration notebook creates these Delta tables:

- `02-silver.config_place_name_alias`
- `02-silver.config_project_category_mapping`
- `02-silver.config_project_status_mapping`
- `02-silver.config_mgb_susceptibility_mapping`
- `02-silver.config_manual_geographic_match`

The notebook seeds the seven approved DPWH component-category rules and the four
documented MGB code mappings. Other rule sets stay empty until a reviewer
approves them.

Review the coverage output before running the validator.
The validator saves evidence in `04-validation.silver_config_dq_results`.

Run both notebooks in Databricks.
Local tests verify notebook structure but cannot create Unity Catalog tables.

See [Silver configuration mappings](../docs/silver/silver_config_mappings.md) for table
grains, approval rules, and cost controls.

### Geography and population

After CONFIG validation passes every stop check, run:

1. `02_silver/01_silver_psgc_place.ipynb`
2. `02_silver/02_silver_population_place_reconciliation.ipynb`
3. `02_silver/03_silver_region_population.ipynb`
4. `04_validation/03_validation_silver_geography_population.ipynb`

The PSGC table must succeed before Table C reconciliation.
Reconciliation must succeed before region aggregation.
Do not continue after a blocking check failure.

The validator stores results in `04-validation.silver_dq_results` before enforcing its
gate. Review every `FLAG`, especially ambiguous and unmatched rows, without deleting them.

These notebooks use only current Bronze PSGC, current Bronze Table C, approved place
aliases, and compact audit evidence. They do not scan project, boundary, or MGB data.

See [Silver geography and population](../docs/silver/silver_geography_population.md) for grains,
matching rules, population authority, lineage, and known limitations.

### Project foundation

After Silver configuration validation passes, run:

1. `02_silver/04_silver_dpwh_project_component.ipynb`
2. `02_silver/05_silver_project.ipynb`
3. `04_validation/04_validation_silver_projects.ipynb`

The component notebook preserves every selected Bronze DPWH source row. It
extracts `componentCategories` from `source_record_json`, normalizes the
comma-separated category set, and maps atomic values with the governed config.
It aggregates immediately back to the source-row grain.

The project notebook consolidates component-level evidence into one canonical
project-level record. One approved category keeps its sector. More than one
approved category becomes `Multi-sector`. Missing or unapproved categories stay
unmapped with a `NULL` sector.

The validator confirms:

- Bronze-to-component row preservation
- component-to-project accounting
- project uniqueness
- budget double-count protection
- mapped and unmapped project and reported-budget coverage
- single-sector, multi-sector, missing-category, and DPWH flood-related counts
- source lineage completeness
- retained source-quality findings

The taxonomy changes the component and project run identities. After the
foundation validator passes, rerun these dependent outputs in order:

1. `02_silver/07_silver_project_source_match.ipynb`
2. `04_validation/05_validation_silver_source_reconciliation.ipynb`
3. `02_silver/08_silver_project_region_map.ipynb`
4. `04_validation/06_validation_silver_project_region_map.ipynb`
5. `02_silver/10_silver_project_flood_map.ipynb`
6. `04_validation/08_validation_silver_project_flood_map.ipynb`

Table 15 also needs a current `silver_mgb_flood_area` and its `06a` evidence.
They do not depend on the taxonomy, so they need no rerun here.

Skip `06_silver_flood_control_component.ipynb` when its selected source and
rule identity are unchanged.

Run all notebooks in Databricks.

Local tests verify notebook structure and contracts but do not create Unity Catalog tables.

See [Silver project foundation](../docs/silver/silver_project_cleaning.md) for project-table contracts, consolidation rules, and known limitations.

### Flood-control source reconciliation

After the project foundation validator passes, run:

1. `02_silver/06_silver_flood_control_component.ipynb`
2. `02_silver/07_silver_project_source_match.ipynb`
3. `04_validation/05_validation_silver_source_reconciliation.ipynb`

The component notebook preserves one row for each selected Bronze flood-control
`object_id`. The match notebook groups only usable source Contract IDs and compares
them with `silver_project` using exact `UPPER(TRIM(contract_id))` equality.

The validator persists results to `04-validation.silver_dq_results` before enforcing
its blocking gate. It reports invalid IDs, repeats, cost conflicts, unmatched groups,
and ambiguous targets without changing either source table.

Run all three notebooks in Databricks. Local tests verify structure and contracts but
do not create Unity Catalog tables.

See [Silver source reconciliation](../docs/silver/silver_source_reconciliation.md) for table
grains, source roles, matching rules, cost protection, lineage, and limitations.

### Project-region mapping

Table 13 depends on current configuration, PSGC geography, project foundation,
and their validators. Flood-control source reconciliation is not a dependency.

Use this complete dependency-aware order when every relevant input changed:

1. `02_silver/00_config_mappings.ipynb`
2. `04_validation/02_validation_silver_config.ipynb`
3. `02_silver/01_silver_psgc_place.ipynb`
4. `04_validation/03_validation_silver_geography_population.ipynb`
5. `02_silver/04_silver_dpwh_project_component.ipynb`
6. `02_silver/05_silver_project.ipynb`
7. `04_validation/04_validation_silver_projects.ipynb`
8. `02_silver/08_silver_project_region_map.ipynb`
9. `04_validation/06_validation_silver_project_region_map.ipynb`

Steps 3 through 7 can be skipped when their selected inputs and rules did not
change and their accepted tables remain current.

The mapping notebook keeps every canonical project and uses this precedence:

1. exact Central Office non-geographic rule
2. approved manual exception
3. exact project PSGC code when a legitimate field exists. It is currently unavailable.
4. exact standardized official region name
5. approved region alias
6. coordinate and selected region-boundary fallback
7. unresolved result

The validator writes all seven quality attributes to
`04-validation.silver_dq_results` before enforcing its STOP gate. Review mapping
coverage, unmatched and ambiguous projects, coordinate conflicts, boundary
version differences, and optional publisher-version gaps.

See [Silver project-to-region mapping](../docs/silver/silver_project_region_mapping.md)
for the Table 13 grain, D-03 resolution, methods, statuses, lineage, spatial cost
controls, and Gold handoff.

### Provincial reporting readiness profile

Provincial reporting remains a pending team decision. D-34 still keeps the
production capstone at region level. Run the read-only profile only after the
current Silver project, PSGC, boundary, and project-region checks pass:

1. `02_silver/08b_profile_project_province_readiness.ipynb`

The notebook creates temporary views only. It extracts DPWH
`location.province` as source evidence, compares it with official PSGC province
names by normalized exact equality, and performs one longitude-first
`ST_COVERS` join against selected province boundaries. Candidate fan-out is
collapsed immediately to one row per canonical project.

Export every result set before the team chooses strict provinces or governed
province reporting areas. The notebook asserts that project count and reported
budget do not change, but it does not publish a mapping table or claim that a
candidate is approved.

See [province reporting readiness](../docs/silver/province_reporting_readiness.md) for
the options, proposed D-57 text, required evidence, blockers, and execution
checklist.

### Regional flood exposure

Table 14 depends only on MGB and boundary Bronze, `silver_mgb_flood_area`,
Silver configuration, Silver PSGC, and their validators. It does not depend on project foundation,
flood-control reconciliation, or Table 13.

If Bronze, configuration, and PSGC are accepted and unchanged:

1. Review the existing accepted upstream evidence.
2. Run `02_silver/08a_silver_mgb_flood_area.ipynb`. It skips the parse when the
   MGB snapshot and parse rule are unchanged.
3. Run `04_validation/06a_validation_silver_mgb_flood_area.ipynb`.
4. Run `02_silver/09_silver_region_flood_exposure.ipynb`.
5. Run `04_validation/07_validation_silver_region_flood_exposure.ipynb`.

When upstream inputs changed, use this dependency-aware order:

1. Bronze pipeline and Bronze validation, when MGB or boundaries changed
2. `02_silver/00_config_mappings.ipynb`, when the MGB mapping changed
3. `04_validation/02_validation_silver_config.ipynb`, after step 2
4. `02_silver/01_silver_psgc_place.ipynb`, when PSGC changed
5. `04_validation/03_validation_silver_geography_population.ipynb`, after step 4
6. `02_silver/08a_silver_mgb_flood_area.ipynb`
7. `04_validation/06a_validation_silver_mgb_flood_area.ipynb`
8. `02_silver/09_silver_region_flood_exposure.ipynb`
9. `04_validation/07_validation_silver_region_flood_exposure.ipynb`

The exposure notebook uses only the selected region boundaries, active approved
MGB mappings, and native Databricks SQL spatial functions. Area is calculated in
the documented equal-area CRS. Execution requires Databricks Runtime 17.1 or
later for `ST_TRANSFORM`.

The validator writes all seven quality attributes to
`04-validation.silver_dq_results` before enforcing its STOP gate. Review unmapped
and unrated MGB rows, unusable geometry, no-data regions, boundary version and
territory differences, and overlap findings.

See [Silver regional flood exposure](../docs/silver/silver_region_flood_exposure.md)
for the Table 14 grain, CRS, boundary strategy, overlap rules, lineage, and Gold
handoff.

### Project flood mapping

Table 15 depends on the project foundation, MGB Bronze, `silver_mgb_flood_area`,
Silver configuration, and their validators. It does not depend on flood-control reconciliation,
Table 13, or Table 14.

If Bronze, configuration, and the project foundation are accepted and unchanged:

1. Review the existing accepted upstream evidence.
2. Run `02_silver/08a_silver_mgb_flood_area.ipynb` and
   `04_validation/06a_validation_silver_mgb_flood_area.ipynb`, unless they
   already ran for the current MGB snapshot.
3. Run `02_silver/10_silver_project_flood_map.ipynb`.
4. Run `04_validation/08_validation_silver_project_flood_map.ipynb`.

When upstream inputs changed, use this dependency-aware order:

1. Bronze pipeline and Bronze validation, when DPWH or MGB changed
2. `02_silver/00_config_mappings.ipynb`, when the MGB mapping changed
3. `04_validation/02_validation_silver_config.ipynb`, after step 2
4. `02_silver/04_silver_dpwh_project_component.ipynb`, when DPWH changed
5. `02_silver/05_silver_project.ipynb`, after step 4
6. `04_validation/04_validation_silver_projects.ipynb`, after step 5
7. `02_silver/08a_silver_mgb_flood_area.ipynb`, when MGB changed
8. `04_validation/06a_validation_silver_mgb_flood_area.ipynb`, after step 7
9. `02_silver/10_silver_project_flood_map.ipynb`
10. `04_validation/08_validation_silver_project_flood_map.ipynb`

The notebook keeps every canonical project. A project receives a flood level
only when its usable map point falls inside polygons of exactly one approved MGB
level. Points inside several approved levels stay `AMBIGUOUS` because no
severity precedence is approved. Execution requires Databricks Runtime 17.1 or
later, because the governed MGB parser in `08a` uses `ST_TRANSFORM`.

The validator writes all seven quality attributes to
`04-validation.silver_dq_results` before enforcing its STOP gate. Review
coverage against both denominators, projects without usable coordinates, usable
points without an approved polygon, ambiguous projects, and unmapped or unusable
MGB rows.

See [Silver project flood mapping](../docs/silver/silver_project_flood_mapping.md) for
the Table 15 grain, classification rule, lineage, cost controls, and Gold
handoff.

## Load Gold

Gold notebooks live in `03_gold`. They build the dimensions and facts in [Gold model](../docs/model/gold_model.md).
Each notebook first checks that its Silver inputs passed Silver validation. Then it loads rows with `MERGE` on deterministic keys, so a rerun changes nothing.

After every Silver validator passes, run the dimensions in this order:

1. `03_gold/00_gold_dim_date.ipynb`
2. `03_gold/01_gold_dim_region.ipynb` builds `dim_region` and `dim_region_boundary`
3. `03_gold/02_gold_dim_flood_susceptibility.ipynb`
4. `03_gold/03_gold_dim_project_status.ipynb`
5. `03_gold/04_gold_dim_project.ipynb`

Then run the facts, which need every dimension key:

1. `03_gold/05_gold_fact_region_population.ipynb`
2. `03_gold/06_gold_fact_region_flood_exposure.ipynb`
3. `03_gold/07_gold_fact_project_snapshot.ipynb`

Then run `04_validation/09_validation_gold.ipynb`. It checks the grain, keys, values, and lineage of every Gold table, and it compares the totals with Silver. It saves its results to `04-validation.gold_dq_results` before its STOP gate, so a failed check stays visible. Review the FLAG rows for projects without a region, a flood level, or a status. See [Gold validation](../docs/validation/validation.md#gold-validation).

Gold runs no spatial matching. `01_gold_dim_region` reads region shapes from `01-bronze.boundaries` for map storage only (D-35). It needs Databricks Runtime 17.1 or later to parse them.

## Build the analytics views

Analytics lives in one notebook, `05_analytics/01_business_questions.ipynb`. After `09_validation_gold` passes, run:

1. `05_analytics/01_business_questions.ipynb` runs after `09_validation_gold` and `09a_validation_gold_province_reporting` pass. It stops unless current Gold holds exactly one DPWH snapshot. Then it creates the `05-analytics` schema if it does not exist, drops the retired views, and builds the persisted Analytics views, one per capstone insight (D-56, proposed). The views read only current-snapshot Gold and hold no data, so a rerun only replaces their definitions.
2. `04_validation/10_validation_analytics.ipynb` first stops unless the latest Gold validation passed and covers the current project, population, and exposure facts. It also stops unless the latest province Gold validation passed. Then it proves that `05-analytics` holds exactly the Analytics views, rebuilds every view from Gold, compares them row by row, and saves its results to `04-validation.analytics_dq_results` before its STOP gate.

The retired regional progress notebooks (`02_regional_project_progress` and `11_validation_regional_project_progress`, D-55) are removed. Their one-snapshot run stays as [retired evidence](../docs/evidence/regional-project-progress/README.md).

The dashboard reads only these Analytics views. See [Analytics views](05_analytics/README.md) and the [dashboard build specification](../dashboard/dashboard_spec.md).

## Validation connection

`04-validation` is the shared evidence layer for Bronze, Silver, and Gold.
Each layer records checks that match its responsibility.

- Bronze validates source preservation, lineage, snapshot identity, and ingestion safety.
- Silver validates cleaning, typing, deduplication, reconciliation, and geographic matching.
- Gold validates analytical grain, keys, measures, dimensions, and reporting readiness.
- Analytics validates that every dashboard view matches Gold exactly.

This sequence produces Bronze, Silver, Gold, and analytics results. They live in `04-validation`
in separate result tables: `dq_results` for Bronze, `silver_config_dq_results` and
`silver_dq_results` for Silver, `gold_dq_results` for Gold, and `analytics_dq_results`
for the analytics views.
Promotion requires the current layer to pass its blocking checks.

The [end-to-end quality gate](06_data_quality/README.md) reads all of these result
tables at the end of the run. It confirms that every validator ran for this pipeline
run and passed, and that the layers agree on snapshot, project count, and budget.
Then it saves `04-validation.quality_gate_results` and lets the dashboard refresh.

## Future layer organization

Do not add Silver or Gold orchestration to `run_all.py`. It stays a manual
Bronze-only helper. The [pipeline job](../resources/README.md) already orchestrates
every layer with Databricks task dependencies, so no second coordinator is needed.

Keep validation notebooks separate too:

```text
04_validation/
├── 01_validation_bronze.py
├── 02_validation_silver_config.ipynb
├── 03_validation_silver_geography_population.ipynb
├── 04_validation_silver_projects.ipynb
├── 05_validation_silver_source_reconciliation.ipynb
├── 06_validation_silver_project_region_map.ipynb
├── 06a_validation_silver_mgb_flood_area.ipynb
├── 07_validation_silver_region_flood_exposure.ipynb
├── 08_validation_silver_project_flood_map.ipynb
├── 09_validation_gold.ipynb
├── 10_validation_analytics.ipynb
└── 11_publish_acceptance_evidence.sql

06_data_quality/
└── 01_end_to_end_quality_gate.py
```

Shared result-writing helpers can move to `src/validation.py` when Python-based
downstream validators need them. Do not create empty runners or modules before their
corresponding implementation exists.

## Central source contract

The six default paths come from one volume root in `src/config.py`:

```text
/Volumes/buildabida-capstone/00-source/cloudflare-r2/
```

Each source notebook accepts four widgets:

- `snapshot_id`: Optional caller-supplied source snapshot ID.
- `source_version`: Optional publisher or release label stored in `load_log`.
- `force_reload`: Replace an identical selected snapshot when set to `true`.
- `source_path`: Optional path override for a controlled test.

When `snapshot_id` is blank, the loader derives a deterministic ID from inexpensive
artifact metadata. It uses the source name, configured version, path, byte size, and
modification time. It never hashes the full source file.

The loader returns `SKIPPED_IDEMPOTENT` only after it verifies the current Delta table.
The requested snapshot, artifact identity, and expected row count must all match.
Reusing an established snapshot ID with changed metadata is an explicit conflict.

Bronze represents the selected current source snapshot. R2 keeps the raw history.
A new snapshot replaces the current Delta table only after Spark can read and write it.
No loader drops tables, schemas, volumes, or raw files.

CSV business fields remain strings. The shared loader adds technical lineage and
records `STARTED`, `SUCCESS`, `FAILED`, or `SKIPPED_IDEMPOTENT`. It also reconciles
source and Bronze row counts.

The loader does not deduplicate, cast, spatially join, categorize, aggregate,
standardize, or fill business values.

## Design summary

Thin notebooks keep source intent visible. One shared loader owns the mechanics.
A seventh CSV source needs one source contract and one documented notebook.
It also needs source-specific validation and focused tests. This structure avoids
copying ingestion logic or introducing an enterprise framework.

## D-57 production rerun order

The [pipeline job](../resources/buildabida_full_pipeline.job.yml) runs these
files as 50 dependent tasks, and its last task refreshes the dashboard after the
end-to-end quality gate passes. `databricks.yml` includes the job, so
`databricks bundle deploy` keeps it in step with this repository. To run the
files by hand, use this dependency order. Stop immediately after any
failed STOP gate; no Gold reporting-area task may bypass Silver validation, and
no reporting-area Analytics task may bypass Gold validation.

1. `00_setup/00_setup_workspace.sql`
2. `00_setup/01_check_sources.py`
3. `run_all.py`, which runs all six Bronze loads and Bronze validation
4. `04_validation/02_bronze_acceptance_evidence.sql`
5. `02_silver/00_config_mappings.ipynb`
6. `04_validation/02_validation_silver_config.ipynb`
7. `02_silver/01_silver_psgc_place.ipynb`
8. `02_silver/01a_silver_province_reporting_area.ipynb`
9. `02_silver/02_silver_population_place_reconciliation.ipynb`
10. `02_silver/03_silver_region_population.ipynb`
11. `02_silver/03a_silver_province_reporting_area_population.ipynb`
12. `04_validation/03_validation_silver_geography_population.ipynb`
13. `02_silver/04_silver_dpwh_project_component.ipynb`
14. `02_silver/05_silver_project.ipynb`
15. `04_validation/04_validation_silver_projects.ipynb`
16. `02_silver/06_silver_flood_control_component.ipynb`
17. `02_silver/07_silver_project_source_match.ipynb`
18. `04_validation/05_validation_silver_source_reconciliation.ipynb`
19. `02_silver/08_silver_project_region_map.ipynb`
20. `04_validation/06_validation_silver_project_region_map.ipynb`
21. `02_silver/08b_profile_project_province_readiness.ipynb`, optional and
    read-only, for capturing current readiness evidence
22. `02_silver/08c_silver_project_province_map.ipynb`
23. `04_validation/03b_validation_silver_province_reporting.ipynb`
24. `02_silver/08a_silver_mgb_flood_area.ipynb`
25. `04_validation/06a_validation_silver_mgb_flood_area.ipynb`
26. `02_silver/09_silver_region_flood_exposure.ipynb`
27. `04_validation/07_validation_silver_region_flood_exposure.ipynb`
28. `02_silver/10_silver_project_flood_map.ipynb`
29. `04_validation/08_validation_silver_project_flood_map.ipynb`
30. `03_gold/00_gold_dim_date.ipynb`
31. `03_gold/01_gold_dim_region.ipynb`
32. `03_gold/01a_gold_dim_province_reporting_area.ipynb`
33. `03_gold/02_gold_dim_flood_susceptibility.ipynb`
34. `03_gold/03_gold_dim_project_status.ipynb`
35. `03_gold/04_gold_dim_project.ipynb`
36. `03_gold/05_gold_fact_region_population.ipynb`
37. `03_gold/05a_gold_fact_province_reporting_area_population.ipynb`
38. `03_gold/06_gold_fact_region_flood_exposure.ipynb`
39. `03_gold/07_gold_fact_project_snapshot.ipynb`
40. `04_validation/09_validation_gold.ipynb`
41. `04_validation/09a_validation_gold_province_reporting.ipynb`
42. `05_analytics/01_business_questions.ipynb`
43. `04_validation/10_validation_analytics.ipynb`
44. `04_validation/11_publish_acceptance_evidence.sql`
45. `06_data_quality/01_end_to_end_quality_gate.py`, which must pass before the
    dashboard refreshes. See the [quality gate guide](06_data_quality/README.md).

Step 44 is the compact PR evidence publisher. It materializes the latest D-57
Silver, Gold, and Analytics checks, project and reported-budget coverage,
mapping-method totals, separate NCR, independent-city, and BARMM totals,
population coverage and exclusions, selected versions, and a mapping-identity
checksum. Its outputs do not reinterpret or remap any project.

For exact-rerun evidence, run step 44 once, rerun steps 22 and 23 with unchanged
inputs, and then run step 44 again. The final `exact_rerun_status` must be
`PASS`. `RERUN_REQUIRED` is expected after the first evidence capture.

Province flood exposure has no task in this order. It is deferred until a
separate Databricks feasibility run proves that the reporting-area boundary and
MGB intersection is safe and affordable. Regional flood tasks remain required
for the unchanged regional model and existing Analytics.

Expected D-57 outcomes are persisted PASS rows for every STOP check, with FLAG
rows allowed for real coverage limitations. Capture mapped and unmapped project
and budget coverage, mappings by method, conflicts, ambiguity, missing
coordinates, NCR, independent-city, BARMM, population coverage, excluded
population, selected versions, and exact-rerun identities. Do not claim runtime
approval until `03b`, `09a`, and `10_validation_analytics` have executed and their saved evidence
passes. The evidence publisher must also show no blocking failures. A claim of
exact-rerun stability requires two captures with the same project-map run ID
and mapping-identity checksum.

The October 15, 2026 run satisfied those conditions: 43 checks passed,
five non-blocking Silver coverage flags remained visible, and two captures
retained one project-map run ID and one mapping checksum. See the
[province-reporting runtime evidence](../docs/evidence/province-reporting/README.md).

The October 16, 2026 run of the full order, with the v2 province validators and
the Analytics views, also satisfied them: 159 checks were published with no
failed STOP check, and the exact rerun passed against the October 15 capture.
That run found four Databricks SQL errors, fixed in steps 8, 22, 32, and 39. See
the [Analytics evidence](../docs/evidence/analytics-2026-10-16/README.md).
