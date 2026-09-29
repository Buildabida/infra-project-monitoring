# Decisions

We log each big choice with an ID, the date and why we made it. We keep old rows, even when we change our mind. The team Doc has the same log.

## Made

| ID | Date | Decision | Why |
| --- | --- | --- | --- |
| D-01 | Sep 28 | Our team workspace runs the final pipeline and the dashboard | Nadine made a team workspace where everyone is a user. It is not tied to one person. |
| D-02 | Sep 26 | Our main question is the one in our brief | Our brief sets it |
| D-05 | Sep 26 | Our team name is Buildabida | It fits infrastructure and sounds fun |
| D-06 | Sep 26 | Tasks live in GitHub issues and one project board | One place for tasks, linked to our code |
| D-07 | Sep 28 | Our tables live in our own `buildabida` catalog | It keeps the capstone apart from old class work, like the Chinook schemas |
| D-08 | Sep 28 | Python loads the sources into `bronze`. SQL does the rest, from `silver` on. | Most of us know SQL best. Python is better for APIs, web pages and Excel files. |
| D-09 | Sep 28 | Our code lives in a fresh repo in the Buildabida GitHub org | The team owns it, not one person, and everyone gets the same access |
| D-10 | Sep 28 | Meetings happen in Gather. Files, screenshots and links go in Drive. | Each kind of thing has one home, and we skip extra tools like VS Code |
| D-11 | Sep 28 | We write code in VS Code, with the Databricks extension. Our team workspace runs it. This changes the VS Code part of D-10. | Free Edition limits us. In VS Code we can use our own tools and AI help without those limits, and Git work does not use the workspace. |
| D-12 | Sep 28 | Our folders are `notebooks`, `src`, `docs`, `dashboard`, `resources` and `tests` | Nadine and Bri know this layout from past teams. The folders are ready, so anyone can jump in. |
| D-13 | Sep 28 | Our catalog is `buildabida-capstone`. Schemas are numbered in run order: `00-source`, `01-bronze`, `02-silver`, `03-gold`, `04-validation`. This replaces the catalog name in D-07. | Nadine set up the team workspace this way and prefers numbers. The words match our class and our docs. |
| D-14 | Sep 28 | Nadine and Kinah each load all five sources, first in their own repo and Databricks account. Then they compare and bring the loads into this repo and the team workspace. | In past groups, one source per person meant nobody knew the other data. Trying it outside the team workspace saves its daily quota until we know the data. |
| D-15 | Sep 28 | Sam owns the star schema. Bri and Tricia finalize the business question and the analytical questions. Kinah keeps the repo, board and story. | Two people are enough for ingestion this week. The schema needs the final questions, so both start now. |
| D-16 | Sep 28 | We run on chat, with one team meeting a week in Gather and a Wednesday check-in with our mentor and support instructor. After it we share the team Doc and our repos with them. | Most of us prefer chat. Two touchpoints a week keep us aligned. |
| D-17 | Sep 29 | Boundary maps: we load 7 files and skip the special areas file. | Its 9 shapes are 1 outline of the Special Geographic Area and 8 parts with no PSGC code. Its barangays are already in the barangay file, and the outline covers its parts, so a project could count twice. |
| D-18 | Sep 29 | Population: census Table C is our population source. Table B is optional, for growth. The 2024 count in the PSGC file is our cross-check. | Table C has people per barangay, which our questions need. It has names but no PSGC codes, so silver matches the names to codes. |
| D-19 | Sep 29 | Flood list: bronze keeps all 9,855 rows. We don't drop rows by contract ID. | The 157 repeated rows (109 contract IDs) are not copies. 83 IDs are different parts of one contract, and 26 are one part split by funding year. Silver should count a repeated cost once, or P2.5B counts twice. |
| D-20 | Sep 29 | Until silver, our checks stay simple bronze load checks. | This week is about bronze. The results still go to `04-validation.dq_results`. |
| D-22 | Sep 29 | We load five sources. They are the DPWH projects API, the flood control layer, the PSGC 2Q 2026 file, census Table C and the boundary maps (7 files). The PSGC file gives our codes and place names, and Table C gives our population. Each source keeps its own bronze table, and silver joins them. | One job per source shows where each number comes from. Table C and the PSGC count come from the same census. On Sep 29, 43,748 of 43,750 Table C rows had the same count in the PSGC file. So the PSGC count stays our check. |

## Still open

| ID | Question | Options we're looking at |
| --- | --- | --- |
| D-03 | How do we match a project to a place? | Map point, office name, or both |
| D-04 | How do we handle projects that are in both the DPWH and flood control lists? | Match by contract ID |
| D-21 | Do we add the DENR MGB flood susceptibility map as a 6th source? We decide on Wed, Sep 30. | Add it now, keep it as a bonus, or skip it |
