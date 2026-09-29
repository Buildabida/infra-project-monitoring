# Databricks notebook source
# MAGIC %md
# MAGIC # Run everything
# MAGIC
# MAGIC Runs the notebooks in order: setup, the five bronze loads, then the checks. Click **Run all**. It takes about 15 minutes.
# MAGIC
# MAGIC Put the two PSA files in the landing volume first (the steps are at the top of `03_bronze_psgc` and `04_bronze_census_2024`). If they are not there yet, those two loads are skipped and the rest still run.
# MAGIC
# MAGIC When it is done, check the table at the end. Each step should say `done`.

# COMMAND ----------

steps = [
    "00_setup/00_setup_workspace",
    "01_bronze/01_bronze_dpwh_projects",
    "01_bronze/02_bronze_flood_control",
    "01_bronze/03_bronze_psgc",
    "01_bronze/04_bronze_census_2024",
    "01_bronze/05_bronze_boundaries",
    "04_validation/01_validation_bronze",
]

results = []
for step in steps:
    try:
        result = dbutils.notebook.run(f"./{step}", 3600) or "done"
    except Exception as error:  # noqa: BLE001 keep going, so one broken source does not stop the others
        result = "FAILED: " + str(error).strip().splitlines()[0][:300]
    results.append((step, result))
    print(f"{step}: {result}")

# COMMAND ----------

display(spark.createDataFrame(results, "step string, result string"))
failed = [step for step, result in results if result.startswith("FAILED")]
if failed:
    raise RuntimeError("These steps failed: " + ", ".join(failed))
