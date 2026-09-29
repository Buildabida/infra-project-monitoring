# Data model

> [!NOTE]
> This is a draft. The final schema is due Oct 3.

Every table lives in our `buildabida-capstone` catalog. The schemas are numbered in run order. The middle column says what one row of the table stands for.

| Table | One row is | Key |
| --- | --- | --- |
| `01-bronze.dpwh_projects` | One project, as the API returns it | `contract_id` |
| `01-bronze.flood_control_projects` | One flood control project | `contract_id` |
| `01-bronze.psgc` | One place in the PSGC list | `psgc_code` |
| `01-bronze.population_2024` | One place and its 2024 population | `psgc_code` |
| `02-silver.projects` | One project from any source, with a PSGC code | `contract_id` |
| `03-gold.dim_place` | One region, province, city or town | `psgc_code` |
| `03-gold.dim_project_type` | One project type | `project_type_id` |
| `03-gold.fact_project` | One project | `contract_id` |
| `04-validation.dq_results` | One check on one column in one run | `run_id`, `table_name`, `column_name`, `check_name` |

In `03-gold`, a fact table holds the things we count, like projects and their money. A dimension table holds the things we group by, like places and project types.

`00-source.landing` is a volume, not a table. It holds the files we download by hand, like the PSGC and census files.

The names have hyphens, so SQL needs backticks around the catalog and the schema, like `` `01-bronze`.psgc ``.
