# D-57 province-reporting runtime evidence

> [!NOTE]
> This run was recorded under the branch decision ID D-55, now D-57, because `main` already used D-55.
> Its Silver and Gold results stay valid for the identities below. Its Analytics rows validated the five
> `analytics_reporting_area_*` views, which D-56 (proposed) retires. Province Analytics now lives in the six
> views and is validated by `10_validation_analytics`. Silver and Gold province validators moved to rule
> version v2 with added population and hierarchy checks, which have not run on Databricks yet.

## Scope

This evidence covers the governed province-reporting implementation for source
snapshot `metadata-6321c7aa6f2a14e12f4c`. It covers the Silver project map and
population outputs, Gold dimensions and facts, five Analytics views, and the
exact-rerun identity check. Province flood exposure remains out of scope.

The evidence was produced on Databricks Serverless on October 15, 2026. The
publisher is
[`11_publish_acceptance_evidence.sql`](../../../notebooks/04_validation/11_publish_acceptance_evidence.sql).

## Acceptance result

| Layer | Checks | PASS | FLAG | FAIL |
| --- | ---: | ---: | ---: | ---: |
| Silver | 15 | 10 | 5 | 0 |
| Gold | 16 | 16 | 0 | 0 |
| Analytics | 17 | 17 | 0 | 0 |
| **Total** | **48** | **43** | **5** | **0** |

Every blocking STOP check passed. The five Silver FLAG rows disclose real
coverage limitations rather than failed reconciliation.

| Identity | Value |
| --- | --- |
| Silver validation run | `3e34c6a3342aade636509b1d5dfb8515806e830c0711835a3b54ded9a1fdb8e3` |
| Gold validation run | `663f9f640e8db97af92c9b21d70dc391dd56617587aa1a12b551baac17898496` |
| Analytics validation run | `cff4e71eff37b2d2c1f801749d8b13b52fefd619959036b58e69b9ea7ed1fb2e` |
| Project-map run | `ce080c63fc23a761faa7b676c118ea944015fe85dd25d2e0efbc593d4f30f2a5` |
| Mapping checksum | `6037151126140483111` |

## Exact-rerun proof

The evidence publisher captured the project map before and after an unchanged
rerun of the mapping notebook and its Silver validator.

| Result | Value |
| --- | --- |
| Status | `PASS` |
| Compared captures | 2 |
| Distinct project-map run IDs | 1 |
| Distinct mapping checksums | 1 |
| Earlier capture | `2026-10-15T03:27:26.208Z` |
| Later capture | `2026-10-15T03:31:29.382Z` |

The unchanged run ID and checksum prove deterministic identity for the selected
source, PSGC, boundary, configuration, and rule versions.

## Project and budget coverage

| Metric | Value |
| --- | ---: |
| Total projects | 265,656 |
| Mapped projects | 200,110 |
| Unmapped projects | 65,546 |
| Mapped project percentage | 75.3267% |
| Total reported budget | PHP 6,535,616,688,962.02 |
| Mapped reported budget | PHP 5,469,683,356,440.04 |
| Unmapped reported budget | PHP 1,065,933,332,521.98 |
| Mapped budget percentage | 83.6904% |

Project grain, mapping-key uniqueness, lineage, and reported-budget
reconciliation all passed.

## Mapping outcomes

| Mapping outcome | Type | Projects | Projects with budget | Reported budget |
| --- | --- | ---: | ---: | ---: |
| Unique coordinate boundary | Province | 184,999 | 184,999 | PHP 5,066,961,026,542.05 |
| Unique coordinate boundary | NCR | 15,111 | 15,111 | PHP 402,722,329,897.99 |
| Unmapped | Unknown | 65,158 | 65,071 | PHP 905,637,334,942.18 |
| Non-geographic | Unknown | 306 | 306 | PHP 157,264,916,703.77 |
| Ambiguous | Unknown | 82 | 82 | PHP 3,031,080,876.03 |

There were no approved project aliases or manual exceptions in the selected
configuration. Their selected identities were
`NO_APPROVED_PROVINCE_ALIAS` and `NO_APPROVED_MANUAL_EXCEPTION`.

## Coverage flags

| Finding | Projects | Percentage |
| --- | ---: | ---: |
| Projects without usable coordinates | 50,518 | 19.0163% |
| Valid points with zero candidates | 14,723 | 5.5421% |
| Points with multiple candidates | 82 | 0.0309% |
| Unresolved reporting areas | 65,546 | 24.6733% |
| Name-coordinate conflicts | 0 | 0% |

These categories are not additive. Unresolved and ambiguous projects remain
under Unknown and continue to reconcile nationally.

## Governed special areas and boundaries

| Area | Projects | Reported budget |
| --- | ---: | ---: |
| NCR | 15,111 | PHP 402,722,329,897.99 |
| Independent city | 0 | Not available |
| BARMM | 1,793 | PHP 42,554,191,858.09 |

The dimension contains 102 members. Boundary status is 79 valid, 22 missing,
zero ambiguous, and zero invalid, plus the non-geographic Unknown status. All 18
independent-city members lack a compatible selected boundary. Negros
Occidental, Negros Oriental, Siquijor, and Sulu also lack one. Without approved
aliases, manual exceptions, or project PSGC evidence, the safe mapping rule
does not assign projects to independent-city areas.

## Population evidence

| Metric | Value |
| --- | ---: |
| Reference year | 2024 |
| Accepted-primary population | 112,348,732 |
| Unresolved accepted population | 214,703 |
| Excluded source population | 113,088,493 |
| Populated governed geographic areas | 101 |
| Missing-population geographic areas | 0 |
| Reporting-area population coverage | 100.0% |

Excluded population is disclosed but does not enter the fact. The accepted
population reconciles before and after reporting-area aggregation. Population
equity remains descriptive and is not evidence of fairness or unfairness.

## Versions

| Version | Value |
| --- | --- |
| Mapping rule | `silver-project-province-reporting-area-map-v1` |
| PSGC | `2Q 2026 as of 2026-06-30` |
| Boundary | `2023-11-06` |
| Alias | `NO_APPROVED_PROVINCE_ALIAS` |
| Manual exception | `NO_APPROVED_MANUAL_EXCEPTION` |

## Acceptance statement

D-57 is runtime-validated for the identities and source snapshot recorded here.
The result does not claim complete geographic coverage, authorize inferred
assignments, or approve province flood exposure. A changed source snapshot,
PSGC version, boundary version, configuration version, or rule version requires
new evidence.
