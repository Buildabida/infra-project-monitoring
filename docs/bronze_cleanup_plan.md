# Optional Bronze cleanup plan

Do not run cleanup until the six R2 loaders and Bronze validation pass in Databricks,
downstream dependencies are checked, and the team manually approves each object.
Nothing in setup or orchestration executes these commands.

| Object | Why it may be obsolete | Dependency check needed | Manual example only |
| --- | --- | --- | --- |
| `01-bronze.population_2024` | Table C is the authoritative population table; PSGC population remains in `psgc` as a cross-check. | Search Silver, Gold, validation, dashboards and queries for references. | `DROP TABLE IF EXISTS \`buildabida-capstone\`.\`01-bronze\`.population_2024;` |
| `01-bronze.psgc_sheet_manifest` | R2 input is CSV, so the current batch does not parse the original workbook. | Preserve it if it is needed as historical evidence; check downstream references. | `DROP TABLE IF EXISTS \`buildabida-capstone\`.\`01-bronze\`.psgc_sheet_manifest;` |
| `01-bronze.psgc_parse_issues` | Same CSV migration reason. | Check audit/report dependencies and preserve prior evidence externally if required. | `DROP TABLE IF EXISTS \`buildabida-capstone\`.\`01-bronze\`.psgc_parse_issues;` |
| `01-bronze.census_2024_table_c_sheet_manifest` | Current R2 file is a combined CSV, not 18 workbooks. | Preserve it until CSV provenance limitations are accepted and documented. | `DROP TABLE IF EXISTS \`buildabida-capstone\`.\`01-bronze\`.census_2024_table_c_sheet_manifest;` |
| `01-bronze.census_2024_table_c_parse_issues` | Same CSV migration reason. | Check audit dependencies and retain historical evidence when required. | `DROP TABLE IF EXISTS \`buildabida-capstone\`.\`01-bronze\`.census_2024_table_c_parse_issues;` |
| `00-source.landing` | Deleted legacy managed volume; the new batch expects `cloudflare-r2`. | Confirm it still exists, is unused, and contains no only copy of source/audit data. | `DROP VOLUME IF EXISTS \`buildabida-capstone\`.\`00-source\`.landing;` |

Before approval, run read-only dependency searches and take any required export or
backup. Delta time travel is not a substitute for preserving externally required raw
source history.
