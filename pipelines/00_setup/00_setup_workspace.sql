-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Set up the catalog
-- MAGIC
-- MAGIC Run this once in your own workspace. It is safe to run again.
-- MAGIC
-- MAGIC It makes the `buildabida` catalog, the `bronze`, `silver`, `gold` and `validation` schemas, and the `bronze.landing` volume for files we download by hand.

-- COMMAND ----------

CREATE CATALOG IF NOT EXISTS buildabida;
USE CATALOG buildabida;

CREATE SCHEMA IF NOT EXISTS bronze COMMENT 'Each source as it came, plus the load time';
CREATE SCHEMA IF NOT EXISTS silver COMMENT 'Cleaned data with PSGC codes';
CREATE SCHEMA IF NOT EXISTS gold COMMENT 'Facts and dimensions for the dashboard and Genie';
CREATE SCHEMA IF NOT EXISTS validation COMMENT 'Data quality results for every run';
CREATE VOLUME IF NOT EXISTS bronze.landing COMMENT 'Files we download by hand';

SHOW SCHEMAS;
