# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: PSGC codes and the 2024 population
# MAGIC
# MAGIC Loads the PSA PSGC publication datafile into two tables:
# MAGIC
# MAGIC - `01-bronze`.`psgc`: one row per place (region, province, city, town, submunicipality or barangay). The key is `psgc_code`.
# MAGIC - `01-bronze`.`population_2024`: one row per place with its 2024 census count. The PSGC file carries the official 2024 population, so every count already has its code. Our population source is census Table C (D-18), so we use this table to cross-check it.
# MAGIC
# MAGIC PSA blocks Databricks, so download the file by hand first:
# MAGIC
# MAGIC 1. Go to https://psa.gov.ph/classification/psgc and download the latest **Publication Datafile** (for example `PSGC-2Q-2026-Publication-Datafile.xlsx`).
# MAGIC 2. In Databricks, open **Catalog**, then `buildabida-capstone` > `00-source` > `landing`. Make a folder named `psa` and upload the file there.
# MAGIC 3. Write the download date in the PSGC source card.
# MAGIC
# MAGIC It is safe to run twice. It always reads the newest file that matches.

# COMMAND ----------

import sys

sys.path.append("../..")  # the repo root, so the import below works everywhere

from src import bronze, config, xlsx

path = bronze.find_file(config.PSA_FOLDER, config.PSGC_FILE_PATTERN)
if path is None:
    dbutils.notebook.exit(f"SKIPPED: no PSGC file in {config.PSA_FOLDER}. Download it by hand first. See the steps above.")
print("Reading", path)

# COMMAND ----------

# Find each column by its header, so a new release with moved columns still loads.
rows = xlsx.read_sheet(path, "PSGC")


def clean(text):
    """Header text on one line, in lower case. Some headers break over two lines in Excel."""
    return " ".join(text.split()).lower()


def header_row(rows):
    """The header is the first row with a "10-digit PSGC" column."""
    for position, (_, cells) in enumerate(rows):
        if any("10-digit psgc" in clean(c) for c in cells):
            return position
    raise ValueError('No row has a "10-digit PSGC" column. Is this the PSGC publication datafile?')


start = header_row(rows)
header = [clean(c) for c in rows[start][1]]


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


def cell(cells, index):
    return cells[index] if index < len(cells) and cells[index] != "" else None


places = []
for row_number, cells in rows[start + 1:]:
    code = cell(cells, want["psgc_code"])
    if code is None:
        continue
    record = {name: cell(cells, index) for name, index in want.items()}
    # Codes are text with leading zeros. If Excel saved one as a number, put the zeros back.
    record["psgc_code"] = code.zfill(10) if code.isdigit() else code
    corr = record["correspondence_code"]
    record["correspondence_code"] = corr.zfill(9) if corr and corr.isdigit() else corr
    record["population_2024"] = xlsx.to_number(record["population_2024"])
    record["row_number"] = row_number
    places.append(record)
print(f"Read {len(places):,} places.")

# COMMAND ----------

columns = (
    "psgc_code string, name string, correspondence_code string, geographic_level string, old_names string, "
    "city_class string, income_class string, urban_rural string, population_2024 long, status string, "
    "row_number int, source_file string"
)
data = [tuple(p[k] for k in want) + (p["row_number"], path) for p in places]
psgc = spark.createDataFrame(data, columns)

loaded = bronze.save_table(spark, psgc, "psgc")
bronze.log_load(spark, "PSGC publication datafile", "psgc", len(places), loaded, path)

population = psgc.where("population_2024 IS NOT NULL").select(
    "psgc_code", "name", "geographic_level", "population_2024", "source_file"
)
counted = bronze.save_table(spark, population, "population_2024")
print(f"Loaded {loaded:,} places and {counted:,} population counts.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick look
# MAGIC
# MAGIC The 2Q 2026 file has 18 regions, 82 provinces, 149 cities, 1,493 towns, 14 submunicipalities and 42,010 barangays.

# COMMAND ----------

display(spark.sql("""
    SELECT geographic_level, COUNT(*) AS places, SUM(population_2024) AS population_2024
    FROM `buildabida-capstone`.`01-bronze`.psgc
    GROUP BY geographic_level
    ORDER BY places
"""))
