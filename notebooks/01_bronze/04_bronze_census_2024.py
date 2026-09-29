# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: 2024 census, Table B
# MAGIC
# MAGIC Loads PSA's 2024 census Table B into `01-bronze`.`census_2024_table_b`. It has the population of every region, province, city and town in 2010, 2015, 2020 and 2024, plus the growth rates. One row is one row of the table, in the order PSA wrote it.
# MAGIC
# MAGIC This table is optional. It adds the older counts and the growth rates, so we can see which places grow fast. Our 2024 population source is census Table C (D-18), and `01-bronze`.`population_2024` from the PSGC file is our cross-check.
# MAGIC
# MAGIC PSA blocks Databricks, so download the file by hand first:
# MAGIC
# MAGIC 1. Go to https://psa.gov.ph/content/2024-census-population-popcen-population-counts-declared-official-president and download **Table B - Population and PGR by Region, Province/HUC, and City/Municipality**.
# MAGIC 2. Upload it to the `psa` folder in `buildabida-capstone` > `00-source` > `landing`, next to the PSGC file.
# MAGIC 3. Write the download date in the census source card.
# MAGIC
# MAGIC How PSA lays out each region sheet: the first row is the region. A blank row starts each province, then its cities and towns follow. `block` counts these groups, and `is_block_head` marks the first row of each one. Silver uses them to tell provinces from towns.

# COMMAND ----------

import re
import sys

sys.path.append("../..")  # the repo root, so the import below works everywhere

from src import bronze, config, xlsx

path = bronze.find_file(config.PSA_FOLDER, config.CENSUS_TABLE_B_PATTERN)
if path is None:
    dbutils.notebook.exit(f"SKIPPED: no Table B file in {config.PSA_FOLDER}. Download it by hand first. See the steps above.")
print("Reading", path)

# COMMAND ----------

rows = []
for sheet in xlsx.sheet_names(path):
    block, previous = 0, None
    for row_number, cells in xlsx.read_sheet(path, sheet):
        name_raw = cells[0] if cells else ""
        numbers = [xlsx.to_number(c) for c in (cells + [""] * 10)[2:10]]  # columns C to J
        if not name_raw or numbers[3] is None:
            continue  # blank rows, titles, headers and notes have no 2024 count
        if previous is None:
            kind = "region"
        elif row_number > previous + 1:
            block, kind = block + 1, "block_head"  # a gap in the row numbers means a new group
        else:
            kind = "row"
        previous = row_number
        counts = [None if n is None else int(n) for n in numbers[:4]]
        rates = [None if n is None else float(n) for n in numbers[4:]]
        name = re.sub(r"\s+[0-9*]+$", "", name_raw.strip())  # drop footnote marks like " 1" or " *"
        rows.append(
            (sheet, row_number, name_raw, name, *counts, *rates, block, kind == "block_head", kind == "region", path)
        )
print(f"Read {len(rows):,} rows from {len(xlsx.sheet_names(path))} sheets.")

# COMMAND ----------

columns = (
    "sheet string, row_number int, name_raw string, name string, "
    "pop_2010 long, pop_2015 long, pop_2020 long, pop_2024 long, "
    "pgr_2010_2015 double, pgr_2015_2020 double, pgr_2015_2024 double, pgr_2020_2024 double, "
    "block int, is_block_head boolean, is_region boolean, source_file string"
)
census = spark.createDataFrame(rows, columns)
loaded = bronze.save_table(spark, census, "census_2024_table_b")
bronze.log_load(spark, "2024 census Table B", "census_2024_table_b", len(rows), loaded, path)
print(f"Loaded {loaded:,} rows.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick look
# MAGIC
# MAGIC The region rows should add up to 112,727,776. That is the national count of 112,729,484 without the 1,708 Filipinos in embassies abroad.

# COMMAND ----------

display(spark.sql("""
    SELECT sheet, name, pop_2020, pop_2024, pgr_2020_2024
    FROM `buildabida-capstone`.`01-bronze`.census_2024_table_b
    WHERE is_region
    ORDER BY pop_2024 DESC
"""))
