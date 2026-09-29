# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: boundary maps
# MAGIC
# MAGIC Loads the shapes of regions, provinces, cities, towns and barangays into `01-bronze`.`boundaries`. One row is one shape. Each shape has its PSGC code, so silver can find the place of every project map point.
# MAGIC
# MAGIC We load 7 of the 8 files in the snapshot, 43,760 shapes. We skip the special areas file (D-17). The reason is in `src/config.py`.
# MAGIC
# MAGIC The shapes come from the barangay-boundaries-repository on GitHub (PSA codes on NAMRIA maps, snapshot 2023-10-24, MIT license). The link in `src/config.py` is pinned to one commit, so the files never change under us.
# MAGIC
# MAGIC 1. Downloads each file as it came into the landing volume.
# MAGIC 2. Keeps the main fields as columns and the full shape as GeoJSON text.
# MAGIC 3. Adds a row to `01-bronze`.`load_log` with the number of shapes in the files.
# MAGIC
# MAGIC The codes are from 2023. The Negros Island Region (2024) and Sulu's move out of BARMM (2024) are not in these maps yet. Silver maps each shape to the current PSGC.

# COMMAND ----------

import json
import sys

sys.path.append("../..")  # the repo root, so the import below works everywhere

from src import api, bronze, config

# COMMAND ----------

# 1. Download the files as they came.
folder = bronze.landing_folder("boundaries", config.BOUNDARY_SNAPSHOT)
for name in config.BOUNDARY_FILES:
    api.download(config.BOUNDARY_BASE + name, f"{folder}/{name}")
    print("Saved", name)

# COMMAND ----------

# 2. One line per shape: the main fields, all fields as JSON text, and the shape as GeoJSON text.
rows_folder = bronze.landing_folder("boundaries", config.BOUNDARY_SNAPSHOT, "rows")


def shape_rows(name, features):
    for feature in features:
        props, geometry = feature["properties"], feature["geometry"]
        yield {
            "boundary_class": name.removesuffix(".geojson"),
            "psgc_code": props.get("psgc_code"),
            "psgc_name": props.get("psgc_name"),
            "psgc_type": props.get("psgc_type"),
            "psgc_status": props.get("psgc_status"),
            "match_confidence": props.get("match_confidence"),
            "match_method": props.get("match_method"),
            "area_sqkm": props.get("AREA_SQKM"),
            "properties_json": json.dumps(props, ensure_ascii=False),
            "geometry_type": geometry["type"] if geometry else None,
            "geometry_json": json.dumps(geometry) if geometry else None,
            "source_file": f"{folder}/{name}",
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
schema = (
    "boundary_class string, psgc_code string, psgc_name string, psgc_type string, psgc_status string, "
    "match_confidence double, match_method string, area_sqkm double, properties_json string, "
    "geometry_type string, geometry_json string, source_file string"
)
shapes = spark.read.schema(schema).json(row_files)
loaded = bronze.save_table(spark, shapes, "boundaries")
bronze.log_load(spark, "Boundary maps (2023-10-24)", "boundaries", expected, loaded, folder)
print(f"Loaded {loaded:,} of {expected:,} shapes.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick look

# COMMAND ----------

display(spark.sql("""
    SELECT boundary_class, COUNT(*) AS shapes, COUNT(psgc_code) AS with_code
    FROM `buildabida-capstone`.`01-bronze`.boundaries
    GROUP BY boundary_class
    ORDER BY shapes
"""))
