# Decisions

We record each major choice with an ID, date, and reason.
Old rows remain when the team changes a decision.
The team document contains the same log.
Decision IDs are stable references.
Dates record when the team agreed, so dates may not appear in ID order.

## Made

| ID | Date | Decision | Why |
| --- | --- | --- | --- |
| D-01 | Sep 28 | The team workspace runs the final pipeline and dashboard. | Nadine created a shared workspace where everyone is a user. It is not tied to one person. |
| D-02 | Sep 26 | The main question is the one in the project brief. | The brief defines the project direction. |
| D-04 | Oct 8 | Use DPWH as the canonical project and reported-budget authority. Preserve flood-control rows as source evidence and reconcile them by exact normalized Contract ID. Do not add flood-control Contract Cost to the DPWH reported budget. Keep unmatched and ambiguous records visible. | This prevents double counting while preserving source evidence and lineage. |
| D-05 | Sep 26 | The team name is Buildabida. | It fits infrastructure and sounds fun. |
| D-06 | Sep 26 | Tasks live in GitHub issues and one project board. | This keeps tasks and code in one place. |
| D-07 | Sep 28 | Tables live in the `buildabida` catalog. | This separates the capstone from earlier class work. |
| D-08 | Sep 28 | Python loads sources into Bronze. SQL owns the later layers, starting with Silver. | The team knows SQL best. Python is better for APIs, web pages, and Excel files. |
| D-09 | Sep 28 | Code lives in a new repository under the Buildabida GitHub organization. | The team owns it, and everyone has the same access. |
| D-10 | Sep 28 | Meetings happen in Gather. Files, screenshots, and links go in Drive. | Each item has one home. This avoids unnecessary tools. |
| D-11 | Sep 28 | Code is written in VS Code with the Databricks extension. The team workspace runs it. This updates D-10. | Free Edition has limits. Local tools and Git work do not consume workspace resources. |
| D-12 | Sep 28 | Repository folders are `notebooks`, `src`, `docs`, `dashboard`, `resources`, and `tests`. | Nadine and Bri know this layout. The structure helps anyone contribute quickly. |
| D-13 | Sep 28 | The catalog is `buildabida-capstone`. Schemas are numbered from `00-source` through `04-validation`. This replaces D-07. | The numbering follows run order. The names match the class and project documentation. |
| D-14 | Sep 28 | Nadine and Kinah each test all five sources independently. They compare results before using the team workspace. | Independent testing builds shared knowledge. It also preserves the team workspace quota while the data is explored. |
| D-15 | Sep 28 | Sam owns the star schema. Bri and Tricia finalize the questions. Kinah maintains the repository, board, and story. | Two people cover ingestion. Schema design can begin while the final questions are refined. |
| D-16 | Sep 28 | Work happens through chat. The team meets weekly and attends a Wednesday mentor check-in. | Most members prefer chat. Two weekly touchpoints maintain alignment. |
| D-17 | Sep 29 | Load seven boundary files and exclude the special-areas file. | Its shapes lack PSGC codes. The barangays already exist elsewhere, so including the file could double-count projects. |
| D-18 | Sep 29 | Census Table C is the population source. Table B is optional for growth. PSGC population is a cross-check. | Table C provides barangay population. Silver must match its place names to PSGC codes. |
| D-19 | Sep 29 | Bronze keeps all 9,855 flood-list rows. Rows are not removed by Contract ID. | The 157 repeated rows are not copies. Silver must prevent repeated project costs from being counted twice. |
| D-20 | Sep 29 | Checks remain simple Bronze load checks until Silver. | Current work focuses on Bronze. Results still go to `04-validation.dq_results`. |
| D-22 | Sep 29 | Load five sources into separate Bronze tables. Silver joins DPWH, flood control, PSGC, Table C, and boundaries. | Separate loads preserve lineage. PSGC population remains a cross-check against authoritative Table C. |
| D-23 | Oct 4 | Cloudflare R2 stores six approved CSV snapshots, including the trimmed MGB extract. Bronze holds the selected snapshot and records its identity. | This replaces D-22 and resolves D-21. R2 retains history while Bronze avoids repeated downloads and duplicate multi-GB snapshots. |
| D-24 | Oct 1 | Table B is outside the current Bronze contract. Keep it only as an optional reference for future population-growth analysis. This updates the Table B part of D-18. | The six-source Bronze contract uses Census Table C as the authoritative population source. PSGC population remains a cross-check. |
| D-25 | Oct 1 | Start geographic analysis at the regional level. Add province-level views only where matching coverage supports them. Keep NCR separate. | The accepted snapshot contains coordinate pairs for 215,139 of 265,661 DPWH rows, about 81%. Silver must separately report actual geographic match coverage. |
| D-26 | Oct 1 | Use flood control as the story entry point. Compare it with other infrastructure types and show where the remaining reported budget goes. | Flood control provides a familiar entry point. The broader portfolio still answers the complete business question. |
| D-27 | Oct 2 | TWG-IDI is the primary user for comparing reported infrastructure investment by area and type. The public is the secondary user. | The sponsor identified this audience so the dashboard has a concrete decision-making purpose. |
| D-28 | Oct 2 | Report project or contract budget, not actual payment or government disbursement. Show source gaps and coverage limitations before interpreting results. | The checked extract lacks payment data. The accepted snapshot has 50,522 DPWH rows without coordinate pairs. BARMM coverage is limited by the source. |
| D-29 | Oct 2 | Keep every pipeline layer reproducible across source updates. Preserve snapshot, run, source version, mapping version, match status, and processing timestamps. | R2 retains raw snapshot history. Downstream lineage makes comparisons and rule changes traceable. |
| D-30 | Oct 5 | Store Silver mapping decisions in five versioned Delta configuration tables. Seed only the documented MGB codes and keep other rules empty until approval. | This updates D-20 for the first Silver milestone. It prevents hidden mappings, guessed values, and duplicate rules across notebooks. |
| D-31 | Oct 7 | Use this project-region precedence. Start with Central Office, an approved manual exception, and then a verified project PSGC code. Continue with exact region name, approved alias, and coordinate-boundary fallback. Otherwise leave the project unresolved. The code stage applies only when a legitimate field exists. Keep ambiguity and name-coordinate conflicts visible. Do not use fuzzy, nearest, or hidden corrections. This resolves D-03. | A region-first waterfall answers the current analysis at the required grain. Reviewed and exact evidence stays ahead of spatial fallback. Conflicts, missing coordinates, boundary-version differences, and unavailable project PSGC codes remain traceable. |
| D-32 | Oct 8 | A project is long-running when more than 24 months pass from its start date to its completion date. A project without a completion date is measured to its snapshot date instead. The snapshot date is the file date of the DPWH snapshot in `load_log`, never the current date. The flag is `NULL` when the start date is missing. | Silver left the rule open. Measuring finished projects to their snapshot date would flag about 204,000 completed projects. Measuring to completion flags about 15,200, mostly ongoing work. A fixed snapshot date makes the flag reproducible. The two-year rule comes from the team's constellation model draft. |
| D-33 | Oct 8 | Gold surrogate keys are deterministic hashes. BIGINT keys use `XXHASH64` and INT keys use `HASH` of a fixed key label plus the natural key, as listed in the Gold model. Date keys are `yyyymmdd`. Key `0` is the reserved unknown member. | A rerun must not change keys. Hashes need no lookup tables, and a STOP check proves they are unique. |
| D-34 | Oct 5 | We stay at the region level for the capstone. Provinces stay a note, not a build. This narrows the drill-down part of D-25. | Options were to build a province drill-down now or keep regions only. The schema is fixed to regions, and 1 in 5 projects has no map point. Oct 5 team call, and Ms. Carmi on Oct 7 said regions first. |
| D-35 | Oct | Gold may read the region rows of `01-bronze.boundaries` for one purpose: to store region shapes and centroids for maps in `dim_region` and `dim_region_boundary`. Gold parses them with the Table 13 rule, takes the snapshot Table 14 used, and copies Table 14's boundary status. Gold runs no intersection, clipping, or area work. | Silver does not store region shapes. Table 14 already decides which shapes are safe. This exception ends when Silver publishes the shapes. |
| D-36 | Oct | `dim_project` has no key `0`. Every `fact_project_snapshot` row comes from a real `silver_project` row, so its project is always known. | The team note says unknown records use key `0`. A project fact never has an unknown project, so an empty unknown member adds nothing. |
| D-37 | Oct | In Gold dimensions, an unmapped category or status stays `NULL`. A status column such as `infra_type_mapping_status` or `status_mapping_version` says why. Gold never writes `Unknown` into a mapped column. Key `0` is the only Unknown member. | `NULL` with a reason keeps unmapped rows separate from a real mapped value. An `Unknown` text value would look like an approved category in the dashboard. |
| D-38 | Oct | Gold keeps five small derivations: the Table 13 region filter on `administrative_level`, `region_short_name` from the trailing parentheses of the PSGC name, `TRIM` on approved config status keys to match Silver's trimmed `status_raw`, `infra_type_mapping_status` from Silver's `category_resolution_status`, and `TRY_CAST` of `infra_year`. None of them maps a category, status, region, or flood level. Each moves to Silver when Silver publishes the field. | They are display or join helpers that Silver does not publish yet. |

Additional context for D-22:

- The five-source design used the DPWH API, flood-control layer, PSGC file, Table C, and seven boundary files.
- PSGC provides codes and place names.
- Table C provides authoritative population.
- On September 29, 43,748 of 43,750 Table C rows matched the PSGC population count.

Snapshot context for D-19 and D-23:

- D-19 records the September 29 flood-control snapshot with 9,855 rows.
- The accepted October 4 snapshot contains 9,861 rows.

## Resolved questions

| ID | Question | Resolution |
| --- | --- | --- |
| D-03 | How do we match a project to a place? Options reviewed: Map point, office name, or both. | D-31 uses both within a governed region-first precedence. Exact reviewed evidence selects the region before coordinate-boundary fallback. Central Office stays non-geographic, and conflicts or unresolved rows stay visible. |
| D-21 | Do we add the DENR MGB flood-susceptibility map as a sixth source? | Yes. D-23 approves the trimmed extract as the sixth R2 snapshot. |
