# Implementation notes

This refactor was completed from repository evidence and the supplied R2 inventory.
The local environment had no Databricks/Spark connection, and the authenticated
Databricks tab was not available to inspect through the browser integration.

Therefore these items remain unverified until Databricks execution:

- actual CSV headers and delimiters;
- source byte sizes and modification timestamps returned inside Databricks;
- exact row counts for all six current R2 files;
- the historical Table C, boundary and MGB reference counts against current files;
- Delta schema evolution from the pre-refactor `load_log` and `dq_results` tables;
- serverless runtime support for the PySpark `Observation` used to count source rows
  during the write.

The loader does not fabricate missing provenance. Full Table C reproducibility needs
`source_file`, `sheet_name`, `source_row_number` and the known duplicate-sheet marker.
Full boundary reproducibility needs the original seven-file name and feature index.
Derived DPWH, flood-control and PSGC CSVs need documented export commands and source
versions before anyone describes them as lossless.
