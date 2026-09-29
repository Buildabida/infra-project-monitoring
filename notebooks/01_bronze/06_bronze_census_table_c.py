# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: 2024 census, Table C
# MAGIC
# MAGIC Loads PSA's 2024 census Table C into `01-bronze`.`census_2024_table_c`. It has the population of every province, city, town and barangay as of July 1, 2024. One row is one row of the table, as PSA wrote it. This is our population source (D-18). It is based on Nadine's first pass.
# MAGIC
# MAGIC PSA blocks Databricks, so download the files by hand first:
# MAGIC
# MAGIC 1. Go to https://psa.gov.ph/content/2024-census-population-popcen-population-counts-declared-official-president and download **Table C** for all 18 regions. Each region is one Excel file, like `NCR_2.xlsx`.
# MAGIC 2. In Databricks, open `buildabida-capstone` > `00-source` > `landing`. Upload the 18 files to a folder whose name starts with `population`, like `population/table_c`.
# MAGIC 3. Write the download date in the census source card.
# MAGIC
# MAGIC How PSA lays out the files: one sheet per province or big city. The first row of a sheet is the province or city. A blank row starts each city or town, then its barangays follow. `block` counts these groups. `is_sheet_head` marks the first row of a sheet, and `is_block_head` marks the first row of each group. The other rows are barangays.
# MAGIC
# MAGIC The BARMM file has 4 extra sheets named `Table C_...`. They copy the Lanao del Sur, Maguindanao del Norte, Maguindanao del Sur and SGA sheets in the same file. Bronze keeps them and marks them in `is_known_duplicate_sheet`, so silver can drop them.
# MAGIC
# MAGIC Place names stay as PSA wrote them, with their note marks, like `BASILAN *`. Silver cleans the names when it matches them to PSGC codes. It is safe to run twice.

# COMMAND ----------

import glob
import os
import sys

repo_root = os.path.abspath("../..")  # the repo root, so the import below works everywhere
sys.path.insert(0, repo_root)

from src import bronze, config, xlsx

paths = sorted(
    path
    for path in glob.glob(config.TABLE_C_FILES_GLOB, recursive=True)
    if not os.path.basename(path).startswith("~$")  # skip Excel's lock files
)
if not paths:
    dbutils.notebook.exit(f"SKIPPED: no Table C files match {config.TABLE_C_FILES_GLOB}. Download them by hand first. See the steps above.")
if len(paths) != config.TABLE_C_FILE_COUNT:
    raise RuntimeError(f"Expected {config.TABLE_C_FILE_COUNT} Table C files, but found {len(paths)}: {paths}")
print(f"Reading {len(paths)} files, like {paths[0]}")

# COMMAND ----------

rows, skipped = [], []
for path in paths:
    source_file = os.path.basename(path)
    for sheet in xlsx.sheet_names(path):
        cells_by_row = xlsx.read_sheet(path, sheet)
        top = " ".join(" ".join(cells[:4]) for _, cells in cells_by_row[:10]).casefold()
        if "total population" not in top or "barangay" not in top:
            skipped.append(f"{source_file} / {sheet}")
            continue  # not a Table C sheet, like the Table B sheet in the NCR file
        sheet_name = sheet.strip()
        block, previous = 0, None
        for row_number, cells in cells_by_row:
            cells = cells + [""] * 4
            place_name, population = cells[1], xlsx.to_number(cells[3])  # column B is the place, column D the count
            if not place_name or population is None:
                continue  # titles, headers, blank rows and notes have no count
            if previous is None:
                kind = "sheet_head"
            elif row_number > previous + 1:
                block, kind = block + 1, "block_head"  # a gap in the row numbers means a new city or town
            else:
                kind = "row"
            previous = row_number
            rows.append(
                (
                    source_file, sheet_name, row_number, place_name, int(population), block,
                    kind == "sheet_head", kind == "block_head", sheet_name in config.TABLE_C_DUPLICATE_SHEETS,
                )
            )
print(f"Read {len(rows):,} rows from {len(paths)} files. Skipped sheets: {skipped or 'none'}")

# COMMAND ----------

columns = (
    "source_file string, sheet_name string, source_row_number int, place_name string, population long, "
    "block int, is_sheet_head boolean, is_block_head boolean, is_known_duplicate_sheet boolean"
)
census = spark.createDataFrame(rows, columns)
loaded = bronze.save_table(spark, census, "census_2024_table_c")
bronze.log_load(spark, "2024 census Table C", "census_2024_table_c", len(rows), loaded, os.path.dirname(paths[0]))
print(f"Loaded {loaded:,} rows.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick look
# MAGIC
# MAGIC Without the 4 copied sheets, the files have 43,750 rows. Their barangays add up to 112,727,776, the country total without the 1,708 Filipinos in embassies abroad.

# COMMAND ----------

display(spark.sql("""
    SELECT
        source_file,
        COUNT(*) AS table_rows,
        COUNT_IF(NOT is_sheet_head AND NOT is_block_head) AS barangays,
        SUM(IF(NOT is_sheet_head AND NOT is_block_head, population, 0)) AS barangay_population
    FROM `buildabida-capstone`.`01-bronze`.census_2024_table_c
    WHERE NOT is_known_duplicate_sheet
    GROUP BY source_file
    ORDER BY source_file
"""))
