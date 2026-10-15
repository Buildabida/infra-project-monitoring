# D-55 province reporting-area change manifest

## Scope

This package implements the approved Option B governed reporting-area model.
It contains every added or modified production file, with repository-relative
paths preserved. It contains no branch, commit, push, pull request, generated
dashboard asset, or Databricks runtime result.

`databricks.yml` is unchanged because the repository file defines bundle
identity and targets but no job DAG. The exact manual workflow order is in
`PROVINCE_REPORTING_PRODUCTION_HANDOFF.md` and `notebooks/README.md`.

## Added files

- `PROVINCE_REPORTING_CHANGE_MANIFEST.md`
- `PROVINCE_REPORTING_PRODUCTION_HANDOFF.md`
- `docs/province_reporting_readiness.md`
- `docs/silver_project_province_mapping.md`
- `notebooks/02_silver/01a_silver_province_reporting_area.ipynb`
- `notebooks/02_silver/03a_silver_province_reporting_area_population.ipynb`
- `notebooks/02_silver/08b_profile_project_province_readiness.ipynb`
- `notebooks/02_silver/08c_silver_project_province_map.ipynb`
- `notebooks/03_gold/01a_gold_dim_province_reporting_area.ipynb`
- `notebooks/03_gold/05a_gold_fact_province_reporting_area_population.ipynb`
- `notebooks/04_validation/03b_validation_silver_province_reporting.ipynb`
- `notebooks/04_validation/09a_validation_gold_province_reporting.ipynb`
- `notebooks/04_validation/10a_validation_provincial_analytics.ipynb`
- `notebooks/04_validation/11_publish_acceptance_evidence.sql`
- `tests/test_province_reporting_production.py`
- `tests/test_province_reporting_readiness.py`

## Modified files

- `README.md`
- `docs/README.md`
- `docs/data-model.md`
- `docs/decisions.md`
- `docs/gold_model.md`
- `docs/silver_config_mappings.md`
- `docs/silver_geography_population.md`
- `docs/silver_project_region_mapping.md`
- `docs/validation.md`
- `notebooks/03_gold/07_gold_fact_project_snapshot.ipynb`
- `notebooks/05_analytics/01_business_questions.ipynb`
- `notebooks/README.md`
- `tests/test_analytics.py`

## Deliberately unchanged

- `databricks.yml`: no job DAG exists to update.
- `dashboard/`: the request prohibits offline dashboard changes.
- Regional Silver, Gold, and Analytics outputs: retained for reconciliation and
  backward compatibility.
- Province flood exposure: deferred pending Databricks safety and cost evidence.

## Local verification

- Full Pytest suite: 503 passed.
- Ruff check: passed.
- Ruff format check: passed.
- SQLFluff over `notebooks`: passed.
- Markdownlint over all Markdown: 0 errors.
- Offline local Markdown-link validation: passed.
- Vale: exit 0, with style warnings and suggestions only.
- `git diff --check`: passed.
- Notebook JSON parsing: passed.

These are local checks. They are not Databricks runtime evidence.

## Package integrity

After ZIP creation, run:

```bash
unzip -t Buildabida_D55_Province_Reporting_Evidence_Ready.zip
shasum -a 256 Buildabida_D55_Province_Reporting_Evidence_Ready.zip
```

The delivery report records the resulting SHA-256 checksum.
