# Data model

> [!NOTE]
> This is a draft. The final schema is due Oct 3.

Every table lives in our `buildabida-capstone` catalog. The schemas are numbered in run order. The middle column says what one row of the table stands for.

| Table | One row is | Key |
| --- | --- | --- |
| `01-bronze.dpwh_projects` | One project, with every field as the API sent it | `contractId` |
| `01-bronze.flood_control_projects` | One feature of the flood control map layer, with `attributes` and `geometry` as the layer sent them. 109 contracts have more than one row ([D-19](decisions.md)). | `attributes.ObjectId` |
| `01-bronze.psgc` | One place in the PSGC 2Q 2026 file | `psgc_code_parsed` |
| `01-bronze.population_2024` | One place and its 2024 count from the PSGC file. We use it to check census Table C ([D-18](decisions.md)). | `psgc_code_parsed` |
| `01-bronze.census_2024_table_b` | One row of census Table B: a region, province, city or town, with its counts from 2010 to 2024. Optional, for growth. | `source_file`, `sheet_name`, `source_row_number` |
| `01-bronze.census_2024_table_c` | One row of census Table C: a province, city, town or barangay, with its 2024 count. Our population source ([D-18](decisions.md)). | `source_file`, `sheet_name`, `source_row_number` |
| `01-bronze.boundaries` | One map feature of a region, province, city, town or barangay, kept whole as GeoJSON text. Some places have 2 or more shapes, so a PSGC code can repeat. | `source_file`, `source_feature_index` |
| `01-bronze.<table>_sheet_manifest` | One sheet of an Excel file, with how its rows were sorted. There is one for `psgc`, `census_2024_table_b` and `census_2024_table_c`. | `source_file`, `sheet_name` |
| `01-bronze.<table>_parse_issues` | One Excel row the load could not read, with its cells and the reason. It should be empty. | `source_file`, `sheet_name`, `source_row_number` |
| `01-bronze.load_log` | One load of one bronze table: the rows the source reports and the rows we loaded. It also lists the raw files with their sizes and SHA-256 fingerprints. | `run_id`, `table_name` |
| `02-silver.projects` | One project from any source, with a PSGC code | `contract_id` |
| `03-gold.dim_place` | One region, province, city or town | `psgc_code` |
| `03-gold.dim_project_type` | One project type | `project_type_id` |
| `03-gold.fact_project` | One project | `contract_id` |
| `04-validation.dq_results` | One check on one column in one run | `run_id`, `table_name`, `column`, `data_quality_check` |

In `03-gold`, a fact table holds the things we count, like projects and their money. A dimension table holds the things we group by, like places and project types.

Bronze keeps every field and value of a source as it came, with the source's own names, like `contractId`. Our snake_case names start in silver. Every bronze table also has `_ingest_run_id`, the run that loaded it, and `load_ts`, the time. The API tables also have `_raw_file` and `_source_url`. When a load turns text into a number or a code, the result goes in a `_parsed` column next to the `_raw` one.

The BARMM file of census Table C has 4 sheets that copy other sheets in it. `census_2024_table_c` keeps them and marks them in `is_known_duplicate_sheet`, and silver drops them.

`00-source.landing` is a volume, not a table. It holds the raw API replies, in a new folder for each run, and the files we download, like the PSGC and census files.

The names have hyphens, so SQL needs backticks around the catalog and the schema, like `` `01-bronze`.psgc ``.
