# Notebooks

Our Databricks notebooks, one folder per step. Run the folders in this order. Each folder writes to the schema with the same number.

| Order | Folder | Writes to | What it does |
| --- | --- | --- | --- |
| 0 | `00_setup` | `00-source` | Makes the catalog, the schemas and the landing volume, and checks our sources |
| 1 | `01_bronze` | `01-bronze` | Loads each source as it came |
| 2 | `02_silver` | `02-silver` | Fixes types, removes duplicates and adds PSGC codes |
| 3 | `03_gold` | `03-gold` | Builds the facts and dimensions for the dashboard and Genie |
| 4 | `04_validation` | `04-validation` | Runs the checks and saves the results |

We add each folder with its first notebook. Try new ideas in your own workspace folder first. Only finished notebooks go here.

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

This works because Databricks adds the repo folder to the Python path. Don't copy a link into a notebook. Change it in `config.py`, and every notebook gets the change.

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
