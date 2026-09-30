"""Shared steps for our bronze notebooks: save the raw copy, save the table and log the load."""

import datetime
import hashlib
import json
import os

from src import config, xlsx

MANILA = datetime.timezone(datetime.timedelta(hours=8))

LOG_COLUMNS = (
    "run_id string, source string, table_name string, rows_expected long, rows_loaded long, "
    "raw_copy string, source_url string, "
    "raw_files array<struct<path: string, size_bytes: long, sha256: string>>"
)


def new_run_id():
    """A new ID for one load, like 20260930T141503123456+0800. It is the start time in Manila, so IDs sort by time."""
    return datetime.datetime.now(MANILA).strftime("%Y%m%dT%H%M%S%f+0800")


def landing_folder(*parts):
    """Make a folder in the landing volume and return its path."""
    path = "/".join([config.LANDING, *parts])
    os.makedirs(path, exist_ok=True)
    return path


def save_raw(path, content):
    """Save a reply exactly as it came. Return (path, size in bytes, SHA-256), so we can prove it never changed."""
    with open(path, "wb") as file:
        file.write(content)
    return path, len(content), hashlib.sha256(content).hexdigest()


def raw_file(path):
    """Return (path, size in bytes, SHA-256) for a raw file that is already in the landing volume."""
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            digest.update(block)
    return path, os.path.getsize(path), digest.hexdigest()


def write_json_lines(path, records):
    """Save one record per line. Spark reads these files straight from the volume."""
    with open(path, "w", encoding="utf-8") as file:
        file.writelines(
            json.dumps(record, ensure_ascii=False) + "\n" for record in records
        )


def table_name(table, schema=config.BRONZE):
    """Full name with backticks, because our catalog and schemas have hyphens."""
    return f"`{config.CATALOG}`.`{schema}`.{table}"


def save_table(spark, df, table, run_id, schema=config.BRONZE):
    """Replace the table with this run's rows, plus the run ID and the load time. Safe to run twice."""
    from pyspark.sql import functions as F

    df = df.withColumn("_ingest_run_id", F.lit(run_id)).withColumn(
        "load_ts", F.current_timestamp()
    )
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        table_name(table, schema)
    )
    return spark.table(table_name(table, schema)).count()


def log_load(
    spark, run_id, source, table, rows_expected, rows_loaded, raw_files, source_url
):
    """Add one row to 01-bronze.load_log, so every load can be traced and checked.

    raw_files is the list of (path, size in bytes, SHA-256) of the raw files the load read.
    """
    from pyspark.sql import functions as F

    paths = [path for path, _, _ in raw_files]
    raw_copy = paths[0] if len(paths) == 1 else os.path.commonpath(paths)
    row = [
        (
            run_id,
            source,
            table,
            int(rows_expected),
            int(rows_loaded),
            raw_copy,
            source_url,
            [(path, size, sha256) for path, size, sha256 in raw_files],
        )
    ]
    log = spark.createDataFrame(row, LOG_COLUMNS).withColumn(
        "load_ts", F.current_timestamp()
    )
    log.write.mode("append").option("mergeSchema", "true").saveAsTable(
        table_name("load_log")
    )
    return rows_expected == rows_loaded


def save_parse_audit(
    spark, run_id, source, table, manifest, issues, raw_files, source_url
):
    """Save the sheet manifest and the parse issues of one Excel load, and log both.

    Then stop before the main table is replaced if any row could not be read.
    """
    for name, rows, columns in (
        (f"{table}_sheet_manifest", manifest, xlsx.MANIFEST_COLUMNS),
        (f"{table}_parse_issues", issues, xlsx.ISSUE_COLUMNS),
    ):
        loaded = save_table(spark, spark.createDataFrame(rows, columns), name, run_id)
        log_load(spark, run_id, source, name, len(rows), loaded, raw_files, source_url)
    if issues:
        raise RuntimeError(
            f"Some rows could not be read ({len(issues):,}). They are in "
            f"`01-bronze`.{table}_parse_issues. The {table} table was not replaced."
        )
