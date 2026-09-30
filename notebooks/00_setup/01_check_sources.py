# Databricks notebook source
# MAGIC %md
# MAGIC # Check our sources
# MAGIC
# MAGIC Databricks Free Edition can only reach some websites. This notebook sends one small request to each source.
# MAGIC
# MAGIC - **OK:** we can load it with code.
# MAGIC - **HTTP 403 or BLOCKED:** download the file by hand, upload it to the `00-source.landing` volume, and write the download date in its source card.
# MAGIC - **Links come from:** `src/config.py`

# COMMAND ----------

import os
import sys

repo_root = os.path.abspath("../..")  # the repo root, so the import below works everywhere
sys.path.insert(0, repo_root)

from src import api, config

rows = [(name, api.check(url), url) for name, url in config.SOURCE_CHECKS.items()]
display(spark.createDataFrame(rows, "source string, status string, url string"))
