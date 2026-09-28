# How we work

These rules help five people build one pipeline without breaking each other's work. We keep our tools simple: GitHub for code and tasks, and Databricks for notebooks. You don't need VS Code.

## Before you start

1. Accept your invite to the [Buildabida org](https://github.com/Buildabida) on GitHub. No invite yet? Ask Nadine, our org owner.
2. In Databricks, click your profile picture, then **Settings**, then **Linked accounts**.
3. Click **Add Git credential** and pick **GitHub**. Then click **Link Git account** and **Authorize Databricks**.
4. Add the repo as a Git folder. The steps are in the [quickstart](README.md#quickstart).

An org owner installs the Databricks GitHub app on Buildabida once. Without it, Databricks can't push to our repo.

## Make a change

1. **Pick an issue.** Take a card on the [project board](https://github.com/orgs/Buildabida/projects/1). Check that it has an owner and a reviewer, and that nothing blocks it.
2. **Pull first.** Pull `main` before you start any work.
3. **Make a branch** named `<type>/issue-<number>-<short-name>`:
   - `feature/issue-6-bronze-dpwh-projects` for new work
   - `fix/issue-14-silver-dates` for a fix
   - `docs/issue-9-source-cards` for docs
4. **Commit small.** Make one change per commit. Say what changed, like `Add bronze load for DPWH projects`.
5. **Open a pull request** into `main`. Fill in every part of the form, and link the issue with `Closes #6`.
6. **Get a review** from the reviewer named in the issue. Then Kinah merges.
7. **Pull again** after a merge, so you have the latest `main`.

The `main` branch only takes pull requests that have one approval and pass our checks. Everyone commits from their own account, so the history shows who did what.

## Write issues and pull requests

We write each issue like a small plan, so anyone can pick it up or review it without guessing. The issue forms ask for these parts:

| Part | What to write |
| --- | --- |
| Outcome | What works when the issue is done |
| Why | Why we need it, and what waits on it |
| Scope | What the issue covers, and what it leaves out |
| Prerequisites | Issues that block it, and related issues |
| Acceptance evidence | The proof we need before we close it |
| Ownership | The owner, the reviewer and the docs it changes |

Start each title with its layer in capitals, like `[BRONZE] Load DPWH projects`.

The pull request form asks for a summary, the related issue, the changes and how you tested them. It also asks for evidence, doc updates, AI help, notes for the reviewer and the acceptance criteria. Good evidence has the run date, the notebook, row counts and check results. Say what you still did not check.

## Labels

| Label | Use it for |
| --- | --- |
| `layer:setup`, `layer:bronze`, `layer:silver`, `layer:gold`, `layer:validation`, `layer:dashboard` | The part of the pipeline the issue changes |
| `layer:docs`, `layer:story` | Docs, source cards, slides and the demo |
| `type:decision` | A choice we need to make and log |
| `status:blocked` | The issue waits on another issue or person |

The board has fields for Status, Priority, Size, Start date and Target date. Set them when you take a card.

## Names

Use the same names in code, docs and diagrams.

| Thing | Pattern | Example |
| --- | --- | --- |
| Notebook | `NN_layer_source` | `01_bronze_dpwh_projects` |
| Schema | The layer name | `bronze`, `silver`, `gold`, `validation` |
| Table | What it holds, in snake_case | `silver.projects` |
| Column | snake_case, no spaces | `contract_id`, `amount_paid` |

Every table lives in our `buildabida` catalog. Our rules for writing and code are in the [style guide](docs/style-guide.md).

## Data quality

Every table gets checks. If a critical check fails, the run stops. Don't skip a failed check to make the run pass. The full list is in [data quality checks](docs/validation.md).

## Using AI tools

AI can help us build faster, but we own everything we ship. These rules come from our capstone kickoff with FTW.

### Pass the four gates

Ask these before you use AI on project work. If any answer is no, stop.

| Gate | Ask yourself |
| --- | --- |
| 1. Data | Am I allowed to share this? |
| 2. AI | Is this tool the right place for it? |
| 3. Output | Can I check what the AI made? |
| 4. Accountability | Can I explain and defend the result? |

### Know what we give AI

| Color | What | Rule |
| --- | --- | --- |
| Green | Explaining Spark, debugging, boilerplate code and tests, docs, SQL ideas, brainstorming | Fine to use. Still review the output. |
| Yellow | Cleaning rules, schema changes, transformation logic, reading results | AI can suggest. A person decides and writes down why. |
| Red | Keys, tokens and passwords, private data, compliance calls, direct changes to the final workspace, decisions about people | Never. |

### Share the least you can

Give AI the schema, a few fake rows, the error message and the code. Never give it whole tables or keys.

### Check before you merge

Before AI-helped code goes into `main`, ask:

1. Does it work?
2. Does it scale to the full data?
3. Is it safe?
4. Can we rerun it and trace every number?
5. Can I defend it?

The pull request form asks these too.

### Turn AI tips into real checks

If AI suggests a data quality check, add it to `validation.dq_results`. Don't just trust a chat that says the data looks fine.

## Keep it safe

- Never commit keys, tokens or passwords, even inside a notebook cell.
- Don't commit data files. Data lives in Databricks tables and volumes.
- Only use public sources that are listed in the README.

## Keep it clean

- Put test work in a branch, not in `main`.
- When you rename or move a file, fix every link to it.
- Delete or clearly label old files, so no one runs the wrong one.

## Where things go

| What | Where |
| --- | --- |
| Code, notebooks and docs | This repo |
| Tasks, owners and reviewers | Issues and our [project board](https://github.com/orgs/Buildabida/projects/1) |
| Big choices | Our [decisions](docs/decisions.md) and the team Doc |
| Screenshots, files and links | Our Drive folder, Docs and Sheets |
| Meetings and work sessions | Gather |

## Where we talk

- **Messenger:** day-to-day team chat
- **Gather:** meetings and work sessions
- **Slack:** the official FTW channel, for pins and context
- **Viber:** our chat with our support instructor (SI) and mentor

If we decide something in chat, write it in our [decisions](docs/decisions.md) and the team Doc.

## Found a problem?

Open an issue with the **Data bug** form. Say what you ran, what you expected and what you got.

Be kind to each other. Our [code of conduct](https://github.com/Buildabida/.github/blob/main/CODE_OF_CONDUCT.md) says how.
