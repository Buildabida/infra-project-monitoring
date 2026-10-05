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
| D-23 | Oct 4 | Cloudflare R2 stores six approved CSV snapshots, including the trimmed MGB extract. Bronze holds the selected snapshot and records its identity. | This replaces D-22 and resolves D-21. R2 retains history while Bronze avoids repeated downloads and duplicate multi-GB snapshots. D-19 records the September 29 flood-control snapshot with 9,855 rows.
The accepted October 4 snapshot contains 9,861 rows. |
| D-24 | Oct 1 | Table B is outside the current Bronze contract. Keep it only as an optional reference for future population-growth analysis. This updates the Table B part of D-18. | The six-source Bronze contract uses Census Table C as the authoritative population source. PSGC population remains a cross-check. |
| D-25 | Oct 1 | Start geographic analysis at the regional level. Add province-level views only where matching coverage supports them. Keep NCR separate. | The accepted snapshot contains coordinate pairs for 215,139 of 265,661 DPWH rows, about 81%. Silver must separately report actual geographic match coverage. |
| D-26 | Oct 1 | Use flood control as the story entry point. Compare it with other infrastructure types and show where the remaining reported budget goes. | Flood control provides a familiar entry point. The broader portfolio still answers the complete business question. |
| D-27 | Oct 2 | TWG-IDI is the primary user for comparing reported infrastructure investment by area and type. The public is the secondary user. | The sponsor identified this audience so the dashboard has a concrete decision-making purpose. |
| D-28 | Oct 2 | Report project or contract budget, not actual payment or government disbursement. Show source gaps and coverage limitations before interpreting results. | The checked extract lacks payment data. The accepted snapshot has 50,522 DPWH rows without coordinate pairs. BARMM coverage is limited by the source. |
| D-29 | Oct 2 | Keep every pipeline layer reproducible across source updates. Preserve snapshot, run, source version, mapping version, match status, and processing timestamps. | R2 retains raw snapshot history. Downstream lineage makes comparisons and rule changes traceable. |

Additional context for D-22:

- The five-source design used the DPWH API, flood-control layer, PSGC file, Table C, and seven boundary files.
- PSGC provides codes and place names.
- Table C provides authoritative population.
- On September 29, 43,748 of 43,750 Table C rows matched the PSGC population count.

## Still open

| ID | Question | Options under review |
| --- | --- | --- |
| D-03 | How do we match a project to a place? | Map point, office name, or both |
| D-04 | How do we handle projects found in both project lists? | Match by Contract ID |

## Resolved questions

| ID | Question | Resolution |
| --- | --- | --- |
| D-21 | Do we add the DENR MGB flood-susceptibility map as a sixth source? | Yes. D-23 approves the trimmed extract as the sixth R2 snapshot. |
