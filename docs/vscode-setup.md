# Set up VS Code

VS Code is optional. Databricks works fine on its own. Use VS Code if you like it, or when the team workspace runs low on usage. Git work in VS Code (pull, commit, push) does not use Databricks. Running a notebook still uses the workspace compute.

## Install

1. Install [VS Code](https://code.visualstudio.com/).
2. Install [Git](https://git-scm.com/downloads). On a Mac, Git may already be there.
3. In VS Code, open the Extensions view and install **Databricks**, made by Databricks.

## Get the repo

1. Open the Source Control view and click **Clone Repository**.
2. Paste `https://github.com/Buildabida/infra-project-monitoring.git` and pick a folder on your computer.
3. When VS Code asks, sign in to GitHub.

## Connect to our workspace

1. Click the **Databricks** icon in the sidebar, then **Create configuration**.
2. Paste the link to our team workspace. It is in the team Doc.
3. Pick **OAuth (user to machine)**, then click **Login to Databricks** and finish the sign in in your browser.
4. Pick the compute. Free Edition only has serverless.

The extension makes a `.databricks` folder in the repo. Git ignores it, so it never gets committed.

## Make a change

1. Pull `main`, then make a branch named after your issue. The rules are in [how we work](../CONTRIBUTING.md#make-a-change).
2. Edit a notebook in `notebooks`. Keep the first line, like `# Databricks notebook source`, so Databricks still sees it as a notebook.
3. To run it, open the **Run on Databricks** menu at the top right of the file and pick **Run File as Workflow**. The run happens on the workspace, and the results show in VS Code.
4. Commit and push in the Source Control view.
5. Open the pull request on GitHub.

## If the workspace runs out of usage

- Git work still works. Only running a notebook needs compute.
- Sign in to your own workspace instead, and run there.
- Never use someone else's token or workspace ID. Ask the team instead.

## Where to read more

- [Databricks extension for VS Code](https://docs.databricks.com/aws/en/dev-tools/vscode-ext/)
- [Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
