# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: boundary maps
# MAGIC
# MAGIC Loads the shapes of regions, provinces, cities, towns and barangays into `01-bronze`.`boundaries`. One row is one map feature, kept whole as GeoJSON text in `source_feature_json`, with its file and its place in the file. The key is `source_file` and `source_feature_index`.
# MAGIC
# MAGIC We load 7 of the 8 files in the snapshot, 43,760 shapes. We skip the special areas file (D-17). The reason is in `src/config.py`.
# MAGIC
# MAGIC The shapes come from the barangay-boundaries-repository on GitHub (PSA codes on NAMRIA maps, snapshot 2023-10-24, MIT license). The link in `src/config.py` is pinned to one commit, so the files never change under us.
# MAGIC
# MAGIC 1. Downloads each file once into the landing volume, as it came. A later run uses the same files.
# MAGIC 2. Writes one line per feature: the whole feature, its file and its place in the file.
# MAGIC 3. Adds a row to `01-bronze`.`load_log` with the number of features, the files, their sizes and their SHA-256 fingerprints.
# MAGIC
# MAGIC Bronze doesn't pull fields out of the feature. Silver reads the PSGC code, the name and the shape from `source_feature_json`, and the checks do the same with `get_json_object`.
# MAGIC
# MAGIC The codes are from 2023. The Negros Island Region (2024) and Sulu's move out of BARMM (2024) are not in these maps yet. Silver maps each shape to the current PSGC.

# COMMAND ----------

import json
import os
import sys

repo_root = os.path.abspath("../..")  # the repo root, so the import below works everywhere
sys.path.insert(0, repo_root)

from src import api, bronze, config

# COMMAND ----------

# 1. Download each file once, as it came. The download goes to a temporary file first, so a cut download never looks whole.
load_run_id = bronze.new_run_id()
folder = bronze.landing_folder("boundaries", config.BOUNDARY_SNAPSHOT)
for name in config.BOUNDARY_FILES:
    if not os.path.exists(f"{folder}/{name}"):
        api.download(config.BOUNDARY_BASE + name, f"{folder}/{name}")
        print("Downloaded", name)
raw_files = [bronze.raw_file(f"{folder}/{name}") for name in config.BOUNDARY_FILES]

# COMMAND ----------

# 2. One line per feature: the whole feature as JSON text, its place in the file and the file.
rows_folder = bronze.landing_folder("boundaries", config.BOUNDARY_SNAPSHOT, "rows")


def shape_rows(name, features):
    for feature_index, feature in enumerate(features):
        yield {
            "source_feature_index": feature_index,
            "source_feature_json": json.dumps(feature, ensure_ascii=False),
            "source_file": f"{folder}/{name}",
            "boundary_class": name.removesuffix(".geojson"),
        }


expected = 0
for name in config.BOUNDARY_FILES:
    with open(f"{folder}/{name}", encoding="utf-8") as file:
        features = json.load(file)["features"]
    expected += len(features)
    bronze.write_json_lines(f"{rows_folder}/{name.removesuffix('.geojson')}.json", shape_rows(name, features))
    print(f"{name}: {len(features):,} shapes")
    del features

# COMMAND ----------

# 3. Read the lines with a set schema, so Spark does not scan the big shapes to guess types.
# Read only the files we load, so an old file left in the folder is never counted.
row_files = [f"{rows_folder}/{name.removesuffix('.geojson')}.json" for name in config.BOUNDARY_FILES]
schema = "source_feature_index long, source_feature_json string, source_file string, boundary_class string"
shapes = spark.read.schema(schema).json(row_files)
loaded = bronze.save_table(spark, shapes, "boundaries", load_run_id)
bronze.log_load(spark, load_run_id, "Boundary maps (2023-10-24)", "boundaries", expected, loaded, raw_files, config.BOUNDARY_BASE)
print(f"Loaded {loaded:,} of {expected:,} shapes.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick look

# COMMAND ----------

display(spark.sql("""
    SELECT
        boundary_class,
        COUNT(*) AS shapes,
        COUNT(GET_JSON_OBJECT(source_feature_json, '$.properties.psgc_code')) AS with_code
    FROM `buildabida-capstone`.`01-bronze`.boundaries
    GROUP BY boundary_class
    ORDER BY shapes
"""))
