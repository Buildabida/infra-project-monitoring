-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Set up and verify the workspace
-- MAGIC
-- MAGIC This notebook is safe to rerun. It creates missing catalog schemas but does not
-- MAGIC create or replace the externally configured `cloudflare-r2` volume. The final
-- MAGIC statement fails clearly when that required volume is unavailable.

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

-- validate the existing external volume; do not create or replace it here
DESCRIBE VOLUME `buildabida-capstone`.`00-source`.`cloudflare-r2`;
