# Province reporting readiness handoff

## Outcome

This change adds a read-only Databricks SQL profiler for the provincial
reporting decision. It does not change a persisted table, approve a geography
rule, or claim runtime evidence.

## Files added

- `notebooks/02_silver/08b_profile_project_province_readiness.ipynb`
- `tests/test_province_reporting_readiness.py`
- `docs/province_reporting_readiness.md`
- `PROVINCE_REPORTING_READINESS_HANDOFF.md`

## Files modified

- `docs/decisions.md`
- `docs/README.md`
- `notebooks/README.md`

## Review focus

- The notebook creates temporary views only.
- Every canonical project remains exactly once in the final profile.
- The reported-budget total is asserted with NULL-safe equality.
- DPWH `location.province` is evidence only.
- Name matching is normalized exact equality only.
- Spatial matching uses `ST_COVERS` and longitude-first points.
- Zero and multiple candidates remain visible.
- D-34 remains approved. D-55 is proposed only.
- HUC versus independent-city classification is reported as unavailable rather
  than inferred.

## Suggested Git metadata

Branch:

```text
feature/province-reporting-readiness-profile
```

Commit title:

```text
Add provincial reporting readiness profile
```

Commit description:

```text
Add a read-only Databricks SQL profile for province-name and coordinate
candidates at canonical project grain. Preserve D-34, record D-55 as proposed,
and document the runtime evidence and human approval required before production
province reporting is built.
```

PR title:

```text
[SILVER] Profile provincial reporting readiness before model approval
```

## PR description

```markdown
## Summary

Adds a read-only provincial reporting readiness profile before any production
province model is approved. D-34 remains active. Proposed D-55 recommends a
governed province-reporting-area contract but stays in the proposed section.

## Changes

- adds a Databricks SQL notebook that profiles official-province name and
  coordinate candidates at one row per canonical project;
- reports project and budget coverage, conflicts, ambiguity, NCR, BARMM,
  boundary-version gaps, and the current HUC/ICC contract gap;
- asserts that project grain and reported-budget totals are unchanged;
- adds lightweight notebook contract tests and a governance/readiness document;
- updates the notebook guide and documentation index.

## Not included

- no production project-province map;
- no province dimension, fact key, population fact, flood-exposure fact, or
  Analytics view;
- no approved province aliases or manual exceptions;
- no Databricks runtime counts;
- no claim that provincial Analytics is ready.

## Testing

- `python -m pytest -q`
- `ruff check .`
- `ruff format --check --diff .`
- `sqlfluff lint notebooks --format github-annotation-native`
- Markdown lint
- offline link check
- Vale, if available
- `git diff --check`

## Runtime evidence required before approval

Run `08b_profile_project_province_readiness` in Databricks and attach all six
result sets listed in `docs/province_reporting_readiness.md`, including workflow
run ID, selected snapshots, project and budget reconciliation, conflicts,
ambiguity, NCR/BARMM results, and version gaps.

## Decision required

Approve either strict official provinces or governed province reporting areas.
Do not move D-55 into the approved decision table until the team reviews the
runtime evidence and explicitly approves the contract.

## AI assistance

AI assisted with SQL, tests, and documentation. A human owner must validate the
Databricks results, explain the mapping policy, and approve the decision.
```

## Reviewer handoff

Review this as a pre-decision evidence change, not as a complete province
implementation. The next implementation should start only after the team records
its grain decision and accepts the observed coverage limitations.
