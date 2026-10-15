# D-55 province reporting-area production handoff

## Decision

D-55, approved October 14, 2026, selects Option B. The reporting-area dimension
contains official PSGC provinces, PSGC cities with no province parent as
`INDEPENDENT_CITY`, NCR as one `NCR` area, and reserved key `0` as `UNKNOWN`.

D-55 supersedes D-34 only where D-34 prohibited province drill-down. Region
remains the parent geography, reconciliation level, BARMM and national control,
and backward-compatible analytical contract.

## Production result

Silver publishes a deterministic reporting-area reference, boundary-status
table, accepted-primary Table C population, and exactly one mapping row per
canonical project. Gold adds the reporting-area and boundary dimensions, the
population fact, and `reporting_area_key` plus mapping states to the existing
project fact. Five new reporting-area Analytics views retain Unknown where
national projects and reported budgets must reconcile.

The project map uses this precedence:

1. non-geographic classification;
2. active approved manual exception;
3. valid unique project PSGC evidence, when available;
4. active approved exact alias;
5. unique longitude-first EPSG:4326 `ST_COVERS` containment;
6. Unknown, unmapped, invalid, or ambiguous.

The current project contract has no legitimate project PSGC field, so stage 3
is unavailable. Raw DPWH `location.province`, including District Engineering
Office text, is never trusted automatically. No fuzzy, substring,
nearest-boundary, or first-candidate rule exists.

## Proof that grain and budget cannot multiply

`08c_silver_project_province_map` aggregates every candidate stage to
`project_key`, joins those one-row views to `silver_project`, and then asserts:

- output rows equal canonical Silver project rows;
- output rows equal distinct `project_key` values;
- output rows equal distinct deterministic mapping keys;
- each key recomputes from `project_key` and the deterministic run ID;
- joined reported budget equals the canonical Silver total with NULL-safe
  equality.

`07_gold_fact_project_snapshot` joins the final one-row project map only once.
Before `MERGE`, it asserts one fact row per canonical project snapshot and the
same reported-budget total as `silver_project`. Gold validation repeats the
current project-count and budget checks. Analytics validation repeats national
mapped plus Unknown reconciliation.

## Exact Databricks order

Run on Serverless compute and stop after any failed STOP check:

1. `00_setup/00_setup_workspace.sql`
2. `00_setup/01_check_sources.py`
3. `run_all.py`
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
21. Optional read-only profile:
    `02_silver/08b_profile_project_province_readiness.ipynb`
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
44. `04_validation/10a_validation_provincial_analytics.ipynb`
45. `04_validation/11_publish_acceptance_evidence.sql`

Gold D-55 tasks must not run before step 23 passes. Analytics must not run
before steps 40 and 41 pass.

## Expected runtime evidence

Every STOP check should persist as `PASS`. Real limitations may persist as
`FLAG`. Do not require or invent 100% coverage. Capture:

- total, mapped, and unmapped projects and mapped percentage;
- total, mapped, and unmapped reported budget and mapped percentage;
- mappings by method, conflicts, ambiguity, and missing coordinates;
- NCR, independent-city, and BARMM totals;
- accepted, unresolved, and excluded population plus coverage;
- selected PSGC, boundary, alias, manual, and rule versions;
- an exact rerun showing unchanged deterministic keys and run IDs.

`04_validation/11_publish_acceptance_evidence.sql` now produces these evidence
sets directly. Run it once, rerun the project map and Silver province validator
without changing inputs, then run the publisher again. The final
`exact_rerun_status` must be `PASS`; the first capture correctly reports
`RERUN_REQUIRED`.

## Reviewed runtime evidence

The October 15, 2026 Databricks export for source snapshot
`metadata-6321c7aa6f2a14e12f4c` contained 48 D-55 checks: 43 `PASS`, five
non-blocking Silver coverage `FLAG` rows, and zero `FAIL` rows. The evidence
preserved 265,656 project rows and reconciled reported budgets through Silver,
Gold, and Analytics. Project mapping resolved 200,110 projects and retained
65,546 under Unknown. This is 75.3267 percent project coverage.

The original export did not contain the expanded budget, method, special-area,
population, or two-capture identity output. Run the new evidence publisher to
capture those fields before describing the implementation as fully
runtime-approved.

## Runtime limitations

- The core D-55 notebooks and validators have run, but the expanded evidence
  publisher still needs its two-capture execution.
- Project mapping coverage is 75.3267 percent in the reviewed snapshot. Unknown
  remains necessary and must not be treated as a failed reconciliation.
- Project PSGC evidence is unavailable in the current canonical source contract.
- Boundary availability and compatibility are recorded per reporting area and
  may legitimately leave some coordinate matches unresolved.
- BARMM remains limited by the DPWH source and is reported, not imputed.
- Population equity is descriptive. It does not establish fairness or
  unfairness.
- Province flood exposure is deferred. No regional exposure is proportionally
  allocated to reporting areas.

## Suggested Git metadata

Branch:

```text
feature/d55-province-reporting-areas
```

Commit title:

```text
feat: add governed province reporting areas
```

Commit description:

```text
Implement D-55 across Silver, Gold, Analytics, validation, tests, and docs.
Preserve regional compatibility and national project and budget reconciliation.
Defer province flood exposure until Databricks feasibility evidence exists.
```

PR title:

```text
Implement D-55 governed province reporting areas
```

## Complete PR description

```markdown
## Summary

Implements approved D-55 Option B reporting areas: official PSGC provinces,
independent cities without a PSGC province parent, NCR, and Unknown. Region
remains the parent and backward-compatible reconciliation geography.

## Changes

- adds governed Silver reporting-area reference and selected boundaries
- adds accepted-primary Table C reporting-area population
- adds one-row-per-project mapping with approved precedence and one spatial join
- adds Gold reporting-area dimensions and population fact
- adds `reporting_area_key` and mapping states to `fact_project_snapshot`
- adds five current-snapshot reporting-area Analytics views
- adds Silver, Gold, and Analytics validation that persists evidence before STOP
- updates tests, model docs, execution order, and reviewer handoff

## Safety and reconciliation

- raw DPWH province text is evidence only
- no fuzzy, substring, nearest-boundary, first-candidate, or proportional rule
- longitude-first EPSG:4326 `ST_COVERS`
- unresolved and ambiguous projects remain under Unknown
- one final mapping row per canonical project
- project count and reported-budget totals reconcile in Silver, Gold, and Analytics
- population uses only positive `ACCEPTED_PRIMARY` barangay rows

## Local verification

- 503 Pytest tests passed
- Ruff check and format check passed
- SQLFluff passed
- Markdownlint passed with 0 errors
- offline local link validation passed
- Vale exited 0 with style warnings and suggestions only
- `git diff --check` passed

## Databricks status

Not run. This PR prepares the production notebooks but does not claim runtime
approval. Run the documented order and attach persisted validation evidence,
coverage, selected versions, and exact-rerun identities.

## Deferred

Province flood exposure is deferred until a separate Databricks feasibility run
proves the reporting-area boundary and MGB intersection is safe and affordable.
No regional exposure is allocated to provinces.

## Reviewer focus

1. D-55 reporting-area membership and parent regions
2. config gates and matching precedence
3. one-project and reported-budget reconciliation
4. accepted-primary population rollup
5. Gold migration and Unknown behavior
6. Analytics denominators and excluded-area disclosure
7. validation evidence persistence before STOP gates
```

## Reviewer handoff

Review D-55 semantics first, then the Silver map and its validator, then Gold and
Analytics reconciliation. Local CI proves static contracts only. The merge
should not be described as runtime-approved until Databricks evidence passes.
