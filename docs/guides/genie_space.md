# Genie space setup

This guide sets up the Genie space for issue #21, so people can ask their own questions in plain words. It gives the approved sources, the instructions to paste, the test questions, and a log to fill in.

> [!IMPORTANT]
> The Genie space is **not set up or tested yet**. The test log below is empty on purpose. Fill it in only with answers you actually saw in Genie.

## Approved sources

Genie reads only the six Analytics views, the same as the dashboard ([D-56](../decisions.md), proposed). They read current Gold only, pass `10_validation_analytics`, and have a comment on every view and column, which Genie uses.

| View | Use it for |
| --- | --- |
| `analytics_investment_distribution` | Where reported budget goes, by region or province reporting area |
| `analytics_population_equity` | Budget share compared with population share, by province reporting area |
| `analytics_flood_alignment` | Flood-control projects compared with MGB flood levels, by region |
| `analytics_implementation_monitoring` | One project at a time: status, progress, dates, review indicators |
| `analytics_infrastructure_network` | One project at a time, with its map point and flood class |
| `analytics_integration_coverage` | How many projects connect to each source, and which don't |

Issue #21 was written before D-56 and says "up to five Gold tables". Pointing Genie at Gold tables would skip the Analytics checks and the view comments. So this guide uses the six views. Confirm this with the team, and update #21.

## Set up the space

1. Deploy and run the pipeline so the six views exist, and confirm the latest [quality gate](../../notebooks/06_data_quality/README.md) is `PASS` or `FLAG`.
2. In the team workspace, open **Genie** and create a new space named `Buildabida infrastructure monitoring`.
3. Pick the same SQL warehouse the dashboard uses.
4. Add the six views from `buildabida-capstone`.`05-analytics`. Add no other tables.
5. Paste the instructions below into the space's general instructions.
6. Add the six sample questions below.
7. Share the space with the team as **Can view** or **Can run**. Only Nadine edits it.
8. Run every test question, then fill in the test log.

## Instructions to paste

```text
You answer questions about Philippine public works projects from the DPWH projects data.

Budget
- "Budget" always means the reported project or contract budget. It is not money paid
  or disbursed. Never call it spending, payment, or disbursement.
- A missing budget is unknown, not zero. Never treat NULL as 0.

Geography
- There are two levels: official region, and province reporting area. A reporting area is
  an official province, an independent city with no province, or NCR as one area.
- Never add region and reporting-area numbers together, and never add reporting areas to
  get a region total. Use the REGION level for regions.
- In analytics_investment_distribution, filter geography_level to one value. Read
  geography_* columns with MAX, never SUM.
- Key 0 means Central Office, unmatched, or unresolved. Say so when it matters.
- BARMM has limited source coverage. Don't rank it or call it low investment.
- A zero for a place with source_coverage_status other than REPORTED is a data gap, not
  zero investment.

Time
- There is one DPWH snapshot. infra_year is a project cohort, not history. Say "projects
  in the 2018 infrastructure-year cohort", never "DPWH spent in 2018".

Flood
- A project with no flood level is not safe from floods. Most project points fall outside
  the approved MGB polygons, and many have no map point.

Integration
- In analytics_integration_coverage, every project appears once in every link. Never add
  rows across links.

General
- Say which view you used. If the data can't answer the question, say so instead of
  guessing. We have no overdue, stalled, fairness, or network-connectivity rule.
```

## Test questions

These are the six stories in the [README](../../README.md#why-we-built-it), plus two checks that Genie respects our limits.

| # | Question | View it should use | What a right answer does |
| --- | --- | --- | --- |
| 1 | Which five regions have the largest share of reported budget? | `analytics_investment_distribution` | Uses the `REGION` level, leaves out key `0`, and says "reported budget" |
| 2 | Which provinces get a bigger share of budget than their share of people? | `analytics_population_equity` | Compares the two shares and calls nothing "unfair" |
| 3 | How many flood-control projects are in high or very high flood areas? | `analytics_flood_alignment` | Uses the MGB levels and mentions projects with no level |
| 4 | Which projects have at least one review indicator? | `analytics_implementation_monitoring` | Counts by indicator and keeps key `0` projects |
| 5 | How many projects have a usable map point? | `analytics_infrastructure_network` | Counts once per project |
| 6 | What share of projects connects to a PSGC region? | `analytics_integration_coverage` | Uses the `PSGC_REGION` link only |
| 7 | How much did DPWH pay contractors in 2018? | none | Says the data has reported budget, not payments, and only cohorts |
| 8 | Which BARMM province gets the least money? | none | Says BARMM coverage is limited, and does not rank it |

Check each number against the dashboard tab for the same view, or a query on the view.

## Test log

| # | Date | Tester | Genie's answer | Matches the view? | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |
| 6 | | | | | |
| 7 | | | | | |
| 8 | | | | | |

Issue #21 is done when every row is filled in, every answer matches its view, the space is shared, and this log is in a pull request.
