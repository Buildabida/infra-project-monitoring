# Silver source reconciliation

This milestone connects the official flood-control source to the canonical DPWH
project foundation without creating duplicate projects or unsupported investment
amounts.

It implements:

- `02-silver.silver_flood_control_component`
- `02-silver.silver_project_source_match`
- persisted validation in `04-validation.silver_dq_results`

Implemented and runtime-validated in Databricks for the current selected snapshots.

The notebooks must be rerun and revalidated when their upstream snapshots or
transformation rules change.

## Business purpose

The DPWH project source and the flood-control list may describe the same contract.
Reconciliation is required before downstream analytics so one official flood-list
record is not treated as another independent project.

DPWH remains authoritative for project identity and reported investment. The
flood-control list provides official membership and component evidence. Its Contract
Cost is never added to the DPWH project budget.

Reported investment means the DPWH project or contract budget. It does not mean
payment or government disbursement.

## Dependency order

Use this dependency order:

1. Run the existing CONFIG notebook and CONFIG validation.
2. Keep the accepted geography and population milestone. Do not rerun it unless its
   inputs changed.
3. Run `02_silver/04_silver_dpwh_project_component.ipynb`.
4. Run `02_silver/05_silver_project.ipynb`.
5. Run `04_validation/04_validation_silver_projects.ipynb`.
6. Run `02_silver/06_silver_flood_control_component.ipynb`.
7. Run `02_silver/07_silver_project_source_match.ipynb`.
8. Run `04_validation/05_validation_silver_source_reconciliation.ipynb`.

Do not continue after a blocking failure.

## Source roles

| Source | Role |
| --- | --- |
| `01-bronze.flood_control_projects` | Row-preserved official flood-list component evidence |
| `02-silver.silver_project` | Canonical DPWH project target and authoritative reported budget |
| `01-bronze.load_log` | Selected flood snapshot, version, and load evidence |
| `04-validation.dq_results` | Bronze acceptance gate |

No PSGC, Census, boundary, MGB, spatial, or Gold processing occurs in this
milestone.

## Flood-control component contract

### Component grain

One row is one selected Bronze flood-control source feature.

The source `object_id` becomes `source_feature_id`. It is not replaced by a generated
row number. The deterministic `flood_component_key` combines source system, selected
snapshot, source feature ID, and transformation-rule version.

### Preserved evidence

The table retains:

- raw and normalized Contract IDs
- source project and component IDs
- raw description, infrastructure type, and type of work
- reported location text and engineering office
- raw and parsed Contract Cost
- raw and parsed dates and coordinates
- source JSON evidence
- source system, path, file, snapshot, version, ingest run, and load timestamp
- deterministic Silver run and rule version

### Repeated Contract IDs

Repeated Contract IDs remain separate component rows. They may describe distinct
parts of one contract or source records from different funding periods. Table 11 does
not use `DISTINCT`, generic deduplication, or arbitrary row selection.

This follows D-19, which requires Bronze flood rows to remain preserved.

### Contract Cost

Contract Cost is parsed with `TRY_CAST` to `DECIMAL(20,2)`. Missing, unparseable, and
negative values receive explicit statuses while the raw source value remains.

Contract Cost is source evidence only. It is not summed into a DPWH project budget.

## Project source-match contract

### Match grain

One row is one usable normalized flood-source Contract ID. Its grain also includes
the selected source snapshot, source version, component run, target run, and rule.

Rows with a null or blank Contract ID remain in the component table. They do not form
a valid match-table key, so validation accounts for them separately.

### Contract-ID normalization

Automatic matching uses only:

```text
UPPER(TRIM(contract_id))
```

It does not remove punctuation, use descriptions, infer geography, or apply fuzzy
matching.

### Match method and statuses

The only automatic method is `EXACT_CONTRACT_ID`.

| Status | Meaning |
| --- | --- |
| `MATCHED_EXACT_CONTRACT_ID` | Exactly one canonical project has the same normalized Contract ID |
| `UNMATCHED` | No canonical project has the normalized Contract ID |
| `AMBIGUOUS_TARGET` | More than one target project candidate has the normalized Contract ID |

A matched project key and target lineage are published only when candidate count is
exactly one. Unmatched and ambiguous results remain visible. The pipeline never picks
an arbitrary target.

### Source component accounting

The match table records:

- source component count
- distinct raw Contract ID count and raw ID evidence
- valid source-cost count
- distinct valid source-cost count
- cost-resolution status

The validation accounting rule is:

```text
Silver flood-control component rows
= grouped components represented in source-match rows
+ component rows with invalid source Contract IDs
```

The expected difference is zero.

### Repeated-cost protection

One distinct valid cost may be retained as source evidence. Multiple distinct valid
costs produce `CONFLICT` and no resolved source cost. Repeated cost values are never
blindly summed.

This resolved source value still does not replace or augment the DPWH reported budget.

## Flood category and flood-list membership

A DPWH project classified into a flood-related category is not automatically proven to
appear in the official flood-control list. Conversely, official flood-list membership
is recorded from exact source reconciliation, not inferred from a project category.

Future Gold `dim_project` may use the accepted reconciliation evidence for fields such
as `is_in_official_flood_list`, `flood_list_match_status`, and
`flood_list_version`. Gold is not implemented by this milestone.

## Lineage and idempotency

The component output retains the selected Bronze snapshot, ingest run, source version,
and source-load timestamp. The source-match output retains both flood-component and
canonical-project lineage.

Business keys and run IDs use deterministic hashes of their documented inputs. Exact
reruns use `CREATE OR REPLACE TABLE` and produce the same logical identities. Random
UUIDs, streaming, cache, repartition, Python UDFs, and spatial functions are not used.

## Cost controls

The implementation keeps compute bounded by:

- reading only the flood-control Bronze table and compact audit evidence for Table 11
- reading only Table 11 and `silver_project` for Table 12
- grouping once by normalized source Contract ID
- grouping once by normalized target Contract ID
- avoiding spatial scans and unrelated large sources
- persisting compact validation evidence before the final gate

## Validation rules

### Stop conditions

Blocking checks protect:

- accepted and nonempty upstream inputs
- exact Bronze-to-component row preservation
- unique component and match keys
- one selected snapshot and deterministic run
- complete mandatory source and target lineage
- one match row for every usable normalized source Contract ID
- complete component-to-match accounting
- exact Contract ID assignment correctness
- protection against resolved values for conflicting source costs

### Review flags

Nonblocking findings report:

- invalid source Contract IDs
- repeated source Contract IDs
- unparseable or negative Contract Cost
- coordinate exceptions
- unmatched source Contract IDs
- ambiguous target candidates
- conflicting source costs
- optional source-version gaps when snapshot lineage still exists

Reviewable source limitations remain visible. They are not changed to fabricate a
passing result.

## Decision boundary

D-04 remains open. This milestone records exact Contract ID match evidence but does
not authorize a final business rule for combining overlapping source records.

## Current runtime validation

The current selected snapshots were executed successfully in Databricks.

Runtime results:

- 9,861 Bronze flood-control rows
- 9,861 Silver flood-control component rows
- 9,704 usable normalized Contract-ID groups
- 9,689 exact Contract-ID matches
- 15 unmatched Contract-ID groups
- 0 ambiguous target matches
- 109 repeated Contract-ID groups
- 76 source Contract Cost conflict groups
- 2 Contract Cost parse failures
- 10 coordinate exceptions
- 0 invalid source Contract IDs

The validator executed 22 checks:

- 16 PASS
- 6 non-blocking FLAG
- 0 FAIL
- all 12 blocking STOP checks passed

Exact Contract-ID match coverage is approximately 99.85% of usable source
Contract-ID groups for the current selected snapshots.

These figures describe the current runtime state and are not hardcoded future
expectations.

## Known limitations

- Only exact normalized Contract ID matching is implemented.
- Missing and inconsistent Contract IDs remain unresolved.
- The current selected snapshot has 15 unmatched Contract-ID groups.
- Publisher `source_version` is unavailable for the current flood-control snapshot,
  although snapshot and ingest-run lineage remain available.
- Match coverage must be recalculated whenever the flood-control or DPWH project
  snapshots change.
- No geography, spatial exposure, population, MGB, or Gold logic is included.

## Downstream dependencies

Future project dimensions and flood-list indicators may consume only accepted match
results after this validator passes. Project-region mapping, project-flood mapping,
Gold dimensions, Gold facts, dashboards, and Genie remain separate future work.
