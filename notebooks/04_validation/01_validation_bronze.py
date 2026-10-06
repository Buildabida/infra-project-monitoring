# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # Validation: six R2 Bronze sources
# MAGIC
# MAGIC ## Purpose
# MAGIC
# MAGIC Prove that each selected Bronze snapshot is structurally safe, traceable to its
# MAGIC artifact and audit event, and faithful to source row grain. Validation reports
# MAGIC conditions; it never cleans, filters, deduplicates, or rewrites Bronze.
# MAGIC
# MAGIC ## Two levels of findings
# MAGIC
# MAGIC - **stop:** a missing table, failed/current audit, broken snapshot identity,
# MAGIC   missing required metadata, or violated source-grain contract blocks downstream use.
# MAGIC - **flag:** a known source anomaly, provenance gap, cast concern, or historical
# MAGIC   reference difference remains visible for review and Silver handling.
# MAGIC
# MAGIC ## Low-cost strategy
# MAGIC
# MAGIC Metrics for each table are combined into one Spark aggregate. The large MGB table is
# MAGIC not cached, collected as business rows, sorted, repartitioned, or scanned once per
# MAGIC individual check. Only the small audit result set reaches the driver.
# MAGIC
# MAGIC ## Step 1 — Define reusable validation result helpers

# COMMAND ----------

import os
import sys

from pyspark.sql import functions as F
from pyspark.sql.window import Window

repo_root = os.path.abspath("../..")
sys.path.insert(0, repo_root)

from src import bronze, config

validation_run_id = bronze.new_run_id()
results = []


def result(
    table, column, name, action, failed_rows, total_rows, details=None, snapshot_id=None
):
    """Add one PASS, FAIL, FLAG, or ERROR row."""
    if failed_rows is None:
        status = "ERROR"
    elif int(failed_rows) == 0:
        status = "PASS"
    else:
        status = "FAIL" if action == "stop" else "FLAG"
    percentage = (
        round(100 * int(failed_rows) / int(total_rows), 2)
        if failed_rows is not None and total_rows
        else None
    )
    results.append(
        (
            validation_run_id,
            table,
            column,
            name,
            None if failed_rows is None else int(failed_rows),
            None if total_rows is None else int(total_rows),
            percentage,
            status,
            action,
            details,
            snapshot_id,
        )
    )


def find_column(frame, candidates):
    """Return the first documented alias present, without changing source columns."""
    actual = {name.casefold(): name for name in frame.columns}
    return next(
        (actual[name.casefold()] for name in candidates if name.casefold() in actual),
        None,
    )


def q(name):
    return bronze.quoted_name(name)


def count_if(condition):
    return F.coalesce(F.sum(F.when(condition, 1).otherwise(0)), F.lit(0)).cast("long")


def invalid_cast(column, data_type):
    return F.expr(
        f"{q(column)} IS NOT NULL AND TRY_CAST({q(column)} AS {data_type}) IS NULL"
    )


def add_metric(
    metrics, key, column, name, action, expression, expected_total=None, details=None
):
    metrics.append(
        (key, column, name, action, expression.alias(key), expected_total, details)
    )


def missing_column(table, label, candidates, action="flag"):
    result(
        table,
        label,
        "required source field is present",
        action,
        1,
        1,
        "None of these documented aliases exists: " + ", ".join(candidates),
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Resolve the latest audit state
# MAGIC
# MAGIC Validation reads only the small `load_log` table to find the latest status for each
# MAGIC Bronze target. `STARTED` or `FAILED` cannot be hidden by an older `SUCCESS`, and an
# MAGIC idempotent skip remains acceptable only when its table metadata agrees.

# COMMAND ----------

# Latest terminal result is tiny audit metadata, not source data.
latest_logs = {}
log_name = bronze.table_name("load_log")
if spark.catalog.tableExists(log_name):
    log = spark.table(log_name)
    required_log_columns = {
        "table_name",
        "status",
        "started_at",
        "completed_at",
        "rows_loaded",
        "snapshot_id",
    }
    if required_log_columns.issubset(log.columns):
        window = Window.partitionBy("table_name").orderBy(
            F.coalesce(F.col("completed_at"), F.col("started_at")).desc_nulls_last()
        )
        latest = (
            log.where(
                F.col("status").isin(
                    "STARTED", "SUCCESS", "FAILED", "SKIPPED_IDEMPOTENT"
                )
            )
            .withColumn("_newest", F.row_number().over(window))
            .where(F.col("_newest") == 1)
            .drop("_newest")
        )
        latest_logs = {row["table_name"]: row for row in latest.toLocalIterator()}


# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Build one grouped check set per source
# MAGIC
# MAGIC Every table receives common row, snapshot, metadata, key, and audit checks. The
# MAGIC source-specific branch then adds only rules supported by that source contract:
# MAGIC
# MAGIC - DPWH values are checked non-destructively for category and cast concerns.
# MAGIC - Flood-control ContractID repetition is a `flag`, never a deduplication rule.
# MAGIC - PSGC population remains a cross-check field.
# MAGIC - Table C keeps BARMM copies and reports missing original-row provenance.
# MAGIC - Boundaries require identifiers, feature lineage, and geometry but perform no
# MAGIC   spatial assignment.
# MAGIC - MGB ratings, geometry, and documented reference counts are checked without place
# MAGIC   mapping.

# COMMAND ----------

for source_name in config.SOURCE_ORDER:
    source = config.source_config(source_name)
    table = source["table"]
    full_name = bronze.table_name(table)
    if not spark.catalog.tableExists(full_name):
        result(
            table,
            "table",
            "required table exists",
            "stop",
            None,
            None,
            "Table is missing",
        )
        continue

    frame = spark.table(full_name)
    metrics = []
    add_metric(
        metrics, "rows", "table", "has at least one row", "stop", F.count(F.lit(1))
    )
    add_metric(
        metrics,
        "snapshot_count",
        "_source_snapshot_id",
        "contains exactly one selected snapshot",
        "stop",
        F.countDistinct(F.col("_source_snapshot_id")),
        1,
    )
    add_metric(
        metrics,
        "snapshot_value",
        "_source_snapshot_id",
        "snapshot matches latest successful load",
        "stop",
        F.first(F.col("_source_snapshot_id"), ignorenulls=True),
    )
    for index, metadata_column in enumerate(config.INGEST_METADATA_COLUMNS):
        if metadata_column not in frame.columns:
            missing_column(table, metadata_column, [metadata_column], "stop")
            continue
        add_metric(
            metrics,
            f"metadata_null_{index}",
            metadata_column,
            "ingestion metadata is not null",
            "stop",
            count_if(F.col(metadata_column).isNull()),
        )

    for label, candidates in source.get("required_column_groups", {}).items():
        if not find_column(frame, candidates):
            missing_column(table, label, candidates, "stop")

    key = find_column(frame, source.get("key_candidates", ()))
    if source.get("key_candidates"):
        if key:
            add_metric(
                metrics,
                "key_null",
                key,
                "source key is not null",
                "stop",
                count_if(F.col(key).isNull()),
            )
            add_metric(
                metrics,
                "key_duplicate",
                key,
                "source-grain key is unique",
                "flag",
                (F.count(F.lit(1)) - F.countDistinct(F.col(key))).cast("long"),
            )
        else:
            missing_column(table, "source key", source["key_candidates"], "stop")

    if source_name == "dpwh_projects":
        status_column = find_column(frame, ["status", "project_status"])
        if status_column:
            known = [
                "completed",
                "on-going",
                "ongoing",
                "not yet started",
                "for procurement",
                "terminated",
            ]
            add_metric(
                metrics,
                "unknown_status",
                status_column,
                "status is a documented category",
                "flag",
                count_if(
                    F.col(status_column).isNull()
                    | ~F.lower(F.trim(F.col(status_column))).isin(*known)
                ),
            )
        for metric_key, candidates, data_type in (
            ("invalid_budget", ["budget", "project_cost"], "DECIMAL(38, 6)"),
            ("invalid_progress", ["progress", "accomplishment"], "DOUBLE"),
            ("invalid_amount_paid", ["amountPaid", "amount_paid"], "DECIMAL(38, 6)"),
            ("invalid_start_date", ["startDate", "start_date"], "DATE"),
            ("invalid_completion_date", ["completionDate", "completion_date"], "DATE"),
        ):
            column = find_column(frame, candidates)
            if column:
                add_metric(
                    metrics,
                    metric_key,
                    column,
                    f"values cast to {data_type}",
                    "flag",
                    count_if(invalid_cast(column, data_type)),
                )

        budget = find_column(frame, ["budget", "project_cost", "projectCost"])
        if budget:
            parsed_budget = F.expr(f"TRY_CAST({q(budget)} AS DECIMAL(38, 6))")
            add_metric(
                metrics,
                "negative_budget",
                budget,
                "reported budget is non-negative when present",
                "flag",
                count_if(parsed_budget < 0),
            )

        progress = find_column(
            frame, ["progress", "physical_progress_pct", "accomplishment"]
        )
        if progress:
            parsed_progress = F.expr(f"TRY_CAST({q(progress)} AS DOUBLE)")
            add_metric(
                metrics,
                "progress_range",
                progress,
                "physical progress is between 0 and 100 when present",
                "flag",
                count_if((parsed_progress < 0) | (parsed_progress > 100)),
            )

        latitude = find_column(frame, ["latitude", "Latitude"])
        longitude = find_column(frame, ["longitude", "Longitude"])
        if latitude and longitude:
            parsed_latitude = F.expr(f"TRY_CAST({q(latitude)} AS DOUBLE)")
            parsed_longitude = F.expr(f"TRY_CAST({q(longitude)} AS DOUBLE)")
            add_metric(
                metrics,
                "coordinate_missing",
                f"{latitude}, {longitude}",
                "project coordinate pair is present",
                "flag",
                count_if(F.col(latitude).isNull() | F.col(longitude).isNull()),
            )
            add_metric(
                metrics,
                "coordinate_range",
                f"{latitude}, {longitude}",
                "project coordinates fall in the Philippines screening box",
                "flag",
                count_if(
                    parsed_latitude.isNotNull()
                    & parsed_longitude.isNotNull()
                    & (
                        (parsed_latitude < config.PH_LAT[0])
                        | (parsed_latitude > config.PH_LAT[1])
                        | (parsed_longitude < config.PH_LON[0])
                        | (parsed_longitude > config.PH_LON[1])
                    )
                ),
            )

    elif source_name == "flood_control_projects":
        contract = find_column(frame, ["ContractID", "contract_id", "contractId"])
        if contract:
            add_metric(
                metrics,
                "contract_null",
                contract,
                "Contract ID is not null",
                "stop",
                count_if(F.col(contract).isNull()),
            )
            add_metric(
                metrics,
                "repeated_contract",
                contract,
                "repeated Contract IDs are preserved for Silver review",
                "flag",
                (F.count(F.lit(1)) - F.countDistinct(F.col(contract))).cast("long"),
            )
        else:
            missing_column(
                table,
                "Contract ID",
                ["ContractID", "contract_id", "contractId"],
                "stop",
            )
        cost = find_column(frame, ["ContractCost", "contract_cost"])
        if cost:
            add_metric(
                metrics,
                "invalid_cost",
                cost,
                "contract cost casts to a number",
                "flag",
                count_if(invalid_cast(cost, "DECIMAL(38, 6)")),
            )
            parsed_cost = F.expr(f"TRY_CAST({q(cost)} AS DECIMAL(38, 6))")
            add_metric(
                metrics,
                "negative_cost",
                cost,
                "contract cost is non-negative when present",
                "flag",
                count_if(parsed_cost < 0),
            )

        latitude = find_column(frame, ["Latitude", "latitude"])
        longitude = find_column(frame, ["Longitude", "longitude"])
        if latitude and longitude:
            parsed_latitude = F.expr(f"TRY_CAST({q(latitude)} AS DOUBLE)")
            parsed_longitude = F.expr(f"TRY_CAST({q(longitude)} AS DOUBLE)")
            add_metric(
                metrics,
                "coordinate_range",
                f"{latitude}, {longitude}",
                "flood-control coordinates fall in the Philippines screening box",
                "flag",
                count_if(
                    parsed_latitude.isNotNull()
                    & parsed_longitude.isNotNull()
                    & (
                        (parsed_latitude < config.PH_LAT[0])
                        | (parsed_latitude > config.PH_LAT[1])
                        | (parsed_longitude < config.PH_LON[0])
                        | (parsed_longitude > config.PH_LON[1])
                    )
                ),
            )

    elif source_name == "psgc":
        population = find_column(
            frame, ["population_2024_parsed", "population_2024", "population"]
        )
        if population:
            add_metric(
                metrics,
                "invalid_population",
                population,
                "population casts to a whole number",
                "flag",
                count_if(invalid_cast(population, "BIGINT")),
            )

    elif source_name == "census_2024_table_c":
        lineage = [
            find_column(frame, [name])
            for name in ("source_file", "sheet_name", "source_row_number")
        ]
        if all(lineage):
            add_metric(
                metrics,
                "lineage_duplicate",
                ", ".join(lineage),
                "source file/sheet/row lineage is unique",
                "stop",
                (
                    F.count(F.lit(1))
                    - F.countDistinct(F.struct(*[F.col(name) for name in lineage]))
                ).cast("long"),
            )
        else:
            result(
                table,
                "source_file, sheet_name, source_row_number",
                "original Table C row provenance is available",
                "stop",
                1,
                1,
                "Missing exact lineage fields; the loader deliberately does not fabricate them.",
            )
        population = find_column(
            frame,
            ["population_parsed", "population_2024", "population", "total_population"],
        )
        if population:
            add_metric(
                metrics,
                "invalid_population",
                population,
                "population casts to a whole number",
                "flag",
                count_if(invalid_cast(population, "BIGINT")),
            )
            parsed_population = F.expr(f"TRY_CAST({q(population)} AS BIGINT)")
            add_metric(
                metrics,
                "nonpositive_population",
                population,
                "population is positive when present",
                "flag",
                count_if(parsed_population <= 0),
            )
        duplicate_flag = find_column(
            frame, ["is_known_duplicate_sheet", "is_known_barmm_duplicate"]
        )
        if duplicate_flag:
            duplicate_condition = F.lower(F.trim(F.col(duplicate_flag))).isin(
                "true", "1", "yes", "y"
            )
            add_metric(
                metrics,
                "known_barmm_rows",
                duplicate_flag,
                "known BARMM duplicate rows are preserved",
                "flag",
                F.abs(
                    count_if(duplicate_condition) - F.lit(config.TABLE_C_DUPLICATE_ROWS)
                ).cast("long"),
                config.TABLE_C_DUPLICATE_ROWS,
            )
        else:
            result(
                table,
                "is_known_duplicate_sheet",
                "known BARMM duplicates can be identified",
                "flag",
                1,
                1,
                "Current CSV does not expose a documented duplicate-sheet marker.",
            )

    elif source_name == "boundaries":
        lineage = [
            find_column(frame, ["source_file"]),
            find_column(frame, ["source_feature_id", "source_feature_index"]),
        ]
        if all(lineage):
            add_metric(
                metrics,
                "boundary_lineage_duplicate",
                ", ".join(lineage),
                "source file/feature lineage is unique",
                "flag",
                (
                    F.count(F.lit(1))
                    - F.countDistinct(F.struct(*[F.col(name) for name in lineage]))
                ).cast("long"),
            )
        else:
            result(
                table,
                "source_file, source_feature_id/source_feature_index",
                "original seven-file feature provenance is available",
                "flag",
                1,
                1,
                "Combined CSV provenance is incomplete unless both fields are supplied.",
            )
        geometry_candidates = source["required_column_groups"]["geometry"]
        geometry = find_column(frame, geometry_candidates)
        if geometry:
            add_metric(
                metrics,
                "geometry_null",
                geometry,
                "geometry representation is not null or empty",
                "stop",
                count_if(F.col(geometry).isNull() | (F.trim(F.col(geometry)) == "")),
            )
        else:
            missing_column(table, "geometry", geometry_candidates, "stop")

    elif source_name == "flood_susceptibility":
        rating_candidates = source["required_column_groups"]["susceptibility rating"]
        rating = find_column(frame, rating_candidates)
        if rating:
            allowed = ["very high", "high", "moderate", "low"]
            code_map = source["rating_code_map"]
            missing_values = [
                value.casefold() for value in source.get("missing_rating_values", [])
            ]
            code_map_expression = F.create_map(
                *[
                    item
                    for code, label in code_map.items()
                    for item in (F.lit(code), F.lit(label))
                ]
            )
            raw_rating = F.trim(F.col(rating))
            normalized = F.coalesce(
                code_map_expression[F.upper(raw_rating)],
                F.lower(raw_rating),
            )
            is_missing_rating = (
                F.col(rating).isNull()
                | (raw_rating == "")
                | F.lower(raw_rating).isin(*missing_values)
            )
            add_metric(
                metrics,
                "unknown_rating",
                rating,
                "rating is a recognized severity or documented missing value",
                "flag",
                count_if(~is_missing_rating & ~normalized.isin(*allowed)),
            )
            for index, category in enumerate(allowed):
                expected = source["rating_reference"][category]
                add_metric(
                    metrics,
                    f"rating_{index}",
                    rating,
                    f"{category} row count matches documented reference",
                    "flag",
                    F.abs(count_if(normalized == category) - F.lit(expected)).cast(
                        "long"
                    ),
                    details=(
                        f"Documented reference count: {expected}. "
                        "Percentage uses the full snapshot row count."
                    ),
                )
            expected_missing = source["rating_reference"]["missing"]
            add_metric(
                metrics,
                "rating_missing",
                rating,
                "missing or unrated row count matches documented reference",
                "flag",
                F.abs(count_if(is_missing_rating) - F.lit(expected_missing)).cast(
                    "long"
                ),
                details=(
                    f"Documented missing or unrated reference count: "
                    f"{expected_missing}. Percentage uses the full snapshot row count."
                ),
            )
        else:
            missing_column(table, "susceptibility rating", rating_candidates, "stop")

        geometry_candidates = source["required_column_groups"]["geometry"]
        geometry = find_column(frame, geometry_candidates)
        if geometry:
            add_metric(
                metrics,
                "geometry_null",
                geometry,
                "flood-area geometry is not null or empty",
                "flag",
                count_if(F.col(geometry).isNull() | (F.trim(F.col(geometry)) == "")),
            )
        else:
            missing_column(table, "geometry", geometry_candidates, "stop")

    try:
        observed = frame.agg(*[item[4] for item in metrics]).first()
    except Exception as error:  # noqa: BLE001 - save a blocking validation result
        result(
            table,
            "table",
            "table checks execute",
            "stop",
            None,
            None,
            str(error)[:1_000],
        )
        continue

    total_rows = int(observed["rows"])
    snapshot_value = observed["snapshot_value"]
    result(
        table,
        "table",
        "has at least one row",
        "stop",
        0 if total_rows > 0 else 1,
        1,
        snapshot_id=snapshot_value,
    )
    result(
        table,
        "_source_snapshot_id",
        "contains exactly one selected snapshot",
        "stop",
        abs(int(observed["snapshot_count"]) - 1),
        1,
        snapshot_id=snapshot_value,
    )
    for key_name, column, name, action, _, expected_total, details in metrics:
        if key_name in {"rows", "snapshot_count", "snapshot_value"}:
            continue
        result(
            table,
            column,
            name,
            action,
            observed[key_name],
            expected_total if expected_total is not None else total_rows,
            details,
            snapshot_value,
        )

    reference_rows = source.get("reference_rows")
    if reference_rows is not None:
        result(
            table,
            "row count",
            "row count matches documented historical reference",
            "flag",
            abs(total_rows - reference_rows),
            reference_rows,
            "Reference mismatch is reviewed; Bronze rows are not removed or added.",
            snapshot_value,
        )

    audit = latest_logs.get(table)
    if audit is None:
        result(
            table,
            "load_log",
            "latest load is SUCCESS or SKIPPED_IDEMPOTENT",
            "stop",
            None,
            None,
            "No terminal audit row",
            snapshot_value,
        )
    else:
        load_ok = audit["status"] in {"SUCCESS", "SKIPPED_IDEMPOTENT"}
        result(
            table,
            "load_log.status",
            "latest load is SUCCESS or SKIPPED_IDEMPOTENT",
            "stop",
            0 if load_ok else 1,
            1,
            f"latest status={audit['status']}",
            snapshot_value,
        )
        if not load_ok or audit["rows_loaded"] is None:
            continue
        result(
            table,
            "load_log.rows_loaded",
            "current Bronze row count matches load_log",
            "stop",
            abs(total_rows - int(audit["rows_loaded"])),
            int(audit["rows_loaded"]),
            snapshot_id=snapshot_value,
        )
        result(
            table,
            "load_log.snapshot_id",
            "current Bronze snapshot matches load_log",
            "stop",
            0 if snapshot_value == audit["snapshot_id"] else 1,
            1,
            f"load_log snapshot={audit['snapshot_id']!r}",
            snapshot_value,
        )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 — Store the validation evidence and enforce the gate
# MAGIC
# MAGIC One row is appended to `04-validation.dq_results` for each check. `PASS` and `FLAG`
# MAGIC remain visible for review; `FAIL` on a stop rule and any `ERROR` produce a blocking
# MAGIC exception after the complete result set is saved.

# COMMAND ----------

columns = (
    "run_id string, table_name string, column string, data_quality_check string, "
    "failed_rows long, total_rows long, percentage double, status string, action string, "
    "details string, snapshot_id string"
)
output = spark.createDataFrame(results, columns).withColumn(
    "run_ts", F.current_timestamp()
)
output.write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable(
    bronze.table_name("dq_results", config.VALIDATION)
)
display(output.orderBy("table_name", "action", "data_quality_check"))

blocked = [
    row
    for row in results
    if row[7] == "ERROR" or (row[8] == "stop" and row[7] == "FAIL")
]
if blocked:
    raise RuntimeError(
        f"{len(blocked)} checks blocked the run: "
        + "; ".join(f"{row[1]} / {row[3]} ({row[7]})" for row in blocked)
    )
print(
    f"Validation {validation_run_id}: no blocking check failed; review FLAG rows before Silver."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC The validation layer separates pipeline safety from known source imperfections. It
# MAGIC protects raw preservation, snapshot lineage, source grain, and source-to-Bronze row
# MAGIC reconciliation while leaving all business transformations to Silver.

# COMMAND ----------

# MAGIC %sql
# MAGIC
# MAGIC SELECT
# MAGIC   COALESCE(
# MAGIC     NULLIF(TRIM(flood_susceptibility_code), ''),
# MAGIC     '<BLANK>'
# MAGIC   ) AS raw_rating,
# MAGIC   CASE
# MAGIC     WHEN geometry_json IS NULL OR TRIM(geometry_json) = ''
# MAGIC       THEN 'BLANK_GEOMETRY'
# MAGIC     ELSE 'HAS_GEOMETRY'
# MAGIC   END AS geometry_status,
# MAGIC   COUNT(*) AS row_count
# MAGIC FROM `buildabida-capstone`.`01-bronze`.flood_susceptibility
# MAGIC WHERE _source_snapshot_id = 'metadata-17bf5e65e1838a2f7be9'
# MAGIC GROUP BY 1, 2
# MAGIC ORDER BY 1, 2;