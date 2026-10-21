# Get the source data

This guide explains how a grader, mentor, or new teammate gets the six source
files. It also explains how to check our results without them.

The repository never stores data files (see [keep it safe](../../CONTRIBUTING.md#keep-it-safe)).
The six approved snapshots live in Cloudflare R2. The team workspace reads them
through the Unity Catalog volume `` `buildabida-capstone`.`00-source`.`cloudflare-r2` ``.

## Pick a path

| You want to | Use | Cost |
| --- | --- | --- |
| Check our results, tables, checks, job runs, and dashboard | [Path 1: read-only access to the team workspace](#path-1-read-only-access-to-the-team-workspace) | No compute beyond your queries |
| See the full pipeline run end to end | [Path 2: ask for a supervised team run](#path-2-ask-for-a-supervised-team-run) | One full run of the daily quota |
| Rebuild everything in your own workspace with the exact snapshots | [Path 3: a copy of the six files](#path-3-a-copy-of-the-six-files) | One full run in your workspace |
| Rebuild with no help from the team | [Path 4: the public sources](#path-4-the-public-sources) | Results won't match our snapshot exactly |

We recommend Path 1 for grading. It shows the exact data, checks, and runs that
our evidence describes. Nothing has to be copied or rebuilt.

## Path 1: read-only access to the team workspace

The final pipeline runs in one shared Databricks Free Edition workspace
([D-01](../decisions.md)). Nadine manages who can use it.

1. Send Nadine the email address you use for Databricks.
2. Nadine adds you as a user of the team workspace.
3. Nadine gives you read-only access. Run this as the catalog owner, and change
   the email address:

   ```sql
   GRANT USE CATALOG ON CATALOG `buildabida-capstone` TO `grader@example.com`;
   GRANT USE SCHEMA, SELECT ON CATALOG `buildabida-capstone` TO `grader@example.com`;
   GRANT READ VOLUME ON VOLUME `buildabida-capstone`.`00-source`.`cloudflare-r2` TO `grader@example.com`;
   ```

4. Nadine gives you **Can view** on the team job and the dashboard.

You can now do these checks without running the pipeline:

- Open **Catalog**, then `buildabida-capstone`, to see every layer from `00-source` to `05-analytics`.
- List the six source files with `LIST '/Volumes/buildabida-capstone/00-source/cloudflare-r2/buildabida/'`.
- Read the latest gate with the query in [check the results](../../README.md#check-the-results).
- Open **Jobs & Pipelines** to see each run, its task graph, and its logs.
- Open the dashboard.

Read-only access is on purpose. A `dev` copy of the job writes to the same
`buildabida-capstone` tables as the team job. A grader run in this workspace
could change the data the showcase uses. If you need a run, use Path 2.

## Path 2: ask for a supervised team run

Ask Nadine to start the team job with **Run now** while you watch. Any
teammate with run rights on the job can do it too. Our two October 21 runs took
1 h 11 min and 1 h 19 min. A full run uses a large part of the workspace's
daily quota. After it finishes, check the gate as
in Path 1. The `ALL` row must be `PASS` or `FLAG`, with no failed STOP check.

## Path 3: a copy of the six files

Use this path to repeat our [clean-workspace test](clean_workspace_test.md) in
your own Free Edition workspace.

1. Ask Nadine for a copy of the six files. She shares them privately, for
   example through the team Drive, and never through the repository.
2. Follow [getting the source files](clean_workspace_test.md#getting-the-source-files)
   to make the volume and upload the files with their exact names.
3. Run `notebooks/00_setup/01_check_sources.py`. All six sources should be `OK`.
4. Follow the rest of the clean-workspace checklist.

The same files give the same `source_snapshot_id` and the same gate counts as
our [October 21 evidence](../evidence/dev-bundle-2026-10-21/README.md).

## Path 4: the public sources

Every source is public, and the README [lists their links](../../README.md#data-we-use).
You can download them yourself and save them under the six file names in
`src/config.py`.

Expect differences from our results:

- Publishers update their data. A new download is a different snapshot, so row counts and totals change.
- Several of our CSVs were made from API JSON, XLSX, or GeoJSON. The MGB file is a trimmed extract. The [Bronze R2 architecture](../bronze/bronze_r2_architecture.md#six-sources-and-provenance) explains how each one was made.
- Bronze checks the columns it needs. A file missing a required column stops before any write, by design. New optional columns only show as `header_drift`. See [update resilience](update_resilience.md).

Use this path to test that the pipeline works, not to repeat our exact numbers.
