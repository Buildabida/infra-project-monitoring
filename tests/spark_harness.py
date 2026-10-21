"""Run a Databricks Python notebook on local Spark with Delta, for gate tests.

Open-source Spark rejects the hyphenated Unity Catalog schema names, so the harness
renames them and skips `USE CATALOG`. Nothing else in the notebook changes.
"""

import re
import shutil
import tempfile
from pathlib import Path

SCHEMA_NAMES = {
    "`01-bronze`": "s01_bronze",
    "`02-silver`": "s02_silver",
    "`03-gold`": "s03_gold",
    "`04-validation`": "s04_validation",
    "`05-analytics`": "s05_analytics",
}


def local_name(sql):
    for unity_name, spark_name in SCHEMA_NAMES.items():
        sql = sql.replace(unity_name, spark_name)
    return sql


def start_spark():
    """Return a local Spark session with Delta, or None when Spark is not installed."""
    try:
        from delta import configure_spark_with_delta_pip
        from pyspark.sql import SparkSession
    except ImportError:
        return None
    warehouse = tempfile.mkdtemp(prefix="gate-warehouse-")
    builder = (
        SparkSession.builder.master("local[1]")
        .appName("quality-gate-tests")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.sql.warehouse.dir", warehouse)
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
    )
    spark = configure_spark_with_delta_pip(builder).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    spark._gate_warehouse = warehouse
    return spark


def stop_spark(spark):
    spark.stop()
    shutil.rmtree(spark._gate_warehouse, ignore_errors=True)


class LocalSpark:
    """Pass every call to Spark, renaming schemas and skipping USE CATALOG."""

    def __init__(self, spark):
        self._spark = spark

    def sql(self, query, args=None, **kwargs):
        if re.match(r"\s*USE CATALOG\b", query, re.IGNORECASE):
            return None
        return self._spark.sql(local_name(query), args=args, **kwargs)

    def table(self, name):
        return self._spark.table(local_name(name))

    def __getattr__(self, name):
        return getattr(self._spark, name)


class Widgets:
    def __init__(self, values):
        self._values = dict(values)

    def text(self, name, default, label=None):
        self._values.setdefault(name, default)

    def get(self, name):
        return self._values[name]


class DbUtils:
    def __init__(self, widgets):
        self.widgets = Widgets(widgets)


def run_notebook(spark, path, widgets=None):
    """Execute a Databricks Python source notebook. Raises what the notebook raises."""
    source = Path(path).read_text(encoding="utf-8")
    namespace = {
        "spark": LocalSpark(spark),
        "dbutils": DbUtils(widgets or {}),
        "display": lambda *args, **kwargs: None,
        "__name__": "__notebook__",
    }
    exec(compile(source, str(path), "exec"), namespace)  # noqa: S102 - runs the notebook under test
    return namespace
