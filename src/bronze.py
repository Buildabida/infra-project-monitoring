"""Shared mechanics for raw, snapshot-aware CSV-to-Delta Bronze ingestion.

The module intentionally owns only reusable technical behavior: source prechecks,
deterministic artifact identity, minimal Delta-safe header handling, current-table
reconciliation, atomic selected-snapshot replacement, row-count preservation, and
operational lineage. Source meaning stays in ``config.py`` and business transformation
stays downstream.

The design favors a small functional API over classes or metaprogramming. This keeps six
source notebooks thin, makes failure paths explicit, and avoids expensive work such as
schema inference or full-file hashing for the large MGB CSV.
"""

import csv
import datetime as dt
import hashlib
import json
import os
import re
import uuid

from src import config

UTC = dt.timezone.utc
LOAD_LOG_COLUMNS = (
    "run_id string, source_name string, table_name string, snapshot_id string, "
    "source_path string, source_format string, source_size_bytes long, "
    "source_modified_at timestamp, source_modified_ns long, source_version string, rows_loaded long, "
    "status string, started_at timestamp, completed_at timestamp, "
    "error_message string, column_mapping_json string"
)
INVALID_DELTA_COLUMN_CHARS = re.compile(r"[ ,;{}()\n\t=]+")


def quoted_name(name):
    """Quote one Spark SQL identifier."""
    return f"`{str(name).replace('`', '``')}`"


def table_name(table, schema=config.BRONZE):
    """Return a three-part name quoted for the project's hyphenated names."""
    return ".".join(map(quoted_name, (config.CATALOG, schema, table)))


def new_run_id():
    """Return a collision-resistant run ID without embedding a local date."""
    return str(uuid.uuid4())


def parse_bool(value):
    """Parse a notebook widget boolean and reject ambiguous values."""
    normalized = str(value).strip().casefold()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n", ""}:
        return False
    raise ValueError(f"Expected a boolean value, got {value!r}")


def inspect_source(path):
    """Read inexpensive file metadata and the CSV header only."""
    path = os.fspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Required R2 volume file does not exist: {path}")
    stat = os.stat(path)
    if stat.st_size <= 0:
        raise ValueError(f"Required R2 volume file is empty: {path}")
    modified_at = dt.datetime.fromtimestamp(stat.st_mtime, UTC)
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as source_file:
            rows = csv.reader(source_file)
            header = next(rows)
            # Read only until any non-whitespace byte after the header. Avoid parsing
            # a potentially very large geometry field merely to prove the file is nonempty.
            has_data_row = any(
                chunk.strip() for chunk in iter(lambda: source_file.read(8_192), "")
            )
    except StopIteration as error:
        raise ValueError(f"CSV has no header row: {path}") from error
    if not header or any(not name.strip() for name in header):
        raise ValueError(f"CSV has an empty or unusable header name: {path}")
    if not has_data_row:
        raise ValueError(f"CSV has a header but no data rows: {path}")
    folded = [name.casefold() for name in header]
    duplicates = sorted({name for name in folded if folded.count(name) > 1})
    if duplicates:
        raise ValueError(
            f"CSV has duplicate header names (case-insensitive): {duplicates}"
        )
    reserved_names = {name.casefold() for name in config.INGEST_METADATA_COLUMNS}
    reserved = sorted(name for name in header if name.casefold() in reserved_names)
    if reserved:
        raise ValueError(
            f"CSV business columns conflict with ingestion metadata: {reserved}"
        )
    return {
        "path": path,
        "file_name": os.path.basename(path),
        "size_bytes": int(stat.st_size),
        "modified_at": modified_at,
        "modified_ns": int(stat.st_mtime_ns),
        "header": header,
    }


def deterministic_snapshot_id(source_name, metadata, source_version=None):
    """Derive a stable ID from cheap metadata, never from full-file hashing."""
    identity = "|".join(
        (
            source_name,
            metadata["path"],
            str(metadata["size_bytes"]),
            str(metadata["modified_ns"]),
            source_version or "",
        )
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    return f"metadata-{digest}"


def _column_mapping(header):
    """Sanitize only characters Delta cannot store and return old-to-new mapping."""
    revised = []
    mapping = {}
    for original in header:
        safe = INVALID_DELTA_COLUMN_CHARS.sub("_", original)
        if not safe.strip("_"):
            raise ValueError(
                f"Header {original!r} cannot be converted to a usable Delta column"
            )
        revised.append(safe)
        if safe != original:
            mapping[original] = safe
    folded = [name.casefold() for name in revised]
    duplicates = sorted({name for name in folded if folded.count(name) > 1})
    if duplicates:
        raise ValueError(
            f"Technical header sanitization would create duplicate names: {duplicates}"
        )
    reserved_names = {name.casefold() for name in config.INGEST_METADATA_COLUMNS}
    reserved = sorted(name for name in revised if name.casefold() in reserved_names)
    if reserved:
        raise ValueError(
            f"Technical header sanitization conflicts with ingestion metadata: {reserved}"
        )
    return revised, mapping


def _log_row(
    run_id,
    source,
    metadata,
    snapshot_id,
    status,
    started_at,
    completed_at=None,
    rows_loaded=None,
    error_message=None,
    column_mapping=None,
):
    """Build one compact load-log event using the fixed audit schema."""
    return (
        run_id,
        source["name"],
        source["table"],
        snapshot_id,
        metadata["path"],
        "csv",
        metadata["size_bytes"],
        metadata["modified_at"],
        metadata["modified_ns"],
        source.get("source_version"),
        rows_loaded,
        status,
        started_at,
        completed_at,
        error_message,
        json.dumps(column_mapping or {}, ensure_ascii=False, sort_keys=True),
    )


def _append_log(spark, row):
    """Append one operational event without storing source rows or large metadata blobs."""
    frame = spark.createDataFrame([row], LOAD_LOG_COLUMNS)
    frame.write.format("delta").mode("append").option(
        "mergeSchema", "true"
    ).saveAsTable(table_name("load_log"))


def _snapshot_audit_rows(spark, source_name, snapshot_id, functions):
    """Return the newest audit event that claims a source/snapshot identity."""
    log_name = table_name("load_log")
    if not spark.catalog.tableExists(log_name):
        return []
    log = spark.table(log_name)
    needed = {
        "source_name",
        "snapshot_id",
        "status",
        "started_at",
        "completed_at",
    }
    if not needed.issubset(log.columns):
        return []
    row = (
        log.where(
            (log["source_name"] == source_name) & (log["snapshot_id"] == snapshot_id)
        )
        .orderBy(
            functions.coalesce(log["completed_at"], log["started_at"]).desc(),
            log["completed_at"].desc_nulls_last(),
        )
        .limit(1)
        .first()
    )
    return [] if row is None else [row]


def _current_table_state(spark, source, functions):
    """Return the small identity summary needed to verify a safe skip.

    Delta commits are atomic, so a table containing one internally consistent
    snapshot is also enough to recover from a previous run whose table commit
    succeeded but whose terminal audit append did not.
    """
    target = table_name(source["table"])
    if not spark.catalog.tableExists(target):
        return None

    frame = spark.table(target)
    required = {
        "_source_snapshot_id",
        "_source_path",
        "_source_file",
        "_source_file_size_bytes",
        "_source_modified_ns",
    }
    if not required.issubset(frame.columns):
        return None

    identity_columns = tuple(sorted(required))
    null_condition = None
    for name in identity_columns:
        condition = functions.col(name).isNull()
        null_condition = (
            condition if null_condition is None else null_condition | condition
        )

    row = frame.agg(
        functions.count(functions.lit(1)).alias("rows_loaded"),
        *(
            functions.countDistinct(functions.col(name)).alias(f"distinct_{index}")
            for index, name in enumerate(identity_columns)
        ),
        *(
            functions.first(functions.col(name), ignorenulls=True).alias(
                f"value_{index}"
            )
            for index, name in enumerate(identity_columns)
        ),
        functions.coalesce(
            functions.sum(functions.when(null_condition, 1).otherwise(0)),
            functions.lit(0),
        ).alias("identity_nulls"),
    ).first()
    return {
        "rows_loaded": int(row["rows_loaded"]),
        "identity_nulls": int(row["identity_nulls"]),
        **{name: row[f"value_{index}"] for index, name in enumerate(identity_columns)},
        "identity_is_single": all(
            int(row[f"distinct_{index}"]) == 1
            for index, _ in enumerate(identity_columns)
        ),
    }


def _same_current_table(state, metadata, snapshot_id, expected_rows=None):
    """Return whether the committed table is exactly the requested artifact."""
    if not state or not state["identity_is_single"] or state["identity_nulls"]:
        return False
    if state["rows_loaded"] <= 0:
        return False
    if expected_rows is not None and state["rows_loaded"] != int(expected_rows):
        return False
    return (
        state["_source_snapshot_id"] == snapshot_id
        and state["_source_path"] == metadata["path"]
        and state["_source_file"] == metadata["file_name"]
        and int(state["_source_file_size_bytes"]) == metadata["size_bytes"]
        and int(state["_source_modified_ns"]) == metadata["modified_ns"]
    )


def _has_required_alias(header, candidates):
    """Return whether at least one documented source-column alias is present."""
    actual = {name.casefold() for name in header}
    return any(name.casefold() in actual for name in candidates)


def validate_source_header(source, header):
    """Fail before a write when documented identifying columns are absent."""
    required = source.get("required_columns", ())
    missing = [name for name in required if name not in header]
    if missing:
        raise ValueError(f"Required identifying columns are missing: {missing}")
    required_any = source.get("required_any_columns", source.get("key_candidates", ()))
    if required_any and not _has_required_alias(header, required_any):
        raise ValueError(
            "None of the documented identifying columns is present: "
            + ", ".join(required_any)
        )


def _same_metadata(row, metadata, source):
    """Compare an audit claim with the selected artifact's inexpensive identity."""
    return (
        row["source_path"] == metadata["path"]
        and int(row["source_size_bytes"]) == metadata["size_bytes"]
        and int(row["source_modified_ns"]) == metadata["modified_ns"]
        and row["source_version"] == source.get("source_version")
    )


def load_csv_snapshot(spark, source, snapshot_id="", force_reload=False):
    """Preserve one R2 CSV as the selected/current Bronze snapshot.

    The function checks the artifact and header before replacement, fails closed on
    snapshot conflicts, verifies current table state before a skip, reads business
    values as strings, adds technical lineage, and reconciles source and target rows.
    The source is scanned once during the write. Delta overwrite is atomic, so readers
    see either the previous complete table or the new complete table.
    """
    from pyspark.sql import Observation
    from pyspark.sql import functions as F

    metadata = inspect_source(source["path"])
    clean_header, column_mapping = _column_mapping(metadata["header"])
    snapshot_id = (snapshot_id or "").strip() or deterministic_snapshot_id(
        source["name"], metadata, source.get("source_version")
    )
    force_reload = parse_bool(force_reload)
    audits = _snapshot_audit_rows(spark, source["name"], snapshot_id, F)
    completed = (
        audits
        if audits
        and audits[0]["status"] in {"SUCCESS", "SKIPPED_IDEMPOTENT"}
        and audits[0]["rows_loaded"] is not None
        else []
    )
    started_at = dt.datetime.now(UTC)
    run_id = new_run_id()

    if audits and not _same_metadata(audits[0], metadata, source):
        error = RuntimeError(
            f"Snapshot conflict for {source['name']!r}: {snapshot_id!r} was already used "
            "with a different version, path, size, or modification time. Use a new snapshot ID."
        )
        try:
            _append_log(
                spark,
                _log_row(
                    run_id,
                    source,
                    metadata,
                    snapshot_id,
                    "FAILED",
                    started_at,
                    completed_at=dt.datetime.now(UTC),
                    error_message=str(error),
                    column_mapping=column_mapping,
                ),
            )
        except Exception as log_error:  # noqa: BLE001 - preserve the conflict
            print(f"Could not record snapshot conflict in load_log: {log_error}")
        raise error

    current = _current_table_state(spark, source, F)
    previous_rows = completed[0]["rows_loaded"] if completed else None
    current_matches = _same_current_table(
        current,
        metadata,
        snapshot_id,
        expected_rows=previous_rows,
    )
    if (
        current
        and current.get("_source_snapshot_id") == snapshot_id
        and not current_matches
    ):
        error = RuntimeError(
            f"Current Bronze table for {source['name']!r} claims snapshot {snapshot_id!r} "
            "but its source metadata or row count does not match. Use a new snapshot ID "
            "or investigate the existing table before replacing it."
        )
        try:
            _append_log(
                spark,
                _log_row(
                    run_id,
                    source,
                    metadata,
                    snapshot_id,
                    "FAILED",
                    started_at,
                    completed_at=dt.datetime.now(UTC),
                    error_message=str(error),
                    column_mapping=column_mapping,
                ),
            )
        except Exception as log_error:  # noqa: BLE001 - preserve the conflict
            print(f"Could not record current-table conflict in load_log: {log_error}")
        raise error

    if current_matches and not force_reload:
        _append_log(
            spark,
            _log_row(
                run_id,
                source,
                metadata,
                snapshot_id,
                "SKIPPED_IDEMPOTENT",
                started_at,
                completed_at=dt.datetime.now(UTC),
                rows_loaded=current["rows_loaded"],
                column_mapping=column_mapping,
            ),
        )
        return {
            "status": "SKIPPED_IDEMPOTENT",
            "run_id": run_id,
            "snapshot_id": snapshot_id,
            "rows_loaded": current["rows_loaded"],
        }

    _append_log(
        spark,
        _log_row(
            run_id,
            source,
            metadata,
            snapshot_id,
            "STARTED",
            started_at,
            column_mapping=column_mapping,
        ),
    )
    try:
        frame = (
            spark.read.option("header", "true")
            .option("inferSchema", "false")
            .option("mode", "FAILFAST")
            .option("multiLine", "false")
            .csv(metadata["path"])
        )
        if len(frame.columns) != len(clean_header):
            raise ValueError(
                f"Spark read {len(frame.columns)} columns but the header has {len(clean_header)}"
            )
        frame = frame.toDF(*clean_header)
        validate_source_header(source, frame.columns)

        observed = Observation("source_rows")
        prepared = (
            frame.withColumn("_source_system", F.lit(source["source_system"]))
            .withColumn("_source_path", F.lit(metadata["path"]))
            .withColumn("_source_file", F.lit(metadata["file_name"]))
            .withColumn("_source_format", F.lit("csv"))
            .withColumn("_source_snapshot_id", F.lit(snapshot_id))
            .withColumn("_ingest_run_id", F.lit(run_id))
            .withColumn("_ingested_at", F.current_timestamp())
            .withColumn(
                "_source_file_size_bytes", F.lit(metadata["size_bytes"]).cast("long")
            )
            .withColumn(
                "_source_modified_ns", F.lit(metadata["modified_ns"]).cast("long")
            )
            .withColumn(
                "_source_modified_at", F.lit(metadata["modified_at"]).cast("timestamp")
            )
            .observe(observed, F.count(F.lit(1)).alias("rows"))
        )
        prepared.write.format("delta").mode("overwrite").option(
            "overwriteSchema", "true"
        ).saveAsTable(table_name(source["table"]))
        source_rows = int(observed.get["rows"])
        rows_loaded = spark.table(table_name(source["table"])).count()
        if source_rows <= 0:
            raise RuntimeError(
                "The CSV header was readable but the source contained no data rows"
            )
        if rows_loaded != source_rows:
            raise RuntimeError(
                f"Source-to-Bronze row preservation failed: source={source_rows}, Bronze={rows_loaded}"
            )
        _append_log(
            spark,
            _log_row(
                run_id,
                source,
                metadata,
                snapshot_id,
                "SUCCESS",
                started_at,
                completed_at=dt.datetime.now(UTC),
                rows_loaded=rows_loaded,
                column_mapping=column_mapping,
            ),
        )
        return {
            "status": "SUCCESS",
            "run_id": run_id,
            "snapshot_id": snapshot_id,
            "rows_loaded": rows_loaded,
        }
    except Exception as error:
        try:
            _append_log(
                spark,
                _log_row(
                    run_id,
                    source,
                    metadata,
                    snapshot_id,
                    "FAILED",
                    started_at,
                    completed_at=dt.datetime.now(UTC),
                    error_message=str(error).strip()[:2_000],
                    column_mapping=column_mapping,
                ),
            )
        except Exception as log_error:  # noqa: BLE001 - preserve the original exception
            print(f"Could not record FAILED in load_log: {log_error}")
        raise
