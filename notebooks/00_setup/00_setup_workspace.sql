-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Set up the catalog
-- MAGIC
-- MAGIC Run this once from VS Code, as a workflow. It is safe to run again. It only adds what is missing.
-- MAGIC
-- MAGIC It makes the `buildabida-capstone` catalog, one schema per step in run order, and the `00-source`.`landing` volume for files we download by hand. The names have hyphens, so SQL needs backticks around them.

-- COMMAND ----------

CREATE CATALOG IF NOT EXISTS `buildabida-capstone`;
USE CATALOG `buildabida-capstone`;

CREATE SCHEMA IF NOT EXISTS `00-source` COMMENT 'Files we download by hand, as they came';
CREATE SCHEMA IF NOT EXISTS `01-bronze` COMMENT 'Each source as it came, plus the load time';
CREATE SCHEMA IF NOT EXISTS `02-silver` COMMENT 'Cleaned data with PSGC codes';
CREATE SCHEMA IF NOT EXISTS `03-gold` COMMENT 'Facts and dimensions for the dashboard and Genie';
CREATE SCHEMA IF NOT EXISTS `04-validation` COMMENT 'Data quality results for every run';
CREATE VOLUME IF NOT EXISTS `00-source`.landing COMMENT 'Files we download by hand';

SHOW SCHEMAS;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Clean up the old names
-- MAGIC
-- MAGIC Before Sep 28 this notebook made a `buildabida` catalog with `bronze`, `silver`, `gold` and `validation`. If you ran that version, you have an extra empty catalog. Check that it is empty, then drop it. Only the person who made it can drop it.
-- MAGIC
-- MAGIC ```sql
-- MAGIC SHOW TABLES IN buildabida.bronze;
-- MAGIC DROP CATALOG buildabida CASCADE;
-- MAGIC ```
