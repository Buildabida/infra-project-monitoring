# Databricks notebook source
# MAGIC %md
# MAGIC # Run everything
# MAGIC
# MAGIC Runs the setup, the bronze loads, then the bronze checks. Click **Run all**. It takes about 15 minutes.
# MAGIC
# MAGIC Put the PSA files in the landing volume first. The steps are at the top of `03_bronze_psgc`, `04_bronze_census_2024` and `06_bronze_census_table_c`.
# MAGIC
# MAGIC - **Required loads:** DPWH projects, flood control, PSGC, boundaries and Table C. If one of them fails or says `SKIPPED`, the checks don't run and say `BLOCKED`. That way the checks can never pass on an older table.
# MAGIC - **Optional load:** Table B. It may say `SKIPPED`.
# MAGIC
# MAGIC When it is done, check the table at the end. The notebook fails if any step says `FAILED` or `BLOCKED`.

# COMMAND ----------

setup_step = "00_setup/00_setup_workspace"
required_loads = [
    "01_bronze/01_bronze_dpwh_projects",
    "01_bronze/02_bronze_flood_control",
    "01_bronze/03_bronze_psgc",
    "01_bronze/05_bronze_boundaries",
    "01_bronze/06_bronze_census_table_c",
]
optional_loads = ["01_bronze/04_bronze_census_2024"]
validation_step = "04_validation/01_validation_bronze"


def run_step(step):
    """Run one notebook. Return "done", its SKIPPED message, or FAILED with the first line of the error."""
    try:
        return dbutils.notebook.run(f"./{step}", 3600) or "done"
    except Exception as error:  # noqa: BLE001 keep going, so we see every broken source in one run
        return "FAILED: " + str(error).strip().splitlines()[0][:300]


results = []
setup_result = run_step(setup_step)
results.append((setup_step, setup_result))
if setup_result.startswith(("FAILED", "SKIPPED")):
    display(spark.createDataFrame(results, "step string, result string"))
    raise RuntimeError(f"Setup did not finish: {setup_result}")

for step in required_loads + optional_loads:
    result = run_step(step)
    results.append((step, result))
    print(f"{step}: {result}")

blocked = [step for step, result in results if step in required_loads and result.startswith(("FAILED", "SKIPPED"))]
if blocked:
    results.append((validation_step, "BLOCKED: required bronze load did not finish: " + ", ".join(blocked)))
else:
    results.append((validation_step, run_step(validation_step)))

# COMMAND ----------

display(spark.createDataFrame(results, "step string, result string"))
failed = [step for step, result in results if result.startswith(("FAILED", "BLOCKED"))]
if failed:
    raise RuntimeError("Pipeline did not finish: " + ", ".join(failed))
