"""Shared steps for our bronze notebooks: save the raw copy, save the table, log the load."""

import datetime
import glob
import json
import os

from src import config


def today():
    """Today's date in the Philippines, like 2026-09-29. Each run saves its raw files under this date."""
    manila = datetime.timezone(datetime.timedelta(hours=8))
    return datetime.datetime.now(manila).strftime("%Y-%m-%d")


def landing_folder(*parts):
    """Make a folder in the landing volume and return its path."""
    path = "/".join([config.LANDING, *parts])
    os.makedirs(path, exist_ok=True)
    return path


def write_json_lines(path, records):
    """Save one record per line, as it came. Spark reads these files straight from the volume."""
    with open(path, "w", encoding="utf-8") as file:
        file.writelines(
            json.dumps(record, ensure_ascii=False) + "\n" for record in records
        )


def find_file(folder, pattern):
    """Return the newest file in a folder that matches a pattern, or None if there is none."""
    matches = sorted(glob.glob(f"{folder}/{pattern}"), key=os.path.getmtime)
    return matches[-1] if matches else None


def table_name(table, schema=config.BRONZE):
    """Full name with backticks, because our catalog and schemas have hyphens."""
    return f"`{config.CATALOG}`.`{schema}`.{table}"


def save_table(spark, df, table, schema=config.BRONZE):
    """Replace the table with this run's rows, plus the load time. Safe to run twice."""
    from pyspark.sql import functions as F

    df = df.withColumn("load_ts", F.current_timestamp())
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        table_name(table, schema)
    )
    return spark.table(table_name(table, schema)).count()


def log_load(spark, source, table, rows_expected, rows_loaded, raw_copy):
    """Add one row to 01-bronze.load_log, so every load can be traced and checked."""
    from pyspark.sql import functions as F

    row = [(source, table, int(rows_expected), int(rows_loaded), raw_copy)]
    columns = "source string, table_name string, rows_expected long, rows_loaded long, raw_copy string"
    log = spark.createDataFrame(row, columns).withColumn(
        "load_ts", F.current_timestamp()
    )
    log.write.mode("append").saveAsTable(table_name("load_log"))
    return rows_expected == rows_loaded
