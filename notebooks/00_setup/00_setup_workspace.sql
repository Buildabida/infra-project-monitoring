-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Set up and verify the workspace
-- MAGIC
-- MAGIC ## Purpose
-- MAGIC
-- MAGIC Define the five medallion and validation namespaces used by the project, then
-- MAGIC verify the existing Unity Catalog volume that exposes Cloudflare R2 source files.
-- MAGIC Setup is intentionally separate from ingestion: it prepares names and access but
-- MAGIC does not copy, transform, delete, or replace source data.
-- MAGIC
-- MAGIC ## Why this setup is safe
-- MAGIC
-- MAGIC - `IF NOT EXISTS` makes catalog and schema creation idempotent.
-- MAGIC - The external `cloudflare-r2` volume is described, never created or replaced here.
-- MAGIC - No `DROP`, `DELETE`, or raw-file operation is part of normal setup.
-- MAGIC - Schema comments state each layer's responsibility for beginner-readable lineage.
-- MAGIC
-- MAGIC ## Step 1 — Create only missing namespaces
-- MAGIC
-- MAGIC Bronze is the raw/as-received layer. Silver owns cleaning and geographic matching;
-- MAGIC Gold owns analytical models; Validation owns check results.

-- COMMAND ----------

CREATE CATALOG IF NOT EXISTS `buildabida-capstone`;
USE CATALOG `buildabida-capstone`;

CREATE SCHEMA IF NOT EXISTS `00-source` COMMENT 'External source files and snapshots';
CREATE SCHEMA IF NOT EXISTS `01-bronze` COMMENT 'Selected source snapshots plus ingestion metadata';
CREATE SCHEMA IF NOT EXISTS `02-silver` COMMENT 'Cleaned data with PSGC codes';
CREATE SCHEMA IF NOT EXISTS `03-gold` COMMENT 'Facts and dimensions for the dashboard and Genie';
CREATE SCHEMA IF NOT EXISTS `04-validation` COMMENT 'Data quality results for every run';

SHOW SCHEMAS;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 2 — Verify the existing R2-backed volume
-- MAGIC
-- MAGIC `DESCRIBE VOLUME` checks that Unity Catalog can resolve the approved source volume.
-- MAGIC Keeping volume provisioning outside this notebook prevents accidental replacement
-- MAGIC of the durable source boundary.

-- COMMAND ----------

-- Verify access only; ownership and provisioning stay outside the Bronze batch.
DESCRIBE VOLUME `buildabida-capstone`.`00-source`.`cloudflare-r2`;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Summary
-- MAGIC
-- MAGIC The workspace contract is five clearly separated schemas plus one existing
-- MAGIC R2-backed source volume. The setup is repeatable and non-destructive.
