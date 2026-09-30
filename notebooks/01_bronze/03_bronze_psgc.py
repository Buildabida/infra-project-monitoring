# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: PSGC codes and the 2024 population
# MAGIC
# MAGIC Loads the PSA PSGC 2Q 2026 publication datafile into these tables:
# MAGIC
# MAGIC - `01-bronze`.`psgc`: one row per place (region, province, city, town, submunicipality or barangay). The key is `psgc_code_parsed`.
# MAGIC - `01-bronze`.`population_2024`: one row per place that has a 2024 census count in the file. Our population source is census Table C (D-18), so we use this table to cross-check it.
# MAGIC - `01-bronze`.`psgc_sheet_manifest`: one row per sheet of the file. For the PSGC sheet, it counts the title and header rows, blank rows, notes, places and rows we could not read. The counts must add up to the rows in the sheet.
# MAGIC - `01-bronze`.`psgc_parse_issues`: every row under the header that is not blank, has no PSGC code and is not a note, with its cells and the reason. If it has any rows, the load stops before it replaces `psgc`.
# MAGIC
# MAGIC Bronze keeps every cell as PSA wrote it. Three columns also get a `_parsed` copy next to the `_raw` one. `psgc_code_parsed` and `correspondence_code_parsed` put back the leading zeros that Excel drops when it saves a code as a number. `population_2024_parsed` is the count as a number. Silver does the rest of the cleaning.
# MAGIC
# MAGIC PSA blocks Databricks, so download the file by hand first:
# MAGIC
# MAGIC 1. Go to https://psa.gov.ph/classification/psgc and download the **Publication Datafile** for 2Q 2026, `PSGC-2Q-2026-Publication-Datafile.xlsx`.
# MAGIC 2. In Databricks, open **Catalog**, then `buildabida-capstone` > `00-source` > `landing`. Make a folder named `psa` and upload the file there.
# MAGIC 3. Write the download date in the PSGC source card.
# MAGIC
# MAGIC The notebook reads only this exact file, the release our docs and checks are for. For a new release, change `PSGC_FILE` in `src/config.py` and check the counts again. It is safe to run twice.

# COMMAND ----------

import os
import sys

repo_root = os.path.abspath("../..")  # the repo root, so the import below works everywhere
sys.path.insert(0, repo_root)

from src import bronze, config, xlsx

load_run_id = bronze.new_run_id()
path = f"{config.PSA_FOLDER}/{config.PSGC_FILE}"
if not os.path.exists(path):
    dbutils.notebook.exit(f"SKIPPED: {path} is not there yet. Download it by hand first. See the steps above.")
raw_files = [bronze.raw_file(path)]
source_file = os.path.basename(path)
print("Reading", path)

# COMMAND ----------

# Find each column by its header, so a release with moved columns still loads.
rows = xlsx.read_sheet(path, "PSGC")
start = next((i for i, (_, cells) in enumerate(rows) if any("10-digit psgc" in xlsx.one_line(c) for c in cells)), None)
if start is None:
    raise ValueError('No row has a "10-digit PSGC" column. Is this the PSGC publication datafile?')
header = [xlsx.one_line(c) for c in rows[start][1]]


def column(*words):
    """The first column whose header has all these words."""
    for index, name in enumerate(header):
        if all(word in name for word in words):
            return index
    raise ValueError(f"No column has {words}. The headers are: {header}")


want = {
    "psgc_code": column("10-digit psgc"),
    "name": column("name"),
    "correspondence_code": column("correspondence"),
    "geographic_level": column("geographic level"),
    "old_names": column("old names"),
    "city_class": column("city class"),
    "income_class": column("income"),
    "urban_rural": column("urban", "rural"),
    "population_2024": column("2024", "population"),
    "status": column("status"),
}

# Bronze keeps every field. If PSA adds a column, stop, so we can add it on purpose.
new_columns = [name for index, name in enumerate(header) if name and index not in want.values()]
if new_columns:
    raise ValueError(f"The PSGC file has columns we don't load yet: {new_columns}. Add them to `want` first.")

# COMMAND ----------

# Sort every row of the sheet. Places go to the table, and rows we can't read go to psgc_parse_issues.


def read_row(cells):
    """A place row has a PSGC code."""
    return None if cells[want["psgc_code"]].strip() else "has no PSGC code"


places, sheet_row, issues = xlsx.sort_sheet(source_file, "PSGC", rows, start, len(header), read_row)
manifest = [
    sheet_row if name == "PSGC" else xlsx.skipped_sheet(source_file, name, xlsx.read_sheet(path, name), "not the PSGC list")
    for name in xlsx.sheet_names(path)
]
print(f"Read {len(places):,} places. Parse issues: {len(issues):,}.")
bronze.save_parse_audit(spark, load_run_id, "PSGC publication datafile", "psgc", manifest, issues, raw_files, config.PSGC_PAGE)

# COMMAND ----------


def cell(cells, index):
    """The cell as PSA wrote it, or None if it is empty."""
    return cells[index] if cells[index].strip() else None


def with_zeros(code, width):
    """The code with its leading zeros back, or None if it is not all digits."""
    code = (code or "").strip()
    return code.zfill(width) if code.isdigit() else None


data, with_population = [], 0
for row_number, cells in places:
    raw = {name: cell(cells, index) for name, index in want.items()}
    with_population += raw["population_2024"] is not None
    data.append(
        (
            raw["psgc_code"],
            with_zeros(raw["psgc_code"], 10),
            raw["name"],
            raw["correspondence_code"],
            with_zeros(raw["correspondence_code"], 9),
            raw["geographic_level"],
            raw["old_names"],
            raw["city_class"],
            raw["income_class"],
            raw["urban_rural"],
            raw["population_2024"],
            xlsx.to_count(raw["population_2024"]),
            raw["status"],
            source_file,
            "PSGC",
            row_number,
        )
    )

columns = (
    "psgc_code_raw string, psgc_code_parsed string, name string, "
    "correspondence_code_raw string, correspondence_code_parsed string, geographic_level string, "
    "old_names string, city_class string, income_class string, urban_rural string, "
    "population_2024_raw string, population_2024_parsed long, status string, "
    "source_file string, sheet_name string, source_row_number int"
)
psgc = spark.createDataFrame(data, columns)
loaded = bronze.save_table(spark, psgc, "psgc", load_run_id)
bronze.log_load(spark, load_run_id, "PSGC publication datafile", "psgc", len(data), loaded, raw_files, config.PSGC_PAGE)

# Every place that has a population cell, with the cell as PSA wrote it and the parsed count.
population = psgc.where("population_2024_raw IS NOT NULL").select(
    "psgc_code_raw",
    "psgc_code_parsed",
    "name",
    "geographic_level",
    "population_2024_raw",
    "population_2024_parsed",
    "source_file",
    "sheet_name",
    "source_row_number",
)
counted = bronze.save_table(spark, population, "population_2024", load_run_id)
bronze.log_load(spark, load_run_id, "PSGC publication datafile", "population_2024", with_population, counted, raw_files, config.PSGC_PAGE)
print(f"Loaded {loaded:,} places and {counted:,} population counts.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick look
# MAGIC
# MAGIC The 2Q 2026 file has 18 regions, 82 provinces, 149 cities, 1,493 towns, 14 submunicipalities and 42,010 barangays.

# COMMAND ----------

display(spark.sql("""
    SELECT geographic_level, COUNT(*) AS places, SUM(population_2024_parsed) AS population_2024
    FROM `buildabida-capstone`.`01-bronze`.psgc
    GROUP BY geographic_level
    ORDER BY places
"""))
