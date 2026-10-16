<p align="center">
  <img src="assets/banner.png" alt="Buildabida. Every project. Every peso. Every place." width="100%">
</p>

# Infrastructure Project Monitoring

A Databricks pipeline for understanding Philippine public infrastructure investment.
It shows where funding is concentrated and which areas receive relatively less investment.

[![Checks](https://github.com/Buildabida/infra-project-monitoring/actions/workflows/checks.yml/badge.svg)](https://github.com/Buildabida/infra-project-monitoring/actions/workflows/checks.yml)

Team Buildabida built this project for the 2026 FTW Foundation Data Engineering Track capstone.

> [!NOTE]
> Bronze ingestion is implemented.
> Silver configuration, geography and population, DPWH project foundation,
> flood-list source reconciliation, project-region mapping, regional flood-exposure,
> and project-flood mapping outputs are implemented.
> The six Gold dimensions are implemented. The three Gold facts are implemented. `09_validation_gold` validates them.
> The Analytics layer is being rebuilt as six views, one per capstone insight (proposed D-56).
> The six-view design ran on Databricks on October 16, 2026, with no failed STOP check. See the [six Analytics views evidence](docs/evidence/six-analytics-views/README.md).

## Why we built it

Government project data is published across several sources.
Each source describes places and project types differently.
This makes the complete investment picture difficult to see.

Our brief asks one main question:

> Where is government infrastructure investment concentrated, and what types of projects are being funded?
> Which areas have relatively low investment compared with population and infrastructure needs?

In simple terms, we want to know where funding goes and what it supports.
We also compare investment with population and infrastructure-need indicators.

The dashboard tells six stories, one per Analytics view:

1. Where does the money go?
2. Are investments proportional to population?
3. Do flood-control investments overlap with flood-prone areas?
4. Which projects need a closer look?
5. Are we seeing projects or a connected infrastructure network?
6. What can we see only after connecting the datasets?

The analysis reports regions and governed province reporting areas (D-57). See [Province reporting-area extension](#province-reporting-area-extension).

## Who it is for

- **People** checking public works investment in their province or city
- **Planners** identifying places with high needs and relatively low investment
- **Reviewers** verifying the pipeline, evidence, and analytical assumptions

## How it works

```mermaid
flowchart LR
    S["R2 source snapshots<br>six CSV datasets"]:::src --> B["bronze"]:::bronze
    B --> SV["silver"]:::silver
    SV --> G["gold"]:::gold
    G --> A["analytics<br>six views"]:::gold
    A --> D["Dashboard and Genie"]:::dash
    B -. "Bronze checks" .-> V["validation"]:::val
    SV -. "Silver checks" .-> V
    G -. "Gold checks" .-> V
    A -. "Analytics checks" .-> V
    classDef src fill:#D7E8FF,stroke:#2B2A4C,color:#2B2A4C
    classDef bronze fill:#FFDCC8,stroke:#2B2A4C,color:#2B2A4C
    classDef silver fill:#D2F4E4,stroke:#2B2A4C,color:#2B2A4C
    classDef gold fill:#FFF2BF,stroke:#2B2A4C,color:#2B2A4C
    classDef val fill:#E6DDFF,stroke:#2B2A4C,color:#2B2A4C
    classDef dash fill:#FFD9E6,stroke:#2B2A4C,color:#2B2A4C
```

Each layer is a schema in the `buildabida-capstone` catalog.
The numbers show the pipeline order.

| Schema | What it holds |
| --- | --- |
| `00-source` | Cloudflare R2 snapshots exposed through a Unity Catalog volume |
| `01-bronze` | Selected raw source snapshots with technical lineage |
| `02-silver` | Cleaned, standardized, reconciled, and geographically matched data |
| `03-gold` | Analytical facts and dimensions |
| `04-validation` | Data-quality and pipeline-validation results |
| `05-analytics` | Six views, one per capstone insight, that the dashboard and Genie read |

Python preserves six selected source snapshots in `01-bronze`.
Grouped Spark checks write Bronze results to `04-validation`.
Silver configuration tables govern mapping decisions.

Implemented Silver outputs currently include:

- official PSGC place hierarchy
- Table C place-level reconciliation
- region-level population
- row-preserving DPWH project components
- canonical project-level consolidation with a governed DPWH
  `componentCategories` sector taxonomy
- row-preserving flood-control components
- exact Contract-ID source reconciliation
- governed project-to-region mapping with retained unresolved and conflict evidence
- regional MGB flood exposure calculated once in an equal-area CRS, with explicit no-data regions
- governed project-to-flood-susceptibility classification with retained no-match and ambiguous evidence

Silver validation checks row preservation, project accounting, and taxonomy
coverage for projects and reported budgets. It checks source reconciliation,
geographic precedence, budget protection, lineage, and retained source-quality
findings. It also checks flood-exposure area, CRS, and overlap.
For project-flood mapping, it independently recomputes every project's MGB candidates.

Gold dimensions and facts are implemented, and `09_validation_gold` checks them.
See the [Gold model](docs/gold_model.md).
Six thin Analytics views read Gold only, one per capstone insight.
A seven-tab dashboard for citizens reads only those views.
See [Analytics views](notebooks/05_analytics/README.md) and the
[dashboard specification](dashboard/dashboard_spec.md).
The [pipeline job](resources/buildabida_full_pipeline.job.yml) runs every layer and gate in order,
then refreshes the dashboard.

## Quickstart

We write code in VS Code and use the shared [Databricks Free Edition](https://www.databricks.com/learn/free-edition) workspace.
Nadine manages workspace access.

1. Install VS Code with the **Databricks** and **Python** extensions.
2. Clone `https://github.com/Buildabida/infra-project-monitoring.git`.
   Open the cloned folder in VS Code.
3. Select the **Databricks** extension.
   Sign in with **OAuth (user to machine)** and choose **Serverless**.
4. Open `notebooks/00_setup/00_setup_workspace.sql`.
   Select **Run on Databricks**, then **Run File as Workflow**.

The final cell lists the five project schemas.
Next, use `01_check_sources.py` to verify access to every configured source.
See [set up VS Code](docs/vscode-setup.md) for the full instructions.

Before loading Bronze, confirm that the six configured CSVs exist in this volume directory:

```text
/Volumes/buildabida-capstone/00-source/cloudflare-r2/buildabida/
```

Then use `notebooks/run_all.py`, the current Source-to-Bronze coordinator.
See [load Bronze](notebooks/README.md#load-bronze) for the complete workflow.

## Data sources

### Loaded Bronze sources

Bronze loads these six approved snapshots from Cloudflare R2:

| Source | What we use it for |
| --- | --- |
| [DPWH projects API](https://api.dpwh.bettergov.ph/projects) by BetterGov.ph | DPWH projects with reported budget, progress, dates, contractor, and map points. The selected snapshot contains 265,661 rows. |
| [BetterGov flood-control projects](https://bettergov.ph/flood-control-projects/table) | Flood-control list named in the project brief. The selected snapshot contains 9,861 rows. |
| [PSGC 2Q 2026](https://psa.gov.ph/classification/psgc) by PSA | Official geographic codes and place names. Population remains a cross-check for Table C. |
| [2024 Census of Population](https://psa.gov.ph/content/2024-census-population-popcen-population-counts-declared-official-president) by PSA | Table C provides the authoritative project population source. |
| [Boundary maps](https://github.com/bendlikeabamboo/barangay-boundaries-repository) with PSGC codes | Geographic reference data for matching project coordinates to places |
| [DENR MGB flood susceptibility](https://controlmap.mgb.gov.ph/arcgis/rest/services/GeospatialDataInventory/GDI_Detailed_Flood_Susceptibility/FeatureServer/0) | Flood-hazard context from the approved trimmed extract. Spatial matching remains downstream. |

### Reference and spot-check sources

These sites support manual verification. They are not additional Bronze datasets.

| Source | What we use it for |
| --- | --- |
| [DPWH Transparency Portal](https://transparency.dpwh.gov.ph) | Official DPWH reference used for source spot-checks |
| [Sumbong sa Pangulo](https://sumbongsapangulo.ph) | DPWH flood-control project reference |

Table C is the authoritative population source.
PSGC population remains a cross-check.
See the [Bronze R2 architecture](docs/bronze_r2_architecture.md) for current CSV provenance limits.

Three important source rules apply:

- The API field `location.province` can contain a DPWH district office name.
  It is not always a PSGC province.
  Silver uses map points and boundaries to identify the geographic area.
- One flood-control contract can have multiple legitimate rows.
  These can represent components or funding years.
  Bronze preserves them, and Silver handles their analytical interpretation.
- A project can appear in both project lists.
  Silver matches records using approved rules to prevent double-counting.

## Known limits

- **Current CSV provenance varies.**
  Several CSVs were derived from API JSON, XLSX, or GeoJSON.
  The repository does not prove that every export was lossless.
  The MGB file is an approved trimmed extract.
- **DPWH data contains gaps.**
  The September 29 checks found zero amount paid for every project.
  About one in five projects has no map point.
  BARMM project coverage is also limited by the source.
- **One workspace owns the final pipeline.**
  This follows [D-01](docs/decisions.md).
  The team limits unnecessary compute and shares code through this repository.
- **MGB missing ratings and geometry remain source-quality findings.**
  The October 6 reconciliation recognizes the official `VHF`, `HF`, `MF`,
  and `LF` severity codes and treats `No rating`, null, and blank ratings as
  missing or unrated during validation only. The final unknown-rating check
  reports zero unexpected values. The selected snapshot contains 1,838
  missing or unrated records, including 1,815 rows where both the rating and
  geometry are blank. These remain non-blocking findings for Silver handling,
  while Bronze preserves the original source values.
- **Few project points fall inside MGB flood polygons.**
  In the first project-flood run, 20,398 of 215,138 projects with usable
  coordinates received a flood level. Another 15 sit inside polygons of more
  than one level. Most of the rest fall outside every approved polygon.
  That is not evidence of low or zero flood risk.
  See [project flood mapping](docs/silver_project_flood_mapping.md#runtime-evidence).

## Find your way around

- **Run it:** [quickstart](#quickstart), [notebooks guide](notebooks/README.md), and [VS Code setup](docs/vscode-setup.md)
- **Look something up:** [data model](docs/data-model.md), [validation](docs/validation.md), [Silver mappings](docs/silver_config_mappings.md), and [Silver geography and population](docs/silver_geography_population.md).
  Continue with [Silver project foundation](docs/silver_project_cleaning.md), [source reconciliation](docs/silver_source_reconciliation.md), [project-to-region mapping](docs/silver_project_region_mapping.md), [regional flood exposure](docs/silver_region_flood_exposure.md), [project flood mapping](docs/silver_project_flood_mapping.md), or the [style guide](docs/style-guide.md).
- **Build the dashboard:** [Analytics views](notebooks/05_analytics/README.md) and the [dashboard build specification](dashboard/dashboard_spec.md)
- **Review evidence:** [Bronze validation evidence](docs/evidence/bronze-r2/README.md)
- **See why we chose something:** [decisions](docs/decisions.md)
- **Contribute:** [how we work](CONTRIBUTING.md)

```text
.
├── README.md          this page
├── CONTRIBUTING.md    team workflow, reviews, and AI rules
├── LICENSE            MIT License for project code
├── notebooks/         Databricks notebooks organized by pipeline step
├── src/               shared Python modules and their current or legacy status
├── docs/              model, validation, evidence, decisions, and guides
├── dashboard/         dashboard build specification and exports
├── tests/             automated tests for shared code
├── resources/         Databricks job and bundle settings
├── assets/            repository images
├── databricks.yml     shared workspace configuration
└── .github/           issue forms, pull request forms, and checks
```

## Help out

Every change uses a pull request with one review.
Read [how we work](CONTRIBUTING.md) before contributing.

Our AI policy is AI-assisted and human-owned.
See [using AI tools](CONTRIBUTING.md#using-ai-tools) for the accountability rules.

## Team and timeline

Team members are Kinah, Bri, Nadine, Sam, and Tricia.
Carmi is the mentor, and Simonee is the support instructor.

| Date | Milestone |
| --- | --- |
| Oct 3 | Bronze ingestion and reviewed draft schema |
| Oct 10 | Silver and Gold tables with validation |
| Oct 17 | Dashboard, Genie, and Databricks Associate exam |
| Oct 24 | Final Capstone Showcase and graduation |

Tasks are tracked on the [project board](https://github.com/orgs/Buildabida/projects/1).

## License and credits

Project code uses the [MIT License](LICENSE).
Source data remains subject to each publisher's terms.
We thank DPWH, PSA, BetterGov.ph, OCHA HDX, and FTW Foundation.

## Province reporting-area extension

D-57 approves governed province reporting areas: official PSGC provinces,
independent cities whose selected PSGC hierarchy has no province parent, NCR as
one reporting area, and Unknown key `0`. Region remains the parent and the
backward-compatible reconciliation geography.

Production notebooks now add the Silver reporting-area reference, boundary,
Table C population aggregation, and one-row-per-project mapping; the Gold
reporting-area dimensions and population fact; `reporting_area_key` on the
project snapshot fact; province content in the six Analytics views (D-56); and
layer-specific validation. DPWH `location.province` is evidence only. Matching is governed,
exact, and fail-closed, with one longitude-first `ST_COVERS` fallback.

Databricks runtime evidence passed for the recorded D-57 snapshot on October 15:
43 checks passed, five non-blocking coverage flags were retained, and no check
failed. That run validated Silver, Gold, and five earlier province Analytics views
that are now retired. On October 16 the full pipeline ran again with the v2
population and hierarchy checks and the six views: 159 checks were published,
no STOP check failed, and the exact rerun passed against the October 15 capture.
A second run of the Analytics validator on the same Gold data changed none of its checks.
Project mapping coverage is 75.3267 percent and reported-budget coverage is
83.6904 percent. Two exact-rerun captures retained the same mapping run ID and
checksum. Province flood exposure remains deferred until selected boundaries
and the MGB intersection are shown to be safe and affordable on Free Edition.
See the [province-reporting runtime evidence](docs/evidence/province-reporting/README.md),
[six Analytics views evidence](docs/evidence/six-analytics-views/README.md),
[production contract](docs/province_reporting_readiness.md),
[Silver mapping](docs/silver_project_province_mapping.md), and
[Gold model](docs/gold_model.md).
