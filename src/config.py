"""Names and links for our Python notebooks. SQL notebooks start with USE CATALOG `buildabida-capstone`."""

CATALOG = "buildabida-capstone"
REPO = "github.com/Buildabida/infra-project-monitoring"

# Tells each website who is asking.
USER_AGENT = f"buildabida ({REPO})"

# One small request per source, to test if Databricks can reach it.
SOURCE_CHECKS = {
    "DPWH projects API (BetterGov)": "https://api.dpwh.bettergov.ph/projects?page=1&limit=1",
    "Flood control map layer (DPWH)": (
        "https://services1.arcgis.com/IwZZTMxZCmAmFYvF/arcgis/rest/services/"
        "FloodControl_Data_20250802_v6_corrected_coordinates_for_uploading/"
        "FeatureServer/0/query?where=1%3D1&returnCountOnly=true&f=json"
    ),
    "BetterGov open data portal": "https://data.bettergov.ph/api/v1/stats",
    "PSA PSGC page": "https://psa.gov.ph/classification/psgc",
    "PSA OpenSTAT": "https://openstat.psa.gov.ph/",
    "HDX boundary maps": "https://data.humdata.org/dataset/cod-ab-phl",
    "Hugging Face (BetterGov copies)": (
        "https://huggingface.co/api/datasets/bettergovph/dpwh-transparency-data"
    ),
    "GitHub raw files": (
        "https://raw.githubusercontent.com/Buildabida/infra-project-monitoring/main/README.md"
    ),
}
