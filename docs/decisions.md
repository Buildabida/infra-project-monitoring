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

## Still open

| ID | Question | Options we're looking at |
| --- | --- | --- |
| D-03 | How do we match a project to a place? | Map point, office name, or both |
| D-04 | How do we handle projects that are in both the DPWH and flood control lists? | Match by contract ID |
