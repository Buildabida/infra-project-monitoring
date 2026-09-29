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

`run_all.py` runs the setup, every bronze load and the bronze checks, in that order.

## Bronze notebooks

Each notebook loads one source as it came, plus the load time. Each source keeps its own tables, and silver joins them. That is decision [D-22](../docs/decisions.md). A load saves the raw pages or files in the landing volume first. Then it adds a row to `01-bronze.load_log` with the number of rows the source reports and the number we loaded. The checks compare the two.

| Notebook | Source | Table |
| --- | --- | --- |
| `01_bronze_dpwh_projects` | DPWH projects API by BetterGov.ph | `dpwh_projects` |
| `02_bronze_flood_control` | DPWH flood control map layer | `flood_control_projects` |
| `03_bronze_psgc` | PSA PSGC 2Q 2026 datafile | `psgc` and `population_2024` |
| `04_bronze_census_2024` | PSA 2024 census, Table B. Optional, for growth. | `census_2024_table_b` |
| `05_bronze_boundaries` | Boundary maps with PSGC codes, 7 files | `boundaries` |
| `06_bronze_census_table_c` | PSA 2024 census, Table C, 18 region files. Our population source ([D-18](../docs/decisions.md)). | `census_2024_table_c` |

The checks for every bronze table live in one notebook, `04_validation/01_validation_bronze`. [Data quality checks](../docs/validation.md#bronze-checks) says how they work.

## Load bronze

1. PSA blocks Databricks, so download the PSGC file, census Table B and the 18 census Table C files by hand. The steps are at the top of `03_bronze_psgc`, `04_bronze_census_2024` and `06_bronze_census_table_c`.
2. In the `00-source.landing` volume, upload the PSGC file and Table B to the `psa` folder, and the 18 Table C files to a folder whose name starts with `population`, like `population/table_c`. If a folder isn't there yet, make it.
3. Run `run_all.py` the way you run any notebook. It takes about 15 minutes.
4. Check the table at the end. Each step should say `done`. If a PSA file is missing, its step says `SKIPPED`, and the rest still run.

Every load is safe to run twice. A second run replaces the table, and `load_log` gets one more row. The raw pages from each day stay in the landing volume.

## Run a notebook

In VS Code, open the file, click the **Run on Databricks** icon at the top right, then **Run File as Workflow**. The run happens on our team workspace, and the results open in a tab. The setup steps are in [set up VS Code](../docs/vscode-setup.md).

## Pick a language

- **SQL** for setup, silver, gold and validation. Most of us know SQL best, and Spark runs SQL and Python on the same engine, so neither one is faster.
- **Python** only where SQL can't do the job, like calling an API, reading a web page or reading an Excel file. Keep that code short, and put helpers in the `src` folder.

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

Put these two lines in the first cell, so the import works from VS Code and from a Git folder:

```python
import sys

sys.path.append("../..")
```

Don't copy a link into a notebook. Change it in `config.py`, and every notebook gets the change.

## Notebook names

Use `NN_layer_source`, like `01_bronze_dpwh_projects` or `02_silver_psgc`. The number sets the run order in a folder.

## Each notebook should

1. Say at the top what it makes.
2. Use our `buildabida-capstone` catalog.
3. Be safe to run twice. A second run with the same input adds no duplicate rows.
4. End with its data quality checks.
5. Say in a comment if AI helped write it, and what you checked.

## Code checks

Every pull request runs our checks. SQLFluff checks our SQL, and Ruff checks our Python. If one finds a problem, the pull request shows a red X and the line to fix. The [style guide](../docs/style-guide.md#checks-that-run-for-you) lists every check.
