# Regional project progress validation evidence

> [!WARNING]
> **Retired evidence.** D-55 was withdrawn by D-56 (proposed) before team approval.
> `analytics_region_project_progress`, `02_regional_project_progress.ipynb`, and `11_validation_regional_project_progress.ipynb` are removed.
> Keep this report as history only. The current contract is in the [Analytics views guide](../../../notebooks/05_analytics/README.md).

## Scope

This report records the first Databricks execution of the proposed D-55
regional project progress view and validator. The run used one DPWH project
snapshot, so it proves the current regional status contract and the required
fail-safe behavior when no comparison snapshot exists. It does not prove
historical change calculations across two snapshots.

The evidence came from these executed Databricks notebook exports on October
15, 2026:

1. `05_analytics/01_business_questions`
2. `04_validation/10_validation_analytics`
3. `05_analytics/02_regional_project_progress`
4. `04_validation/11_validation_regional_project_progress`

The exported notebooks did not display the validation run ID or persisted run
timestamp, so this report does not invent either value.

## Run identity

| Item | Value |
| --- | --- |
| Rule version | `regional-project-progress-validation-v1` |
| DPWH snapshot ID | `metadata-6321c7aa6f2a14e12f4c` |
| Snapshot date key | `20261004` |
| Comparison status | `NO_PRIOR_SNAPSHOT` |
| Official region rows | 18 |

## Outcome

- The base Analytics v2 validator saved 152 checks. It reported 138 `PASS`, 14
  `FLAG`, and zero blocking failures.
- All 12 regional progress STOP checks passed.
- The expected no-prior-snapshot check produced one non-blocking `FLAG`.
- The progress-decrease review check passed with zero affected projects.
- The regional view returned all 18 official PSGC regions.
- The output contained 18 distinct region keys and 18 distinct PSGC region
  codes.
- Region key `0` did not enter the regional view.
- The 265,108 mapped projects reconciled exactly to current Gold.
- Mapped reported budget reconciled exactly at
  PHP 6,378,351,772,243.23.
- Current status counts and percentages reconciled.
- Current snapshot lineage reconciled.
- Every previous and change measure remained `NULL`. No unavailable history
  was published as zero.

The complete results from the regional validator are in
[`validation-results-2026-10-15.csv`](validation-results-2026-10-15.csv).

## Coverage note

The regional view intentionally excludes current projects whose Gold region key
is `0`. The base Analytics validation separately reported 474 such projects.
The regional progress validator reconciled the remaining 265,108 mapped
projects and did not drop a mapped project.

BARMM remained visible as an official region with
`NO_MAPPED_PROJECT_DATA`, zero mapped projects, and no reported budget value.
It was not interpreted as zero investment.

## Acceptance note

Describe this run as **completed with one expected non-blocking finding**.
Current regional status is runtime-validated. Historical project change is not
yet available because Gold contains only one distinct DPWH snapshot.

Process a later, distinct DPWH snapshot through the validated Bronze, Silver,
and Gold pipeline before presenting status changes, progress changes, new
projects, or no-longer-present projects. Force-reloading the same snapshot does
not create comparison history.

D-55 remains proposed and still requires explicit team approval before merge.
