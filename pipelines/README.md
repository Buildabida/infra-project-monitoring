# Pipelines

Our Databricks notebooks, one folder per step. Run the folders in this order.

| Order | Folder | What it does |
| --- | --- | --- |
| 0 | `00_setup` | Makes the catalog, schemas and landing volume, and checks our sources |
| 1 | `01_bronze` | Loads each source as it came into `bronze` |
| 2 | `02_silver` | Fixes types, removes duplicates and adds PSGC codes |
| 3 | `03_gold` | Builds the facts and dimensions for the dashboard and Genie |
| 4 | `04_validation` | Runs the checks and saves the results |

We add each folder with its first notebook.

## Pick a language

- **SQL** for setup, silver, gold and validation. Most of us know SQL best, and Spark runs SQL and Python on the same engine, so neither one is faster.
- **Python** only where SQL can't do the job, like calling an API, reading a web page or reading an Excel file. Keep that code short, and put helpers in the `buildabida` folder.

This is decision [D-08](../docs/decisions.md).

## Start each notebook the same way

In a SQL notebook, the first line picks our catalog. Then name each table as `schema.table`, like `silver.projects`:

```sql
USE CATALOG buildabida
```

In a Python notebook, import our names and links from [`buildabida/config.py`](../buildabida/config.py):

```python
from buildabida import api, config
```

This works because Databricks adds the repo folder to the Python path. Don't copy a link into a notebook. Change it in `config.py`, and every notebook gets the change.

## Notebook names

Use `NN_layer_source`, like `01_bronze_dpwh_projects` or `02_silver_psgc`. The number sets the run order in a folder.

## Each notebook should

1. Say at the top what it makes.
2. Use our `buildabida` catalog.
3. Be safe to run twice. A second run with the same input adds no duplicate rows.
4. End with its data quality checks.
5. Say in a comment if AI helped write it, and what you checked.

## Code checks

Every pull request runs our checks. SQLFluff checks our SQL, and Ruff checks our Python. If one finds a problem, the pull request shows a red X and the line to fix. The [style guide](../docs/style-guide.md#checks-that-run-for-you) lists every check.
