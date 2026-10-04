# Optional Bronze cleanup plan

Do not run cleanup until all six R2 loaders pass in Databricks.
Bronze validation must also pass.
Check downstream dependencies before removing any object.
The team must approve every cleanup action manually.

Setup and orchestration never run these commands.

| Object | Why it may be obsolete | Dependency check | Manual example |
| --- | --- | --- | --- |
| `01-bronze.population_2024` | Table C is authoritative. PSGC population stays in `psgc` as a cross-check. | Search Silver, Gold, validation, dashboards, and queries for references. | `DROP TABLE IF EXISTS \`buildabida-capstone\`.\`01-bronze\`.population_2024` |
| `01-bronze.psgc_sheet_manifest` | The R2 input is CSV. The current batch does not parse the original workbook. | Preserve it when needed as historical evidence. Check all downstream references. | `DROP TABLE IF EXISTS \`buildabida-capstone\`.\`01-bronze\`.psgc_sheet_manifest` |
| `01-bronze.psgc_parse_issues` | This object belongs to the earlier workbook process. | Check audit and report dependencies. Preserve required evidence outside the table. | `DROP TABLE IF EXISTS \`buildabida-capstone\`.\`01-bronze\`.psgc_parse_issues` |
| `01-bronze.census_2024_table_c_sheet_manifest` | The current R2 file is one combined CSV. It does not use 18 workbooks. | Preserve it until the team accepts and documents the CSV provenance limits. | `DROP TABLE IF EXISTS \`buildabida-capstone\`.\`01-bronze\`.census_2024_table_c_sheet_manifest` |
| `01-bronze.census_2024_table_c_parse_issues` | This object belongs to the earlier workbook process. | Check audit dependencies. Retain required historical evidence outside the table. | `DROP TABLE IF EXISTS \`buildabida-capstone\`.\`01-bronze\`.census_2024_table_c_parse_issues` |
| `00-source.landing` | The legacy managed volume was retired. The new batch uses `cloudflare-r2`. | Confirm it is unused. Confirm it does not hold the only source or audit copy. | `DROP VOLUME IF EXISTS \`buildabida-capstone\`.\`00-source\`.landing` |

Before approval, run read-only dependency searches.
Export or back up any required data.
Delta time travel does not replace required external raw-source history.
