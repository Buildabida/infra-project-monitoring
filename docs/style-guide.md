# Style guide

Short rules for how we write and code. They come from the guides listed at the end.

## Write so anyone can follow

1. **One idea per sentence.** If a sentence needs a semicolon or a dash, split it in two.
2. **Say the main thing first.** Put what the reader needs most in the first line.
3. **Talk to the reader.** Use "you" and "we". Say who does what: "The notebook loads the table", not "The table is loaded".
4. **Use present tense.** Write "loads", not "will load".
5. **Use short, common words.** Say "start", not "commence". Explain a new term in one line the first time you use it.
6. **Number the steps.** Put one action in each step. Then say what the reader should see.
7. **Put the condition first.** Write "If the check fails, stop the run", not the other way around.
8. **Write headings in sentence case.** Start a task heading with a verb, like "Run the pipeline".
9. **Make links say where they go.** Never write "click here".
10. **Put code in code font.** File names, tables, columns and commands go in backticks, like `silver.projects`.
11. **Use tables for real data only.** Fill every cell. Write "None" if there's nothing.
12. **Keep each fact in one place.** Link to it instead of copying it.
13. **Update the docs in the same pull request as the code.**

Our house rules for writing: no em dashes, no semicolons, and a 7th grade reading level or lower. Code is fine with semicolons. To check the grade, paste your text into a free readability checker like [WebFX Read-Able](https://www.webfx.com/tools/read-able/).

## Pick SQL first

Use SQL for setup, silver, gold and validation. Most of us know SQL best, and Spark runs SQL and Python on the same engine, so neither one is faster. Use Python only where SQL can't do the job, like calling an API, reading a web page or reading an Excel file. This is decision [D-08](decisions.md).

## Write clear SQL

1. **Start with our catalog.** The first line of a SQL notebook is `USE CATALOG buildabida`. Then name each table as `schema.table`, like `silver.projects`.
2. **Write keywords and functions in capitals.** Names stay in snake_case, like `SELECT contract_id`.
3. **Put one column on each line,** with the comma at the end of the line.
4. **Use CTEs, not nested queries.** Give each CTE one job and a name that says it, like `projects_with_places`. End with `SELECT * FROM` the last CTE.
5. **Say the join type.** Write `INNER JOIN` or `LEFT JOIN`, never a plain `JOIN`. Don't use right joins.
6. **Name every alias with `AS`,** like `amount_paid AS paid`. When you join, put the table alias before each column.
7. **Use `UNION ALL`** unless you want to drop duplicate rows on purpose.
8. **Make it safe to run twice.** Use `CREATE OR REPLACE TABLE` to rebuild a table, or `MERGE INTO` to add only new rows.
9. **Use `TRY_CAST` for messy values,** so one bad value doesn't stop the run. Then count the new NULLs in your checks.
10. **Keep one row per key with `QUALIFY`.** Rank the rows with `ROW_NUMBER()`, and keep the rows where the rank is 1.
11. **Use `GROUP BY ALL`,** so you never leave out a column.
12. **Add a comment to every gold table and column.** Genie reads them, so clear comments give better answers.

Here's a short, clear silver table:

```sql
USE CATALOG buildabida;

CREATE OR REPLACE TABLE silver.projects
COMMENT 'One row per DPWH project'
AS
WITH latest AS (
    SELECT
        contract_id,
        TRY_CAST(budget AS DECIMAL(18, 2)) AS budget,
        TO_DATE(start_date) AS start_date,
        loaded_at
    FROM bronze.dpwh_projects
    QUALIFY ROW_NUMBER() OVER (PARTITION BY contract_id ORDER BY loaded_at DESC) = 1
)

SELECT * FROM latest;
```

### Let Databricks format your SQL

1. In Databricks, open your **Home** folder.
2. Click **Create**, then **File**, and name it `.dbsql-formatter-config.json`.
3. Paste the settings below, then refresh the page.

```json
{
  "keywordCasing": "uppercase",
  "functionNameCasing": "uppercase",
  "indentationWidth": 4,
  "commaPosition": "end"
}
```

Before you commit, click **Edit**, then **Format Notebook**. Your SQL now matches rules 2 and 3.

## Write short, clear Python

1. **Keep links and the catalog name in `buildabida/config.py`.** Python notebooks import them. Never copy a link into a notebook.
2. **Put helpers in the `buildabida` folder, not in notebooks.** Import them with `from buildabida import api, config`. Don't use `%run`.
3. **Give each step its own cell.** Only print or display what you need to check.
4. **Name columns in snake_case.** True or false columns start with `is_` or `has_`. DataFrame names end in `_df`.
5. **Build columns in one `select`.** Rename with `.alias()` instead of long `withColumn` chains.
6. **Keep chains short.** Wrap a chain of up to 5 steps in parentheses. Never end a line with a backslash.
7. **Always say how to join.** Write `how="left"` or `how="inner"`. Don't use right joins.
8. **Use built-in Spark functions.** Avoid Python UDFs. They're slower and harder to check.
9. **Name your numbers.** Put a number like a date cutoff in a named constant, with a comment that says why.
10. **Catch the error you expect.** Write `except requests.RequestException`, not `except Exception`.
11. **Write data quality rules as data.** Keep the rules in a list, and run them all in one place.

Here's a short, clear `select`:

```python
projects_df = raw_df.select(
    F.col("contractId").alias("contract_id"),
    F.col("budget").cast("decimal(18,2)").alias("budget"),
    F.to_date("startDate").alias("start_date"),
)
```

## Checks that run for you

Every pull request runs these checks. A red X means a check found a problem. Click **Details** to see where. The first four must pass before we merge.

| Check | What it looks at | How to fix it |
| --- | --- | --- |
| SQL (SQLFluff) | SQL notebooks | Fix the line it names. For capitals, use **Format Notebook**. |
| Python (Ruff) | Python code | Fix the line it names. |
| Markdown layout | The layout of Markdown files | Fix the line it names. |
| Links | Links between our files | Fix the path, or add the missing file. |
| Writing tips | Semicolons, dashes, long sentences and wordy phrases | Split or trim the sentence. These are tips, so they never block a merge. |

## Where these rules come from

- [Google developer documentation style guide](https://developers.google.com/style)
- [Microsoft Writing Style Guide](https://learn.microsoft.com/en-us/style-guide/welcome/)
- [Diátaxis](https://diataxis.fr/), for how we split our docs
- [Plain language guide](https://digital.gov/guides/plain-language/)
- [Write the Docs guide](https://www.writethedocs.org/guide/)
- [GitHub issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms), for our issue and pull request forms
- [NYC Mobility Pipeline](https://github.com/hyenalouise/nyc-mobility-pipeline), a class repo Bri shared, for issues that read like small plans and for how we work
- [dbt SQL style guide](https://docs.getdbt.com/best-practices/how-we-style/2-how-we-style-our-sql) and [SQLFluff](https://docs.sqlfluff.com/)
- [Databricks SQL formatting](https://docs.databricks.com/aws/en/sql/user/sql-editor/custom-format) and [Genie best practices](https://docs.databricks.com/aws/en/genie/best-practices)
- [Where PySpark and Spark SQL fit best](https://community.databricks.com/t5/technical-blog/where-pyspark-and-sparksql-fit-best-in-the-enterprise/ba-p/111021)
- [Palantir PySpark style guide](https://github.com/palantir/pyspark-style-guide)
- [Databricks notebook best practices](https://docs.databricks.com/aws/en/notebooks/best-practices)
- [Ruff](https://docs.astral.sh/ruff/)
