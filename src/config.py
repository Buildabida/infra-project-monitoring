"""Names and links for our Python notebooks. SQL notebooks start with USE CATALOG `buildabida-capstone`.

Change a link here, and every notebook gets it.
"""

CATALOG = "buildabida-capstone"
SOURCE = "00-source"
BRONZE = "01-bronze"
VALIDATION = "04-validation"

# Files we save before we load them: API pages and files we download by hand.
LANDING = f"/Volumes/{CATALOG}/{SOURCE}/landing"

REPO = "github.com/Buildabida/infra-project-monitoring"

# Tells each website who is asking.
USER_AGENT = f"buildabida ({REPO})"

# 1. DPWH projects, through the BetterGov.ph API. Up to 5,000 projects per page.
DPWH_API = "https://api.dpwh.bettergov.ph/projects"
DPWH_PAGE_SIZE = 5000

# 2. Flood control projects, the DPWH map layer behind sumbongsapangulo.ph. Up to 1,000 per call.
FLOOD_LAYER = (
    "https://services1.arcgis.com/IwZZTMxZCmAmFYvF/arcgis/rest/services/"
    "FloodControl_Data_20250802_v6_corrected_coordinates_for_uploading/FeatureServer/0/query"
)
FLOOD_PAGE_SIZE = 1000

# 3. PSA blocks Databricks, so we download the PSGC file by hand into LANDING/psa.
# It also has the 2024 population of every place, with its code.
# Our population source is census Table C (D-18). We use the PSGC count to cross-check it.
# We read one exact file of each, the release our docs and checks are for. For a new release,
# change the name here and check the counts again.
PSA_FOLDER = f"{LANDING}/psa"
PSGC_PAGE = "https://psa.gov.ph/classification/psgc"
PSGC_FILE = "PSGC-2Q-2026-Publication-Datafile.xlsx"
CENSUS_PAGE = (
    "https://psa.gov.ph/content/"
    "2024-census-population-popcen-population-counts-declared-official-president"
)

# Census Table C, our population source (D-18). PSA blocks Databricks, so we download the 18 region
# files by hand into one folder. The load stops if the files don't match these counts.
TABLE_C_FOLDER = f"{LANDING}/population/table_c"
TABLE_C_FILES_GLOB = f"{TABLE_C_FOLDER}/*.xlsx"
TABLE_C_FILE_COUNT = 18
TABLE_C_EXPECTED_ROWS = 45_611
TABLE_C_DUPLICATE_ROWS = 1_861
TABLE_C_ANALYSIS_ROWS = 43_750
TABLE_C_NON_DATA_SHEETS = 2
# The BARMM file has 4 extra sheets that copy other sheets in the same file. Bronze keeps and marks them.
TABLE_C_DUPLICATE_SHEETS = {
    "Table C_Lanao del Sur_1",
    "Table C_Maguindanao del Norte1",
    "Table C_Maguindanao del Sur1",
    "Table C_SGA1",
}

# 5. Boundary maps with PSGC codes (PSA and NAMRIA, 2023-10-24 snapshot).
# The link is pinned to one commit, so the files never change under us.
BOUNDARY_SNAPSHOT = "2023-10-24"
BOUNDARY_BASE = (
    "https://raw.githubusercontent.com/bendlikeabamboo/barangay-boundaries-repository/"
    "edf53994c8f217d9e1ce3f74c3d0a78025e0812a/2023-10-24/hierarchical_t0p005/"
)
# We load 7 of the 8 files (D-17). We skip special_geographic_areas.geojson: its 8 parts have
# no PSGC code, the special area barangays are already in barangays.geojson, and its outline
# covers the same ground as its parts, so a project could be counted twice.
BOUNDARY_FILES = [
    "regions.geojson",
    "provinces.geojson",
    "highly_urbanized_cities.geojson",
    "independent_component_cities.geojson",
    "component_cities.geojson",
    "municipalities.geojson",
    "barangays.geojson",
]

# A rough box around the Philippines, to screen map points. A point outside it is not in the country.
# A point inside it can still be at sea, so silver checks the points against the boundary maps.
PH_LAT = (4.2, 21.3)
PH_LON = (116.0, 127.0)

# One small request per source, to test if Databricks can reach it.
SOURCE_CHECKS = {
    "DPWH projects API (BetterGov)": f"{DPWH_API}?page=1&limit=1",
    "Flood control map layer (DPWH)": f"{FLOOD_LAYER}?where=1%3D1&returnCountOnly=true&f=json",
    "BetterGov open data portal": "https://data.bettergov.ph/api/v1/stats",
    "PSA PSGC page": PSGC_PAGE,
    "PSA OpenSTAT": "https://openstat.psa.gov.ph/",
    "HDX boundary maps": "https://data.humdata.org/dataset/cod-ab-phl",
    "Hugging Face (BetterGov copies)": (
        "https://huggingface.co/api/datasets/bettergovph/dpwh-transparency-data"
    ),
    "GitHub raw files": (
        "https://raw.githubusercontent.com/Buildabida/infra-project-monitoring/main/README.md"
    ),
}
