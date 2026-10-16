-- Databricks notebook source
-- MAGIC %md
-- MAGIC # D-57 province-reporting acceptance evidence
-- MAGIC
-- MAGIC Run this notebook after `03b_validation_silver_province_reporting`,
-- MAGIC `09a_validation_gold_province_reporting`, and `10_validation_analytics`.
-- MAGIC It publishes the latest blocking-check evidence, project and budget coverage,
-- MAGIC mapping-method totals, special-geography totals, population coverage, selected
-- MAGIC versions, and a repeatable mapping-identity capture.
-- MAGIC
-- MAGIC For exact-rerun evidence, run this notebook once, rerun
-- MAGIC `08c_silver_project_province_map` and
-- MAGIC `03b_validation_silver_province_reporting` without changing any inputs, then
-- MAGIC run this notebook again. The final comparison must show `PASS`.

-- COMMAND ----------

USE CATALOG `buildabida-capstone`;

CREATE SCHEMA IF NOT EXISTS `04-validation`;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Latest D-57 validation results

-- COMMAND ----------

CREATE OR REPLACE TABLE
    `04-validation`.province_reporting_acceptance_evidence
USING DELTA
COMMENT 'Latest Silver, Gold, and Analytics blocking-check evidence for D-57 province reporting.'
AS
WITH combined_evidence AS (
    SELECT
        validation_run_id,
        pipeline_run_id,
        layer,
        table_name,
        source_snapshot_id,
        rule_version,
        data_quality_attribute,
        data_quality_check,
        failed_rows,
        total_rows,
        percentage,
        status,
        action,
        details,
        run_ts
    FROM `04-validation`.silver_dq_results
    WHERE rule_version = 'silver-province-reporting-validation-v2'

    UNION ALL

    SELECT
        validation_run_id,
        pipeline_run_id,
        layer,
        table_name,
        source_snapshot_id,
        rule_version,
        data_quality_attribute,
        data_quality_check,
        failed_rows,
        total_rows,
        percentage,
        status,
        action,
        details,
        run_ts
    FROM `04-validation`.gold_dq_results
    WHERE rule_version = 'gold-province-reporting-validation-v2'

    UNION ALL

    SELECT
        validation_run_id,
        pipeline_run_id,
        layer,
        table_name,
        source_snapshot_id,
        rule_version,
        data_quality_attribute,
        data_quality_check,
        failed_rows,
        total_rows,
        percentage,
        status,
        action,
        details,
        run_ts
    FROM `04-validation`.analytics_dq_results
    WHERE rule_version = 'analytics-validation-v4'
),
ranked_evidence AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY layer, table_name, data_quality_check
            ORDER BY run_ts DESC, validation_run_id DESC
        ) AS evidence_rank
    FROM combined_evidence
)
SELECT
    validation_run_id,
    pipeline_run_id,
    layer,
    table_name,
    source_snapshot_id,
    rule_version,
    data_quality_attribute,
    data_quality_check,
    failed_rows,
    total_rows,
    percentage,
    status,
    action,
    details,
    run_ts
FROM ranked_evidence
WHERE evidence_rank = 1;

-- COMMAND ----------

SELECT ASSERT_TRUE(
    COUNT(*) > 0
    AND COUNT(DISTINCT layer) = 3
    AND COUNT_IF(action = 'stop' AND status = 'FAIL') = 0,
    CONCAT(
        'D-57 acceptance failed: ',
        COUNT_IF(action = 'stop' AND status = 'FAIL'),
        ' blocking failures across ',
        COUNT(DISTINCT layer),
        ' validation layers'
    )
)
FROM `04-validation`.province_reporting_acceptance_evidence;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Current coverage and deterministic mapping identity

-- COMMAND ----------

CREATE OR REPLACE TEMPORARY VIEW province_reporting_current_acceptance_metrics AS
WITH project_metrics AS (
    SELECT
        MAX(map.project_source_snapshot_id) AS source_snapshot_id,
        MAX(map.run_id) AS project_map_run_id,
        MAX(map.mapping_rule_version) AS mapping_rule_version,
        MAX(map.mapping_config_version) AS mapping_config_version,
        MAX(map.psgc_version) AS psgc_version,
        MAX(map.boundary_version) AS boundary_version,
        COUNT(*) AS total_projects,
        COUNT_IF(map.reporting_area_key <> 0) AS mapped_projects,
        COUNT_IF(map.reporting_area_key = 0) AS unmapped_projects,
        SUM(project.reported_budget_pesos) AS total_reported_budget_pesos,
        SUM(
            CASE
                WHEN map.reporting_area_key <> 0 THEN project.reported_budget_pesos
            END
        ) AS mapped_reported_budget_pesos,
        SUM(
            CASE
                WHEN map.reporting_area_key = 0 THEN project.reported_budget_pesos
            END
        ) AS unmapped_reported_budget_pesos,
        COUNT_IF(map.coordinate_status <> 'VALID_PAIR') AS missing_coordinate_projects,
        COUNT_IF(
            map.coordinate_status = 'VALID_PAIR'
            AND map.spatial_candidate_count = 0
        ) AS zero_spatial_candidate_projects,
        COUNT_IF(map.spatial_candidate_count > 1) AS multiple_spatial_candidate_projects,
        COUNT_IF(map.conflict_flag) AS conflict_projects,
        COUNT_IF(map.reporting_area_type = 'NCR') AS ncr_projects,
        SUM(
            CASE
                WHEN map.reporting_area_type = 'NCR' THEN project.reported_budget_pesos
            END
        ) AS ncr_reported_budget_pesos,
        COUNT_IF(map.reporting_area_type = 'INDEPENDENT_CITY') AS independent_city_projects,
        SUM(
            CASE
                WHEN map.reporting_area_type = 'INDEPENDENT_CITY'
                    THEN project.reported_budget_pesos
            END
        ) AS independent_city_reported_budget_pesos,
        COUNT_IF(map.parent_region_code = '1900000000') AS barmm_projects,
        SUM(
            CASE
                WHEN map.parent_region_code = '1900000000'
                    THEN project.reported_budget_pesos
            END
        ) AS barmm_reported_budget_pesos,
        BIT_XOR(XXHASH64(CONCAT_WS(
            '||',
            CAST(map.project_key AS STRING),
            CAST(map.project_province_map_key AS STRING),
            CAST(map.reporting_area_key AS STRING),
            map.mapping_method,
            map.match_status,
            map.run_id
        ))) AS mapping_identity_checksum
    FROM `02-silver`.silver_project_province_map AS map
    INNER JOIN `02-silver`.silver_project AS project
        ON map.project_key = project.project_key
),
population_metrics AS (
    SELECT
        MAX(reference_year) AS population_reference_year,
        SUM(population_count) AS accepted_population,
        SUM(
            CASE
                WHEN reporting_area_key = 0 THEN population_count
            END
        ) AS unresolved_accepted_population,
        MAX(excluded_population_count) AS excluded_population,
        COUNT_IF(reporting_area_key <> 0 AND population_count IS NOT NULL)
            AS populated_reporting_areas,
        COUNT_IF(reporting_area_key <> 0 AND population_count IS NULL)
            AS missing_population_reporting_areas,
        COUNT_IF(reporting_area_key <> 0) AS geographic_reporting_areas
    FROM `02-silver`.silver_province_reporting_area_population
),
boundary_metrics AS (
    SELECT
        COUNT_IF(boundary_status = 'VALID_BOUNDARY') AS valid_boundary_areas,
        COUNT_IF(boundary_status = 'MISSING_BOUNDARY') AS missing_boundary_areas,
        COUNT_IF(boundary_status = 'AMBIGUOUS_BOUNDARY') AS ambiguous_boundary_areas,
        COUNT_IF(boundary_status = 'INVALID_BOUNDARY') AS invalid_boundary_areas
    FROM `02-silver`.silver_province_reporting_area_boundary
)
SELECT
    project.source_snapshot_id,
    project.project_map_run_id,
    project.mapping_rule_version,
    project.mapping_config_version,
    SPLIT_PART(project.mapping_config_version, '|', 1) AS alias_version,
    SPLIT_PART(project.mapping_config_version, '|', 2) AS manual_mapping_version,
    project.psgc_version,
    project.boundary_version,
    project.total_projects,
    project.mapped_projects,
    project.unmapped_projects,
    ROUND(
        100.0 * project.mapped_projects / NULLIF(project.total_projects, 0),
        4
    ) AS mapped_project_percentage,
    project.total_reported_budget_pesos,
    project.mapped_reported_budget_pesos,
    project.unmapped_reported_budget_pesos,
    ROUND(
        100.0 * project.mapped_reported_budget_pesos
            / NULLIF(project.total_reported_budget_pesos, 0),
        4
    ) AS mapped_budget_percentage,
    project.missing_coordinate_projects,
    project.zero_spatial_candidate_projects,
    project.multiple_spatial_candidate_projects,
    project.conflict_projects,
    project.ncr_projects,
    project.ncr_reported_budget_pesos,
    project.independent_city_projects,
    project.independent_city_reported_budget_pesos,
    project.barmm_projects,
    project.barmm_reported_budget_pesos,
    population.population_reference_year,
    population.accepted_population,
    population.unresolved_accepted_population,
    population.excluded_population,
    population.populated_reporting_areas,
    population.missing_population_reporting_areas,
    ROUND(
        100.0 * population.populated_reporting_areas
            / NULLIF(population.geographic_reporting_areas, 0),
        4
    ) AS population_area_coverage_percentage,
    boundary.valid_boundary_areas,
    boundary.missing_boundary_areas,
    boundary.ambiguous_boundary_areas,
    boundary.invalid_boundary_areas,
    project.mapping_identity_checksum
FROM project_metrics AS project
CROSS JOIN population_metrics AS population
CROSS JOIN boundary_metrics AS boundary;

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS
    `04-validation`.province_reporting_acceptance_runs (
        capture_id STRING NOT NULL,
        captured_at TIMESTAMP NOT NULL,
        source_snapshot_id STRING NOT NULL,
        project_map_run_id STRING NOT NULL,
        mapping_rule_version STRING NOT NULL,
        mapping_config_version STRING NOT NULL,
        alias_version STRING NOT NULL,
        manual_mapping_version STRING NOT NULL,
        psgc_version STRING,
        boundary_version STRING,
        total_projects BIGINT NOT NULL,
        mapped_projects BIGINT NOT NULL,
        unmapped_projects BIGINT NOT NULL,
        mapped_project_percentage DOUBLE,
        total_reported_budget_pesos DECIMAL(38, 2),
        mapped_reported_budget_pesos DECIMAL(38, 2),
        unmapped_reported_budget_pesos DECIMAL(38, 2),
        mapped_budget_percentage DOUBLE,
        missing_coordinate_projects BIGINT NOT NULL,
        zero_spatial_candidate_projects BIGINT NOT NULL,
        multiple_spatial_candidate_projects BIGINT NOT NULL,
        conflict_projects BIGINT NOT NULL,
        ncr_projects BIGINT NOT NULL,
        ncr_reported_budget_pesos DECIMAL(38, 2),
        independent_city_projects BIGINT NOT NULL,
        independent_city_reported_budget_pesos DECIMAL(38, 2),
        barmm_projects BIGINT NOT NULL,
        barmm_reported_budget_pesos DECIMAL(38, 2),
        population_reference_year INT,
        accepted_population BIGINT,
        unresolved_accepted_population BIGINT,
        excluded_population BIGINT,
        populated_reporting_areas BIGINT NOT NULL,
        missing_population_reporting_areas BIGINT NOT NULL,
        population_area_coverage_percentage DOUBLE,
        valid_boundary_areas BIGINT NOT NULL,
        missing_boundary_areas BIGINT NOT NULL,
        ambiguous_boundary_areas BIGINT NOT NULL,
        invalid_boundary_areas BIGINT NOT NULL,
        mapping_identity_checksum BIGINT
    )
USING DELTA
COMMENT 'Append-only D-57 coverage and deterministic rerun evidence captures.';

INSERT INTO `04-validation`.province_reporting_acceptance_runs
SELECT
    UUID() AS capture_id,
    CURRENT_TIMESTAMP() AS captured_at,
    metrics.*
FROM province_reporting_current_acceptance_metrics AS metrics;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Mapping methods and statuses

-- COMMAND ----------

CREATE OR REPLACE TABLE
    `04-validation`.province_reporting_acceptance_mapping_methods
USING DELTA
COMMENT 'Current D-57 project counts and budgets by governed mapping outcome.'
AS
WITH latest_capture AS (
    SELECT capture_id, captured_at
    FROM `04-validation`.province_reporting_acceptance_runs
    ORDER BY captured_at DESC, capture_id DESC
    LIMIT 1
)
SELECT
    capture.capture_id,
    capture.captured_at,
    map.mapping_method,
    map.match_status,
    map.match_quality,
    map.reporting_area_type,
    COUNT(*) AS projects,
    COUNT_IF(project.reported_budget_pesos IS NOT NULL) AS projects_with_budget,
    SUM(project.reported_budget_pesos) AS reported_budget_pesos
FROM `02-silver`.silver_project_province_map AS map
INNER JOIN `02-silver`.silver_project AS project
    ON map.project_key = project.project_key
CROSS JOIN latest_capture AS capture
GROUP BY
    capture.capture_id,
    capture.captured_at,
    map.mapping_method,
    map.match_status,
    map.match_quality,
    map.reporting_area_type;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Evidence outputs

-- COMMAND ----------

SELECT
    layer,
    COUNT(*) AS total_checks,
    COUNT_IF(status = 'PASS') AS passed_checks,
    COUNT_IF(status = 'FLAG') AS flagged_checks,
    COUNT_IF(status = 'FAIL') AS failed_checks,
    MAX(run_ts) AS latest_validation_ts
FROM `04-validation`.province_reporting_acceptance_evidence
GROUP BY layer
ORDER BY CASE layer
    WHEN 'silver' THEN 1
    WHEN 'gold' THEN 2
    WHEN 'analytics' THEN 3
    ELSE 4
END;

-- COMMAND ----------

SELECT *
FROM `04-validation`.province_reporting_acceptance_runs
ORDER BY captured_at DESC, capture_id DESC
LIMIT 1;

-- COMMAND ----------

SELECT
    mapping_method,
    match_status,
    match_quality,
    reporting_area_type,
    projects,
    projects_with_budget,
    reported_budget_pesos
FROM `04-validation`.province_reporting_acceptance_mapping_methods
ORDER BY projects DESC, mapping_method, match_status, reporting_area_type;

-- COMMAND ----------

SELECT
    layer,
    table_name,
    data_quality_check,
    status,
    action,
    failed_rows,
    total_rows,
    percentage,
    details,
    validation_run_id,
    pipeline_run_id,
    source_snapshot_id,
    run_ts
FROM `04-validation`.province_reporting_acceptance_evidence
ORDER BY
    CASE layer
        WHEN 'silver' THEN 1
        WHEN 'gold' THEN 2
        WHEN 'analytics' THEN 3
        ELSE 4
    END,
    CASE status
        WHEN 'FAIL' THEN 1
        WHEN 'FLAG' THEN 2
        ELSE 3
    END,
    table_name,
    data_quality_check;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Exact-rerun comparison
-- MAGIC
-- MAGIC `RERUN_REQUIRED` is expected after the first capture. After rerunning the
-- MAGIC project map and its validator with unchanged inputs, rerun this notebook.
-- MAGIC The result must be `PASS` before claiming deterministic-rerun evidence.

-- COMMAND ----------

WITH latest_snapshot AS (
    SELECT source_snapshot_id
    FROM `04-validation`.province_reporting_acceptance_runs
    ORDER BY captured_at DESC, capture_id DESC
    LIMIT 1
),
ranked_captures AS (
    SELECT
        runs.*,
        ROW_NUMBER() OVER (
            ORDER BY captured_at DESC, capture_id DESC
        ) AS capture_rank
    FROM `04-validation`.province_reporting_acceptance_runs AS runs
    WHERE source_snapshot_id = (
        SELECT source_snapshot_id
        FROM latest_snapshot
    )
),
last_two AS (
    SELECT *
    FROM ranked_captures
    WHERE capture_rank <= 2
)
SELECT
    CASE
        WHEN COUNT(*) < 2 THEN 'RERUN_REQUIRED'
        WHEN COUNT(DISTINCT project_map_run_id) = 1
         AND COUNT(DISTINCT mapping_identity_checksum) = 1
         AND COUNT(DISTINCT mapping_rule_version) = 1
         AND COUNT(DISTINCT mapping_config_version) = 1
         AND COUNT(DISTINCT psgc_version) = 1
         AND COUNT(DISTINCT boundary_version) = 1
            THEN 'PASS'
        ELSE 'FAIL'
    END AS exact_rerun_status,
    COUNT(*) AS compared_captures,
    COUNT(DISTINCT project_map_run_id) AS distinct_project_map_run_ids,
    COUNT(DISTINCT mapping_identity_checksum) AS distinct_mapping_checksums,
    MIN(captured_at) AS earlier_capture_at,
    MAX(captured_at) AS later_capture_at,
    MAX(project_map_run_id) AS project_map_run_id,
    MAX(mapping_identity_checksum) AS mapping_identity_checksum
FROM last_two;