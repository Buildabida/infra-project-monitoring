# Documentation fixes

Copy the files in this folder over the repository root, keeping their paths.
Or, from the repository root on branch `feat/productionize-governance`, run:

    git am doc-fixes.patch

## What changed

| File | Change |
| --- | --- |
| `README.md` | New Assumptions section. Links the Gold diagram and the new data-access guide. Clarifies 49 versus 50 tasks. |
| `docs/model/gold_model.md` | Meaning column for all 159 Gold columns, copied from the notebook column comments. |
| `docs/model/data-model.md` | Gold diagram with all twelve tables, including the D-57 province tables. Analytics status updated. |
| `docs/images/gold-model-erd.png` | New image of the same diagram, for slides. |
| `docs/guides/data_access.md` | New. How a grader gets the data. Read-only access to the team workspace is the main path. |
| `docs/decisions.md` | D-56 moved from Proposed to Made, dated Oct 16 (PR #137 merge). |
| `docs/evidence/dev-bundle-2026-10-21/README.md` | Most likely deployed commit, labeled as inferred, with how to confirm it. |
| `docs/guides/clean_workspace_test.md` | Commit field updated. Links the data-access guide. |
| `docs/README.md` | Index entries for the new guide and the diagram. |
| `docs/validation/validation.md`, `notebooks/05_analytics/README.md` | Removed "proposed" from D-56. |
| `tests/test_gold_dimensions.py`, `tests/test_gold_facts.py` | Accept the new Meaning column. New test that every Meaning matches its notebook comment. |
| `tests/test_analytics.py` | Expects D-56 under Made, not Proposed. |

Checked locally: 526 tests passed, Ruff lint and format, markdownlint, all links and anchors, and Vale.
