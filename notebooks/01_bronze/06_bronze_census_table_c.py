# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: 2024 census, Table C
# MAGIC
# MAGIC Loads PSA's 2024 census Table C into `01-bronze`.`census_2024_table_c`. It has the population of every province, city, town and barangay as of July 1, 2024. One row is one row of the table, as PSA wrote it. This is our population source (D-18). It is based on Nadine's first pass.
# MAGIC
# MAGIC It also saves two tables that show how every row of every sheet was sorted:
# MAGIC
# MAGIC - `census_2024_table_c_sheet_manifest`: one row per sheet. It counts the title and header rows, blank rows, notes, place rows and rows we could not read. The counts must add up to the rows in the sheet. Sheets that are not Table C are listed with the reason.
# MAGIC - `census_2024_table_c_parse_issues`: every row we could not read, with its cells and the reason. If it has any rows, the load stops before it replaces `census_2024_table_c`.
# MAGIC
# MAGIC PSA blocks Databricks, so download the files by hand first:
# MAGIC
# MAGIC 1. Go to https://psa.gov.ph/content/2024-census-population-popcen-population-counts-declared-official-president and download **Table C** for all 18 regions. Each region is one Excel file, like `NCR_2.xlsx`.
# MAGIC 2. In Databricks, open `buildabida-capstone` > `00-source` > `landing`. Upload the 18 files to `population/table_c`. If a folder isn't there yet, make it.
# MAGIC 3. Write the download date in the census source card.
# MAGIC
# MAGIC How PSA lays out the files: one sheet per province or big city. Column B has the place and column D the count. The first row under the header is the province or city. A blank row starts each city or town, then its barangays follow. `block` counts these groups. `is_sheet_head` marks the first row of a sheet, and `is_block_head` marks the first row of each group. The other rows are barangays. Notes and sources at the end of a sheet are in column A.
# MAGIC
# MAGIC Bronze keeps the place and the count as PSA wrote them, in `place_name_raw` and `population_raw`, with any spaces and note marks, like `BASILAN *`. `population_parsed` is the count as a number. Sheet names also stay as PSA wrote them, and 7 of them end in a space. Silver cleans the names when it matches them to PSGC codes.
# MAGIC
# MAGIC The BARMM file has 4 extra sheets named `Table C_...`. They copy the Lanao del Sur, Maguindanao del Norte, Maguindanao del Sur and SGA sheets in the same file. Bronze keeps them and marks them in `is_known_duplicate_sheet`, so silver can drop them. These copies also have PSA's check cells to the right of column D. Only columns A to D are Table C, so bronze doesn't load those cells, and the raw files keep them.
# MAGIC
# MAGIC The load stops if the files change: we expect 45,611 rows, 1,861 of them in the copied sheets, 43,750 rows to use and 2 sheets that are not Table C. It is safe to run twice.

# COMMAND ----------

import glob
import os
import sys

repo_root = os.path.abspath("../..")  # the repo root, so the import below works everywhere
sys.path.insert(0, repo_root)

from src import bronze, config, xlsx

load_run_id = bronze.new_run_id()
paths = sorted(
    path
    for path in glob.glob(config.TABLE_C_FILES_GLOB)
    if not os.path.basename(path).startswith("~$")  # skip Excel's lock files
)
if not paths:
    dbutils.notebook.exit(f"SKIPPED: no Table C files in {config.TABLE_C_FOLDER}. Download them by hand first. See the steps above.")
if len(paths) != config.TABLE_C_FILE_COUNT:
    raise RuntimeError(f"Expected {config.TABLE_C_FILE_COUNT} Table C files, but found {len(paths)}: {paths}")
raw_files = [bronze.raw_file(path) for path in paths]
print(f"Reading {len(paths)} files from {config.TABLE_C_FOLDER}")

# COMMAND ----------


def is_header(cells):
    """Table C's header has Total Population in column D."""
    return xlsx.one_line((cells + [""] * 4)[3]) == "total population"


def read_row(cells):
    """Table C's rule: a place in column B and a whole number in column D. Columns A and C are empty."""
    first, place, middle, count = cells
    if first.strip() or middle.strip():
        return "has text in column A or C, where Table C has none"
    if not place.strip():
        return "has no place in column B"
    if xlsx.to_count(count) is None:
        return f"has no whole number in column D: {count!r}"
    return None


rows, manifest, issues, skipped = [], [], [], []
for path in paths:
    source_file = os.path.basename(path)
    for sheet_name in xlsx.sheet_names(path):
        cells_by_row = xlsx.read_sheet(path, sheet_name)
        header = next((i for i, (_, cells) in enumerate(cells_by_row) if is_header(cells)), None)
        if header is None:
            skipped.append(f"{source_file} / {sheet_name}")
            manifest.append(xlsx.skipped_sheet(source_file, sheet_name, cells_by_row, "no Table C header: column D does not say Total Population"))
            continue
        data, sheet_row, sheet_issues = xlsx.sort_sheet(source_file, sheet_name, cells_by_row, header, 4, read_row)
        manifest.append(sheet_row)
        issues.extend(sheet_issues)
        block, previous = 0, None
        for row_number, (_, place_name_raw, _, population_raw) in data:
            if previous is None:
                kind = "sheet_head"
            elif row_number > previous + 1:
                block, kind = block + 1, "block_head"  # a gap in the row numbers means a new city or town
            else:
                kind = "row"
            previous = row_number
            rows.append(
                (
                    source_file, sheet_name, row_number, place_name_raw, population_raw, xlsx.to_count(population_raw),
                    block, kind == "sheet_head", kind == "block_head", sheet_name in config.TABLE_C_DUPLICATE_SHEETS,
                )
            )
print(f"Read {len(rows):,} rows from {len(paths)} files. Parse issues: {len(issues):,}. Sheets that are not Table C: {skipped or 'none'}")
bronze.save_parse_audit(spark, load_run_id, "2024 census Table C", "census_2024_table_c", manifest, issues, raw_files, config.CENSUS_PAGE)

# COMMAND ----------

# Stop if the files are not the ones we checked, before the table is replaced.
copied = sum(row[-1] for row in rows)
found = (len(rows), copied, len(rows) - copied, len(skipped))
expected = (config.TABLE_C_EXPECTED_ROWS, config.TABLE_C_DUPLICATE_ROWS, config.TABLE_C_ANALYSIS_ROWS, config.TABLE_C_NON_DATA_SHEETS)
if found != expected:
    raise RuntimeError(
        f"Table C source contract changed: rows, copied rows, rows to use and other sheets are {found}, "
        f"but we expect {expected}. Other sheets: {skipped}. Check the PSA files and headers before you change the numbers."
    )

columns = (
    "source_file string, sheet_name string, source_row_number int, place_name_raw string, population_raw string, "
    "population_parsed long, block int, is_sheet_head boolean, is_block_head boolean, is_known_duplicate_sheet boolean"
)
census = spark.createDataFrame(rows, columns)
loaded = bronze.save_table(spark, census, "census_2024_table_c", load_run_id)
bronze.log_load(spark, load_run_id, "2024 census Table C", "census_2024_table_c", len(rows), loaded, raw_files, config.CENSUS_PAGE)
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
        SUM(IF(NOT is_sheet_head AND NOT is_block_head, population_parsed, 0)) AS barangay_population
    FROM `buildabida-capstone`.`01-bronze`.census_2024_table_c
    WHERE NOT is_known_duplicate_sheet
    GROUP BY source_file
    ORDER BY source_file
"""))
