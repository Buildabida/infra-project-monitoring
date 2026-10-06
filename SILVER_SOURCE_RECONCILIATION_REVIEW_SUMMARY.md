# Silver source reconciliation review summary

## Outcome

The current `main` baseline now contains the complete static implementation for
Silver Tables 11 and 12 plus their validation gate.

Implemented outputs:

- `02-silver.silver_flood_control_component`
- `02-silver.silver_project_source_match`
- source-reconciliation checks in `04-validation.silver_dq_results`

Requires Databricks execution.

## Baseline reviewed

The supplied repository archive identifies commit
`9b3e4e5dfd54463dd9476f9cb80313196a4ca717`. A read-only remote check confirmed
that the same commit was the `main` branch head before implementation began.

The review covered the current README files, decisions, data model, and validation
contracts. It also covered source configuration, Bronze evidence, existing Silver
Tables 1 through 10, and current tests.

## Source contract confirmed

The local flood-control source header was inspected. It contains:

- `object_id`
- `contract_id`
- `project_id`
- `project_component_id`
- `description`
- `infra_type`
- `type_of_work`
- `contract_cost`
- dates and coordinates
- source JSON and source-file lineage

The implementation therefore uses the real `object_id` for source-feature identity.
It does not invent a row number.

The local file supported schema verification only. Runtime claims remain tied to the
selected Bronze snapshot and require Databricks execution.

## Files changed

The complete added and modified file list is in
`SILVER_SOURCE_RECONCILIATION_CHANGE_MANIFEST.md`.

## Output grains

Table 11 has one row per selected Bronze flood-control source feature. Its identity
uses the real source `object_id`, selected snapshot, source system, and rule version.

Table 12 has one row per usable normalized flood-source Contract ID. Its grain also
includes the source snapshot, source version, component run, target run, and match rule.

## Design review

The implementation follows these boundaries:

- DPWH remains authoritative for canonical projects and reported investment.
- The flood-control list provides official source-component and membership evidence.
- Table 11 preserves every selected flood source feature and repeated Contract IDs.
- Table 12 uses exact `UPPER(TRIM(contract_id))` matching only.
- Punctuation remains meaningful and is not stripped.
- Invalid source IDs remain visible in Table 11 and in validation accounting.
- Unmatched and ambiguous targets remain visible.
- Conflicting source costs do not produce a resolved value.
- Flood Contract Cost is not added to DPWH reported budget.
- `silver_project` is read but never modified.
- D-04 remains open.

## Validation review

The new validator covers all seven project data-quality attributes:

- Consistency
- Accuracy
- Completeness
- Auditability
- Validity
- Uniqueness
- Timeliness

It writes evidence before enforcing the blocking gate. STOP checks protect row
accounting, grain, exact-match correctness, cost-resolution safety, and lineage.
FLAGS retain expected source limitations for review.

## Measured and unresolved findings

Existing accepted Bronze evidence records 157 repeated Contract-ID rows in its selected
9,861-row flood snapshot. That evidence is diagnostic and is not hardcoded as a future
invariant.

This package did not execute Databricks. Current Silver repeated-ID groups, cost
conflicts, exact-match coverage, unmatched groups, ambiguous targets, and PASS, FLAG,
or FAIL totals are not claimed.

The validator will report those findings with component-level and Contract-ID-level
denominators. D-04 remains open after the run because match evidence alone does not
authorize a final source-combination rule.

## Lineage

Table 11 retains flood source system, file, path, snapshot, version, ingest run, and
load timestamp. Table 12 retains the source component run and the matched project
snapshot, ingest run, rule version, and project run when a unique target exists.

## Scope intentionally excluded

This milestone does not implement:

- PSGC or Census processing
- boundary or MGB processing
- spatial functions
- project-region or project-flood mapping
- Tables 13 through 15
- Gold facts or dimensions
- dashboard or Genie logic
- a final D-04 source-combination business rule

## Runtime handoff

Use this order in Databricks:

1. Existing CONFIG and CONFIG validation
2. Accepted geography and population milestone, without rerunning unless required
3. `notebooks/02_silver/04_silver_dpwh_project_component.ipynb`
4. `notebooks/02_silver/05_silver_project.ipynb`
5. `notebooks/04_validation/04_validation_silver_projects.ipynb`
6. `notebooks/02_silver/06_silver_flood_control_component.ipynb`
7. `notebooks/02_silver/07_silver_project_source_match.ipynb`
8. `notebooks/04_validation/05_validation_silver_source_reconciliation.ipynb`

Review every FLAG and store the executed evidence before downstream promotion.
