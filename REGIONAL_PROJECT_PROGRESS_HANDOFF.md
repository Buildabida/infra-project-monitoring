# Regional project progress handoff

## Recommendation

Keep the existing `analytics_project_delivery_status` view. It already supports
the latest FINISHED, ACTIVE, INACTIVE, and unmapped status mix by region.

Add `analytics_region_project_progress` for the different question, "What
changed since the previous DPWH snapshot?" The two views are complementary.
Infrastructure year cannot answer that question because it is a project cohort
attribute in the current snapshot.

This package does not create or modify an offline dashboard. After the proposed
contract is approved and validated in Databricks, the live dashboard can use the
Analytics view as its governed regional map dataset.

## Contract

The new view has one row per current official PSGC region. It reports:

- current project count and status mix
- current reported budget
- the immediately preceding source snapshot, when available
- project and reported-budget changes
- projects whose status changed
- projects that moved to FINISHED
- projects whose valid physical progress increased or decreased
- new and no-longer-present projects
- projects whose official region changed.

`ACTIVE` includes `For Procurement`. It must not be presented as proof that
physical construction is under way. A lower reported progress value remains a
review flag because the later source may correct an earlier value.

## One-snapshot behavior

A fresh Databricks account normally has one Gold DPWH snapshot. That is enough
for the current status map. It is not enough to calculate change.

With one snapshot:

- `comparison_status` is `NO_PRIOR_SNAPSHOT`
- current status measures are populated
- every previous or change measure is `NULL`, never zero.

To show real change, process a second, distinct DPWH source snapshot through
Bronze, Silver, Gold, and their validators. Force-reloading the same snapshot
does not create historical evidence because its source snapshot ID is unchanged.

## Databricks run order

After the normal pipeline has produced and validated Gold, run:

1. `notebooks/05_analytics/01_business_questions.ipynb`
2. `notebooks/04_validation/10_validation_analytics.ipynb`
3. `notebooks/05_analytics/02_regional_project_progress.ipynb`
4. `notebooks/04_validation/11_validation_regional_project_progress.ipynb`

The last validator persists 12 STOP checks and 2 FLAG checks to
`04-validation.analytics_dq_results` before its final STOP gate.

## Governance

D-55 is drafted under `Proposed decisions awaiting team approval`. It is not
recorded as approved. Obtain explicit team approval before merging the new
historical Analytics contract.

## Files added

- `notebooks/05_analytics/02_regional_project_progress.ipynb`
- `notebooks/04_validation/11_validation_regional_project_progress.ipynb`
- `tests/test_regional_project_progress.py`
- `docs/evidence/regional-project-progress/README.md`
- `docs/evidence/regional-project-progress/validation-results-2026-10-15.csv`
- `REGIONAL_PROJECT_PROGRESS_PR_DESCRIPTION.md`
- `REGIONAL_PROJECT_PROGRESS_HANDOFF.md`

## Files updated

- `docs/decisions.md`
- `docs/data-model.md`
- `docs/validation.md`
- `notebooks/README.md`
- `notebooks/05_analytics/README.md`

## Local verification

- `pytest`: 490 passed
- Ruff 0.16.9 check: passed
- Ruff 0.16.9 format check: passed
- SQLFluff 4.3.0: passed
- Markdown lint: passed
- Offline link check: passed
- Vale: zero errors
- `git diff --check`: passed

## Databricks evidence

The four notebooks ran in the documented order on October 15, 2026. The base
Analytics validator saved 152 checks with 138 `PASS`, 14 `FLAG`, and no blocking
failure. All 12 regional progress STOP checks passed. One expected FLAG records
that no prior snapshot is available.

The view returned all 18 official regions. Its 265,108 mapped projects and
PHP 6,378,351,772,243.23 mapped reported budget reconciled exactly to current
Gold. Current status measures are ready to use. Historical measures remain
`NULL` until a second distinct DPWH snapshot reaches Gold.

See the
[dated evidence](docs/evidence/regional-project-progress/README.md).
