# Dashboard CI fix

This package contains the two repository files needed for PR #142.

## Included files

- `databricks.yml`
  - Uses published dashboard ID `01f1cd53d40c10a59b3c05f0548efcb2`.
- `dashboard/buildabida_infrastructure_project_monitoring.lvdash.json`
  - Contains the real JSON export, not a macOS Finder bookmark.
  - Preserves the new dashboard pages and layout.
  - Reads the governed `05-analytics` views and approved Gold boundary tables.
  - Uses plain-text punctuation required by the repository contract.

## Apply to the branch

Extract the ZIP at the repository root and replace the existing files while
preserving the paths above. Then commit and push the replacements to
`fix/published-dashboard-id`.

Suggested commit title:

```text
fix(dashboard): commit the governed dashboard export
```

## Verification

The complete Python CI test suite was run with Python 3.12 and pytest 9.1.1:

```text
526 passed, 18 skipped
```

The published dashboard URL is:

https://dbc-7c256bfa-3ccc.cloud.databricks.com/dashboardsv3/01f1cd53d40c10a59b3c05f0548efcb2/published?o=7474644873778966

After the PR is merged, run the production deployment workflow. When the
deployment succeeds, repair the failed `business_dashboard` task.
