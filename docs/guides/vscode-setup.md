# Set up VS Code

We write code in VS Code and run it on our Databricks team workspace. That is decision [D-11](decisions.md). Git work in VS Code does not use the workspace. Running a notebook does.

Free Edition is serverless only, so we run each file as a workflow. The **Upload and Run File** choice needs a cluster, so it does not work for us.

## 1. Install

1. Install [VS Code](https://code.visualstudio.com/) and [Git](https://git-scm.com/downloads). On a Mac, Git may already be there.
2. In VS Code, open the Extensions view and install **Databricks** and **Python**. VS Code also suggests both when you open our repo.

## 2. Get the repo

1. Open the Source Control view and click **Clone Repository**.
2. Paste `https://github.com/Buildabida/infra-project-monitoring.git` and pick a folder on your computer.
3. When VS Code asks, sign in to GitHub. Then open the folder.

## 3. Sign in to our workspace

The repo has a `databricks.yml` file that points at our team workspace, so you only sign in.

1. Click the **Databricks** icon in the left bar.
2. Under **Configuration**, click **Auth Type**, then the gear icon **Sign in to Databricks workspace**.
3. Pick **OAuth (user to machine)** and keep the profile name. Then click **Login to Databricks**, finish the sign in in your browser and approve **all-apis**.
4. Click **Select compute** and pick **Serverless**.

The extension makes a `.databricks` folder in the repo. Git ignores it, so it never gets committed.

## 4. Run a notebook

1. Open `notebooks/00_setup/00_setup_workspace.sql`.
2. Click the **Run on Databricks** icon at the top right, then **Run File as Workflow**.
3. A **Databricks Job Run** tab opens with the results. The last cell lists the five schemas.

Every notebook keeps its first line, like `-- Databricks notebook source`. That line tells Databricks the file is a notebook.

## 5. Make a change

1. Pull `main`, then make a branch named after your issue. The rules are in [how we work](../CONTRIBUTING.md#make-a-change).
2. Edit the notebook. Run it as a workflow until it passes its checks.
3. Commit and push in the Source Control view. Check the list of changed files first.
4. Open the pull request on GitHub.

## If the workspace runs out of usage

Free Edition stops compute for the rest of the day when the quota is used up. The team workspace has one quota for all of us, so keep test runs small.

- Git work still works. Only running a notebook needs compute.
- To run in your own workspace instead, change the `host` line in `databricks.yml` on your computer, then sign in again. Don't commit that change.
- Never use someone else's token. Ask the team instead.

## Where to read more

- [Databricks extension for VS Code](https://docs.databricks.com/aws/en/dev-tools/vscode-ext/)
- [Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
