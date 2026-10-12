# Analytics views validation evidence

## Scope

This report records Databricks evidence for the six analytics views from issue #126.
The views answer business questions Q1 to Q6 for the dashboard (#20) and Genie (#21).

The evidence covers:

- building the six views in `05-analytics`
- the Gold gate before validation
- 87 checks that rebuild each view from Gold and compare it row by row
- a rerun that updates the same evidence rows

The evidence was captured on October 12, 2026 in the `buildabida-capstone` Unity Catalog.
Both notebooks ran interactively on Databricks serverless, from the synced dev bundle.
The workflow run was cancelled after more than 10 minutes in the job queue.

## Run identity

| Item | Value |
| --- | --- |
| Validation run ID | `34f5763a05a741426ed6d8225cb248ab1b2ab896bff59a3ad7e97cd101d22844` |
| Views built | `2026-10-12T10:49Z` (`2026-10-12 18:49` Asia/Manila) |
| Evidence saved | `2026-10-12T10:52:31.916Z` (`2026-10-12 18:52:31` Asia/Manila) |
| DPWH snapshot ID | `metadata-6321c7aa6f2a14e12f4c` |
| MGB snapshot ID | `metadata-17bf5e65e1838a2f7be9` |
| Gold `fact_project_snapshot` run ID | `185190695a2153a9cd67c5055a5542993ef7280aadde3f77cf9cf4543b911ac4` |
| Gold `dim_region` run ID | `0e4a50bd17f0d38d46c35e1a6f636775e4c12e14c113b34147559209199f7f09` |
| Gold `fact_region_population` run ID | `3f729c6fbda8a4683895658e1577329b3f0497c9aec6a2232456ecc3e9754ecd` |
| Gold `fact_region_flood_exposure` run ID | `a7ba8dcd8bcdd96d343603e6fecf931a7d95bd14ce3d81f9ff55cf942a592863` |

The validation run ID is a hash of the four Gold run IDs and the rule version `analytics-validation-v1`.
The same Gold data always gives the same ID.

## Outcome

- `01_business_questions` created all six views.
- The Gold gate passed: the latest Gold validation had no failed STOP checks and covered the current population and exposure facts.
- `10_validation_analytics` saved 87 checks: 76 `PASS` and 11 `FLAG`, with zero `FAIL`.
- All 74 checks with action `stop` passed, and the STOP gate passed.
- Two checks with action `flag` found nothing, so they count as `PASS`.
- A second run of both notebooks gave the same row counts, results and totals.

The complete machine-readable result is in
[`validation-results-2026-10-12.csv`](validation-results-2026-10-12.csv).

## Views

| View | Question | Rows |
| --- | --- | ---: |
| `analytics_regional_investment` | Q1. Regional investment distribution | 18 |
| `analytics_category_portfolio` | Q2. Infrastructure category portfolio | 9 |
| `analytics_project_delivery_status` | Q3. Project delivery and status | 342 |
| `analytics_population_equity` | Q4. Population-based equity | 18 |
| `analytics_flood_control_exposure` | Q5. Flood control versus flood exposure | 18 |
| `analytics_region_category` | Q6. Investment by area and type | 123 |

## Totals

| Measure | Projects | Reported budget (₱) |
| --- | ---: | ---: |
| Regional views (Q1, Q3, Q6) | 265,084 | 6,378,351,772,243.23 |
| Region key `0` | 572 | 157,264,916,718.79 |
| **All current Gold projects (Q2)** | **265,656** | **6,535,616,688,962.02** |

Q1 plus key `0` equals every current Gold project and the full Gold budget.
No project has a region key missing from `dim_region`.

| View | Share total |
| --- | ---: |
| Q1 budget share | 100.0000 |
| Q2 budget share | 99.9999 |
| Q4 investment share | 100.0000 |
| Q4 population share | 99.9998 |
| Q4 comparable population share | 100.0000 |

Each total is within the rounding tolerance of 0.01.

## Validation flags

The flags keep known data limits visible. They do not change any view.

| View | Check | Finding |
| --- | --- | ---: |
| Q1 | Current projects left out on region key `0` (306 `NON_GEOGRAPHIC`, 266 `UNMATCHED`) | 572 projects |
| Q1 | Projects in the view with a reported budget of 0 | 19,379 projects |
| Q1 | Official regions with no or limited DPWH coverage (BARMM, not ranked) | 1 region |
| Q2 | Projects with no usable category (sector `NULL`, D-37), ₱48,050,146,057.75 | 20,496 projects |
| Q2 | Multi-sector projects counted whole in the broad flood share (D-39), ₱16,367,824,185.17 | 180 projects |
| Q3 | Projects with no mapped status group | 4 projects |
| Q3 | Projects without a long-running flag because they have no start date | 19,756 projects |
| Q4 | Regions left out of the equity comparison (BARMM) | 1 region |
| Q5 | Flood control projects not placed in an MGB level (6,636 outside every zone, 2,541 with no usable point) | 9,177 of 34,967 projects |
| Q5 | Regions whose flood levels overlap, so no total area | 10 regions |
| Q5 | Regions with no evaluated flood exposure | 5 regions |

These flags found nothing:

- Q1: projects in the view without a reported budget
- Q4: official regions without a primary population

## Rerun

Both notebooks ran a second time on the same Gold data.
The second run gave the same row counts, the same 87 results and the same totals.

`04-validation.analytics_dq_results` then held one validation run ID with 87 rows:

| `validation_run_id` | Checks | Last run |
| --- | ---: | --- |
| `34f5763a…2844` | 87 | `2026-10-12T10:52:31.916Z` |

The rerun updated the same rows through `MERGE`. It did not add copies.

## No placeholder text

No view writes `Unknown` or `Unmapped` in place of a missing sector or status (D-37).
A query of Q2, Q3 and Q6 after the rerun found 0 rows with either value in `standardized_sector` or `status_group`.
Every `NULL` sector or status keeps its reason in `infra_type_mapping_status` or `status_mapping_status`.

## Evidence images

### View row counts

![Row counts of the six analytics views](images/01-view-row-counts.png)

### Gold gate

![Gold gate ASSERT_TRUE returned null](images/02-gold-gate.png)

### Validation flags

![The 11 FLAG rows saved to analytics_dq_results](images/03-validation-flags.png)

### STOP gate

![Analytics STOP gate returned null](images/04-stop-gate.png)

### Evidence rows after the rerun

![One validation run ID with 87 rows](images/05-rerun-evidence-rows.png)

### No placeholder text

![Zero Unknown or Unmapped values in Q2, Q3 and Q6](images/06-no-unknown-text.png)

## Acceptance note

Every blocking check passed. Describe the result as **completed with non-blocking findings**.
Do not describe it as "all data-quality checks passed."

The run used Gold from before #125. Rerun both notebooks after #125 merges and add the result here.
