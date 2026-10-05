# Bronze R2 ingestion validation evidence

## Scope

This report records Databricks evidence for the six-source Bronze ingestion.
All sources come from the approved Cloudflare R2 volume.

The evidence covers:

- workspace setup
- source prechecks
- per-source snapshot loading
- idempotent reruns
- grouped data-quality validation
- corrective changes prompted by validation findings

The evidence was captured on October 4, 2026 in the `buildabida-capstone` Unity Catalog.
The exported validation result has run ID `732b92cd-496e-4386-94ce-befbb5f06bdf`.
Its timestamp is `2026-10-04T14:12:42.759Z`.
The equivalent Asia/Manila timestamp is `2026-10-04 22:12:42.759`.

## Outcome

- Workspace setup confirmed the five project schemas and existing `00-source.cloudflare-r2` volume.
- Source precheck returned `OK` for all six configured CSV artifacts.
- All six Bronze notebooks completed for their selected snapshots.
- Captured reruns returned `SKIPPED_IDEMPOTENT`.
  Each source retained its expected Bronze row count.
- Grouped validation exported 126 checks.
  Results were 105 `PASS`, 21 `FLAG`, zero `FAIL`, and zero `ERROR`.
- All 96 checks configured with blocking action `stop` passed.
- Validation flags remain visible for review.
  They do not remove, deduplicate, correct, or rewrite Bronze rows.

The complete machine-readable result is in
[`validation-results.csv`](validation-results.csv).

## Selected snapshots

| Bronze table | Rows | Snapshot ID | Rerun status | Validation |
| --- | ---: | --- | --- | --- |
| `dpwh_projects` | 265,661 | `metadata-6321c7aa6f2a14e12f4c` | `SKIPPED_IDEMPOTENT` | 17 PASS, 8 FLAG |
| `flood_control_projects` | 9,861 | `metadata-0d088311118dfd63d63a` | `SKIPPED_IDEMPOTENT` | 20 PASS, 2 FLAG |
| `psgc` | 43,768 | `metadata-9f97e93e082df80535d6` | `SKIPPED_IDEMPOTENT` | 18 PASS, 0 FLAG |
| `census_2024_table_c` | 43,750 | `metadata-afa2fa4c580930b7c10a` | `SKIPPED_IDEMPOTENT` | 17 PASS, 3 FLAG |
| `boundaries` | 43,760 | `metadata-50c107fb3be0785f3a48` | `SKIPPED_IDEMPOTENT` | 17 PASS, 1 FLAG |
| `flood_susceptibility` | 63,684 | `metadata-17bf5e65e1838a2f7be9` | `SKIPPED_IDEMPOTENT` | 16 PASS, 7 FLAG |
| **Total** | **470,484** | Six selected snapshots | Six safe skips | **105 PASS, 21 FLAG** |

For every table, the validation export confirms:

- at least one row exists
- exactly one selected snapshot is present
- required ingestion metadata is populated
- the current Bronze row count matches `load_log`
- the current Bronze snapshot matches `load_log`
- the latest audit status is `SUCCESS` or `SKIPPED_IDEMPOTENT`

## Corrective changes recorded during validation

### 1. DPWH reported-budget source contract

The initial source precheck stopped with:

```text
dpwh_projects /Volumes/buildabida-capstone/00-source/cloudflare-r2/buildabida/dpwh_projects.csv FAILED null - null Required source field groups are missing: reported budget (one of: budget, project_cost, projectCost)
```

The CSV header uses `reported_budget`.
The DPWH `required_column_groups` configuration accepted three other aliases.
Those aliases were `budget`, `project_cost`, and `projectCost`.
The configuration did not accept the actual header.

The configuration now includes `reported_budget` in the reported-budget aliases.
The precheck gate itself was not weakened.
It still rejects missing source contracts.
After the correction, all six artifacts returned `OK`.

### 2. Known source imperfections were separated from blocking safety checks

The grouped validator initially blocked three checks:

```text
dpwh_projects / source-grain key is unique (FAIL)
boundaries / source file and feature lineage is unique (FAIL)
flood_susceptibility / flood-area geometry is not null or empty (FAIL)
```

These checks changed from blocking action `stop` to review action `flag`.
The conditions remain measured and exported.
Only their pipeline action changed.
Bronze continues to preserve the source rows for downstream review.

| Source | Check | Finding | Share | Action |
| --- | --- | ---: | ---: | --- |
| `dpwh_projects` | Duplicate `contract_id` groups | 5 | 0.0019% of 265,661 rows | `stop` to `flag` |
| `boundaries` | Duplicate source file and feature lineage | 232 | 0.53% of 43,760 rows | `stop` to `flag` |
| `flood_susceptibility` | Null or empty geometry | 1,815 | 2.85% of 63,684 rows | `stop` to `flag` |

The severity change does not classify the affected values as correct.
It keeps them visible for Silver handling.
Blocking failures remain reserved for unsafe or untraceable Bronze snapshots.

## Validation flags

The exported result contains the following non-blocking findings.

### DPWH projects

| Check | Finding |
| --- | ---: |
| Physical progress outside 0 to 100 | 17 rows |
| Missing project coordinate pair | 50,522 rows |
| Duplicate source-grain `contract_id` groups | 5 groups |
| Undocumented status category | 105 rows |
| `start_date` does not cast to `DATE` | 1 row |
| `completion_date` does not cast to `DATE` | 16 rows |
| `amount_paid` does not cast to `DECIMAL(38, 6)` | 6 rows |
| `progress` does not cast to `DOUBLE` | 5 rows |

### Flood-control projects

| Check | Finding |
| --- | ---: |
| Contract cost does not cast to a number | 2 rows |
| Repeated Contract IDs retained for Silver review | 157 rows |

### Census Table C

| Check | Finding |
| --- | ---: |
| Documented BARMM duplicate marker is unavailable | 1 check |
| Non-positive population when present | 12 rows |
| Difference from the 45,611-row historical reference | 1,861 rows |

The selected CSV contains 43,750 rows.
Bronze reports the historical-count difference without repairing it.

### Boundaries

| Check | Finding |
| --- | ---: |
| Duplicate source-file and feature lineage | 232 rows |

### MGB flood susceptibility

| Check | Finding |
| --- | ---: |
| Null or empty geometry | 1,815 rows |
| Values outside accepted text rating labels | 61,862 rows |
| High reference-count difference | 15,111 rows |
| Low reference-count difference | 17,092 rows |
| Moderate reference-count difference | 25,302 rows |
| Very-high reference-count difference | 6,156 rows |
| Missing-rating reference-count difference | 1,799 rows |

The five documented reference counts total 63,684.
This total exactly matches the selected MGB snapshot row count.

The validator also flags nearly all populated `flood_susceptibility_code` values against text labels.
This pattern shows that source values and validation labels use different representations.
Reconcile the code-to-label contract before describing the category-distribution checks as passing.
This is a validation-interpretation follow-up.
Bronze values must remain unchanged.

### PSGC

No validation flags were recorded.

## Design evidence

| Requirement | Evidence |
| --- | --- |
| Batch-based | Each notebook selects one bounded CSV snapshot and invokes the shared loader once. |
| Idempotent | All six captured reruns returned `SKIPPED_IDEMPOTENT` and retained their row counts. |
| Parameterized | Notebooks expose snapshot ID, source version, force reload, and optional source-path widgets. |
| Snapshot-aware | Every table contains one snapshot ID. Table metadata reconciles with `load_log`. |
| Raw-preserving | Source-quality findings remain as flags. Validation does not filter, correct, or deduplicate Bronze. |
| Low-cost | Source metadata and headers are checked before full reads. Validation metrics are grouped by source. |
| Resilient | Missing contracts and blocking safety failures stop the workflow with specific diagnostics. |
| Traceable | Rows carry ingestion metadata, snapshot IDs, run IDs, source metadata, and matching load-log evidence. |

## Evidence images

### Workspace setup

![Workspace schemas and R2-backed source volume](images/01-workspace-setup.png)

### Six-source precheck

![All configured source artifacts returned OK](images/02-source-precheck.png)

### DPWH projects Bronze notebook

![DPWH Bronze notebook and idempotent result](images/03-dpwh-projects.png)

### Flood-control projects Bronze notebook

![Flood-control Bronze notebook and idempotent result](images/04-flood-control-projects.png)

### PSGC Bronze notebook

![PSGC Bronze notebook and idempotent result](images/05-psgc.png)

### Census Table C Bronze notebook

![Census Table C Bronze notebook and idempotent result](images/06-census-table-c.png)

### Boundaries Bronze notebook

![Boundary Bronze notebook and idempotent result](images/07-boundaries.png)

### MGB flood susceptibility Bronze notebook

![MGB flood-susceptibility Bronze notebook and idempotent result](images/08-mgb-flood-susceptibility.png)

### Grouped Bronze validation

![Grouped six-source validation notebook](images/09-bronze-validation.png)

## Acceptance note

The evidence supports successful setup and six-source availability.
It also supports snapshot loading, table-to-audit reconciliation, and safe same-snapshot reruns.
Every blocking safety check passed.

Describe the result as **completed with non-blocking findings**.
Do not describe it as "all data-quality checks passed."

The MGB category-validation acceptance item remains open.
Reconcile coded susceptibility values with the documented text labels.
Then capture the updated validation output before closing that item.

## October 5, 2026 MGB validation follow-up

### Follow-up scope

This follow-up records the first Databricks run after adding the official MGB
code-to-label mapping. The October 4 evidence above remains unchanged as the
historical record of the earlier text-only comparison.

The updated validator maps codes only while evaluating checks:

| Source code | Validation label |
| --- | --- |
| `VHF` | `very high` |
| `HF` | `high` |
| `MF` | `moderate` |
| `LF` | `low` |

Bronze continues preserving the original source values.

### Run identity and outcome

- Validation run ID: `f530d193-5566-4bc4-abdb-3a88b65fa763`
- UTC timestamp: `2026-10-05T10:03:36.142Z`
- Asia/Manila timestamp: `2026-10-05 18:03:36.142`
- Checks exported: 126
- Results: 105 `PASS`, 21 `FLAG`, zero `FAIL`, and zero `ERROR`
- Blocking checks: all 96 checks with action `stop` passed

The rerun therefore passed the Bronze safety gate with non-blocking findings.
Store the complete machine-readable follow-up as
`validation-results-2026-10-05.csv` beside this report.

### MGB follow-up results

| Check | October 4 finding | October 5 finding |
| --- | ---: | ---: |
| Values outside the accepted rating labels | 61,862 rows | 16 rows |
| High reference-count difference | 15,111 rows | 869 rows |
| Low reference-count difference | 17,092 rows | 184 rows |
| Moderate reference-count difference | 25,302 rows | 455 rows |
| Very-high reference-count difference | 6,156 rows | 307 rows |
| Missing-rating reference-count difference | 1,799 rows | 1,799 rows |
| Null or empty geometry | 1,815 rows | 1,815 rows |

The decrease from 61,862 to 16 confirms that the validator now recognizes the
official MGB codes. It does not classify the remaining 16 values as valid.
Those values still require distinct-value profiling.

The distribution checks also remain review flags. The selected snapshot differs
from the documented category references, especially the missing-rating count.
These differences may reflect a newer extract or a source-quality issue.
They must not be repaired in Bronze.

### Follow-up acceptance status

The code-to-label representation mismatch is resolved.
The Bronze validation gate passes without a blocking result.

Keep the broader MGB category-distribution item open until the team:

1. profiles the 16 remaining values
2. confirms the actual blank-rating count
3. decides whether the documented reference counts describe another source version
4. records the conclusion for Silver handling
