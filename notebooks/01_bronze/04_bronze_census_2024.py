# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: 2024 census, Table B
# MAGIC
# MAGIC Loads PSA's 2024 census Table B into `01-bronze`.`census_2024_table_b`. It has the population of every region, province, city and town in 2010, 2015, 2020 and 2024, plus the growth rates. One row is one row of the table, in the order PSA wrote it.
# MAGIC
# MAGIC This table is optional. It adds the older counts and the growth rates, so we can see which places grow fast. Our 2024 population source is census Table C (D-18), and `01-bronze`.`population_2024` from the PSGC file is our cross-check. If the file is not there, the load says `SKIPPED`, and the other loads and the checks still run.
# MAGIC
# MAGIC It also saves `census_2024_table_b_sheet_manifest` and `census_2024_table_b_parse_issues`, like the other Excel loads. If a row can't be read, the load stops before it replaces the table.
# MAGIC
# MAGIC PSA blocks Databricks, so download the file by hand first:
# MAGIC
# MAGIC 1. Go to https://psa.gov.ph/content/2024-census-population-popcen-population-counts-declared-official-president and download **Table B - Population and PGR by Region, Province/HUC, and City/Municipality**.
# MAGIC 2. Upload it to the `psa` folder in `buildabida-capstone` > `00-source` > `landing`, next to the PSGC file. Keep the file name as PSA wrote it. The name is in `src/config.py`.
# MAGIC 3. Write the download date in the census source card.
# MAGIC
# MAGIC How PSA lays out each region sheet: column A has the place, columns C to F have the counts and columns G to J the growth rates. The first row under the header is the region. A blank row starts each province, then its cities and towns follow. `block` counts these groups, and `is_block_head` marks the first row of each one. Silver uses them to tell provinces from towns. Notes and sources at the end of a sheet are in column A.
# MAGIC
# MAGIC Bronze keeps the name and the numbers as PSA wrote them, in the `_raw` columns, with note marks like `CITY OF MAKATI 1`. Silver cleans the names and turns the numbers into numbers. It is safe to run twice.

# COMMAND ----------

import os
import sys

repo_root = os.path.abspath("../..")  # the repo root, so the import below works everywhere
sys.path.insert(0, repo_root)

from src import bronze, config, xlsx

load_run_id = bronze.new_run_id()
path = f"{config.PSA_FOLDER}/{config.TABLE_B_FILE}"
if not os.path.exists(path):
    dbutils.notebook.exit(f"SKIPPED: {path} is not there. Table B is optional. See the steps above.")
raw_files = [bronze.raw_file(path)]
source_file = os.path.basename(path)
print("Reading", path)

# COMMAND ----------


def header_end(rows):
    """Where the header ends. The header is the row with TOTAL POPULATION in column C and the row of census dates under it."""
    for position, (_, cells) in enumerate(rows):
        if xlsx.one_line((cells + [""] * 3)[2]) == "total population":
            below = rows[position + 1][1] + [""] if position + 1 < len(rows) else [""]
            return position + 1 if not below[0].strip() else position
    return None


def read_row(cells):
    """Table B's rule: a place in column A and at least one count in columns C to F. Column B is empty."""
    name, middle, counts = cells[0], cells[1], cells[2:6]
    has_count = any(xlsx.to_count(count) is not None for count in counts)
    if middle.strip():
        return "has text in column B, where Table B has none"
    if not name.strip():
        return "has no place in column A"
    if not has_count:
        return "has a place in column A but no count in columns C to F"
    return None


rows, manifest, issues = [], [], []
for sheet_name in xlsx.sheet_names(path):
    cells_by_row = xlsx.read_sheet(path, sheet_name)
    header = header_end(cells_by_row)
    if header is None:
        manifest.append(xlsx.skipped_sheet(source_file, sheet_name, cells_by_row, "no Table B header: column C does not say TOTAL POPULATION"))
        continue
    data, sheet_row, sheet_issues = xlsx.sort_sheet(source_file, sheet_name, cells_by_row, header, 10, read_row)
    manifest.append(sheet_row)
    issues.extend(sheet_issues)
    block, previous = 0, None
    for row_number, cells in data:
        if previous is None:
            kind = "region"
        elif row_number > previous + 1:
            block, kind = block + 1, "block_head"  # a gap in the row numbers means a new group
        else:
            kind = "row"
        previous = row_number
        name_raw, numbers_raw = cells[0], cells[2:10]  # counts in columns C to F, growth rates in G to J
        rows.append(
            (source_file, sheet_name, row_number, name_raw, *numbers_raw, block, kind == "block_head", kind == "region")
        )
print(f"Read {len(rows):,} rows from {len(manifest)} sheets. Parse issues: {len(issues):,}.")
bronze.save_parse_audit(spark, load_run_id, "2024 census Table B", "census_2024_table_b", manifest, issues, raw_files, config.CENSUS_PAGE)

# COMMAND ----------

columns = (
    "source_file string, sheet_name string, source_row_number int, name_raw string, "
    "pop_2010_raw string, pop_2015_raw string, pop_2020_raw string, pop_2024_raw string, "
    "pgr_2010_2015_raw string, pgr_2015_2020_raw string, pgr_2015_2024_raw string, pgr_2020_2024_raw string, "
    "block int, is_block_head boolean, is_region boolean"
)
census = spark.createDataFrame(rows, columns)
loaded = bronze.save_table(spark, census, "census_2024_table_b", load_run_id)
bronze.log_load(spark, load_run_id, "2024 census Table B", "census_2024_table_b", len(rows), loaded, raw_files, config.CENSUS_PAGE)
print(f"Loaded {loaded:,} rows.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick look
# MAGIC
# MAGIC The region rows should add up to 112,727,776. That is the national count of 112,729,484 without the 1,708 Filipinos in embassies abroad.

# COMMAND ----------

display(spark.sql("""
    SELECT sheet_name, name_raw, pop_2020_raw, pop_2024_raw, pgr_2020_2024_raw
    FROM `buildabida-capstone`.`01-bronze`.census_2024_table_b
    WHERE is_region
    ORDER BY TRY_CAST(pop_2024_raw AS DOUBLE) DESC
"""))
