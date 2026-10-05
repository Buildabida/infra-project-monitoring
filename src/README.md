# Shared Python modules

This directory contains active Bronze code and one retained legacy module.

## Current ingestion modules

- `config.py` defines the six approved source contracts and shared catalog paths.
- `bronze.py` implements the shared R2-to-Bronze ingestion mechanics.
- `api.py` contains the earlier API helper retained by the repository.
- `__init__.py` marks the directory as a Python package.

## Legacy workbook module

`xlsx.py` preserves the earlier PSGC and Census Table C workbook-inspection logic.
The current Bronze pipeline reads approved CSV snapshots from Cloudflare R2 and does
not import this module.

The workbook code remains under `src` because its reproducibility tests still run in
CI. If the team later creates a dedicated legacy package, move `xlsx.py` and
`tests/test_xlsx.py` together in one pull request. Do not mix that relocation with
Silver or Gold implementation work.
