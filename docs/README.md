# Docs

Start here to find any doc about our pipeline. We draft in the team Google Doc first, then keep the final version here.

| If you need to | Read |
| --- | --- |
| Set up Databricks and run the first notebooks | [Quickstart](../README.md#quickstart) |
| Know what each table holds and its key | [Data model](data-model.md) |
| Know what we check and what happens when a check fails | [Data quality checks](validation.md) |
| Know why we chose something | [Decisions](decisions.md) |
| Write docs, SQL or Python the way we do | [Style guide](style-guide.md) |
| Make a change, write an issue or open a pull request | [How we work](../CONTRIBUTING.md) |
| See what each notebook folder does | [Pipelines guide](../pipelines/README.md) |

Source cards stay in the team Doc until Oct 3. After that, each source gets a card here.

## Keep our docs clean

- Keep each fact in one place. Link to it instead of copying it.
- Update the docs in the same pull request as the code.
- If a doc and the code disagree, fix one of them before you merge.
- Don't rewrite an old decision. Add a new decision that replaces it.
- Keep old proof. Add new proof with its own date instead of changing an old result.
- When you say something ran, give the date and the notebook, so anyone can check it.
