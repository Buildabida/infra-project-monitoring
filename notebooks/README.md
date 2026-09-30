# Notebooks

Our Databricks notebooks, one folder per step. Run the folders in this order. Each folder writes to the schema with the same number.

| Order | Folder | Writes to | What it does |
| --- | --- | --- | --- |
| 0 | `00_setup` | `00-source` | Makes the catalog, the schemas and the landing volume, and checks our sources |
| 1 | `01_bronze` | `01-bronze` | Loads each source as it came |
| 2 | `02_silver` | `02-silver` | Fixes types, removes duplicates and adds PSGC codes |
| 3 | `03_gold` | `03-gold` | Builds the facts and dimensions for the dashboard and Genie |
| 4 | `04_validation` | `04-validation` | Runs the checks and saves the results |

We add each folder with its first notebook. Try new ideas in a scratch file first. Only finished notebooks go here.

`run_all.py` runs the setup, the bronze loads and the bronze checks, in that order. The checks run only if every required load finished.

## Bronze notebooks

Each notebook loads one source as it came. Bronze keeps every field and value of the source. It doesn't rename, change types, clean, drop repeats or join anything. Silver does that. Each source keeps its own tables, and silver joins them. That is decision [D-22](../docs/decisions.md).

- **Raw copy first.** An API load saves each reply exactly as it came. Each run gets a new landing folder, like `dpwh_projects/20260930T141503123456+0800`. Then it reads only the files of its own run, so an old page can never slip in. The files we download by hand stay where we upload them.
- **Where each row came from.** Every bronze table has `_ingest_run_id` and `load_ts`. The API tables also have `_raw_file` and `_source_url`. The Excel tables have `source_file`, `sheet_name` and `source_row_number`.
- **Parsing adds, it never replaces.** Some loads turn text into a number or a code. They keep the cell as PSA wrote it in a `_raw` column, and put the result in a `_parsed` column next to it.
- **Every Excel row is counted.** An Excel load also saves a sheet manifest and a parse issues table. The manifest counts the title and header rows, blank rows, notes, data rows and rows the load could not read. These counts must add up to the rows in each sheet. If a row can't be read, the load stops before it replaces its main table.
- **A log row for every table.** Each load adds a row to `01-bronze.load_log`. It has the run ID, the rows the source reports and the rows we loaded. It also lists the raw files with their sizes and SHA-256 fingerprints. The checks compare the counts.

| Notebook | Source | Tables |
| --- | --- | --- |
| `01_bronze_dpwh_projects` | DPWH projects API by BetterGov.ph | `dpwh_projects` |
| `02_bronze_flood_control` | DPWH flood control map layer | `flood_control_projects` |
| `03_bronze_psgc` | PSA PSGC 2Q 2026 datafile | `psgc` and `population_2024`, plus `psgc_sheet_manifest` and `psgc_parse_issues` |
| `04_bronze_census_2024` | PSA 2024 census, Table B. Optional, for growth. | `census_2024_table_b`, plus its manifest and parse issues |
| `05_bronze_boundaries` | Boundary maps with PSGC codes, 7 files | `boundaries` |
| `06_bronze_census_table_c` | PSA 2024 census, Table C, 18 region files. Our population source ([D-18](../docs/decisions.md)). | `census_2024_table_c`, plus its manifest and parse issues |

The checks for every bronze table live in one notebook, `04_validation/01_validation_bronze`. [Data quality checks](../docs/validation.md#bronze-checks) says how they work.

## Load bronze

1. PSA blocks Databricks, so download the PSGC file, census Table B and the 18 census Table C files by hand. The steps are at the top of `03_bronze_psgc`, `04_bronze_census_2024` and `06_bronze_census_table_c`.
2. Upload the files to the `00-source.landing` volume. The PSGC file and Table B go in the `psa` folder. The 18 Table C files go in `population/table_c`. If a folder isn't there yet, make it.
3. Run `run_all.py` the way you run any notebook. It takes about 15 minutes.
4. Check the table at the end. Every required load must say `done` before the checks run. Table B is optional and may say `SKIPPED`. If the PSGC or Table C load says `SKIPPED`, the checks don't run and say `BLOCKED`.

Every load is safe to run twice. An API load saves its replies in a new folder for each run. It replaces its bronze table only after it has read the whole source. So a second run keeps both raw copies and never mixes their pages. Each run adds one more row per table to `load_log`.

## Run a notebook

In VS Code, open the file, click the **Run on Databricks** icon at the top right, then **Run File as Workflow**. The run happens on our team workspace, and the results open in a tab. The setup steps are in [set up VS Code](../docs/vscode-setup.md).

## Pick a language

- **SQL** for setup, the check rules, silver and gold. Most of us know SQL best, and Spark runs SQL and Python on the same engine, so neither one is faster.
- **Python** for loading APIs and Excel files, and for the small notebook that runs the SQL checks and saves their results. Keep that code short, and put helpers in the `src` folder.

This is decision [D-08](../docs/decisions.md).

## Start each notebook the same way

In a SQL notebook, the first line picks our catalog. Our catalog and schema names have hyphens, so put backticks around them. Then name each table as `` `schema`.table ``, like `` `02-silver`.projects ``:

```sql
USE CATALOG `buildabida-capstone`
```

In a Python notebook, import our names and links from [`src/config.py`](../src/config.py):

```python
from src import api, config
```

Put these lines in the first cell, so the import works from VS Code and from a Git folder. They put the repo root first on the path, so Python finds our `src` folder before any other:

```python
import os
import sys

repo_root = os.path.abspath("../..")
sys.path.insert(0, repo_root)
```

Don't copy a link into a notebook. Change it in `config.py`, and every notebook gets the change.

## Notebook names

Use `NN_layer_source`, like `01_bronze_dpwh_projects` or `02_silver_psgc`. The number sets the run order in a folder.

## Each notebook should

1. Say at the top what it makes.
2. Use our `buildabida-capstone` catalog.
3. Be safe to run twice. A second run doesn't mix raw files or add duplicate rows.
4. End with a quick look. The checks that count live in `04_validation/01_validation_bronze`.
5. Say in a comment if AI helped write it, and what you checked.

## Code checks

Every pull request runs our checks. SQLFluff checks our SQL, Ruff checks our Python, and pytest runs the tests in `tests`. If one finds a problem, the pull request shows a red X and the line to fix. The [style guide](../docs/style-guide.md#checks-that-run-for-you) lists every check.
