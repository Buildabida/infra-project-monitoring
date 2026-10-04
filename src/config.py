"""Central configuration for the R2-to-Bronze batch.

The six files already exist in the Unity Catalog volume. Notebooks may override
the snapshot ID and force-reload flag, but paths and table names live here.
"""

CATALOG = "buildabida-capstone"
SOURCE = "00-source"
BRONZE = "01-bronze"
VALIDATION = "04-validation"

SOURCE_VOLUME = "cloudflare-r2"
SOURCE_VOLUME_PATH = f"/Volumes/{CATALOG}/{SOURCE}/{SOURCE_VOLUME}"

# provenance_class: A original publisher artifact; B lossless export;
# C approved trimmed extract; D preprocessed/derived artifact; E unknown.
# The first five originals were API JSON, XLSX, or GeoJSON. Their CSV export
# process is not recorded, so the CSVs are not claimed to be lossless.
SOURCES = {
    "dpwh_projects": {
        "table": "dpwh_projects",
        "file_name": "dpwh_projects.csv",
        "source_system": "BetterGov DPWH projects API export",
        "provenance_class": "D",
        "provenance": "CSV derived from the DPWH projects API; export procedure and losslessness are unverified.",
        "grain": "one source project row per selected snapshot",
        "key_candidates": ["contractId", "contract_id", "ContractID"],
        "required_any_columns": ["contractId", "contract_id", "ContractID"],
    },
    "flood_control_projects": {
        "table": "flood_control_projects",
        "file_name": "flood_control_projects.csv",
        "source_system": "DPWH flood control map layer export",
        "provenance_class": "D",
        "provenance": "CSV derived from the ArcGIS feature layer; export procedure and losslessness are unverified.",
        "grain": "one source feature row; repeated Contract IDs are preserved",
        "key_candidates": ["ObjectId", "ObjectID", "object_id", "OBJECTID"],
        "required_any_columns": ["ObjectId", "ObjectID", "object_id", "OBJECTID"],
    },
    "psgc": {
        "table": "psgc",
        "file_name": "psgc.csv",
        "source_system": "PSA PSGC publication export",
        "provenance_class": "D",
        "provenance": "CSV derived from the PSA publication workbook; export procedure and losslessness are unverified.",
        "grain": "one PSGC place row in the exported snapshot",
        "key_candidates": [
            "psgc_code_parsed",
            "psgc_code",
            "10-digit PSGC",
            "10-digit_PSGC",
        ],
        "required_any_columns": [
            "psgc_code_parsed",
            "psgc_code",
            "10-digit PSGC",
            "10-digit_PSGC",
        ],
    },
    "census_2024_table_c": {
        "table": "census_2024_table_c",
        "file_name": "population_2024_table_c_test.csv",
        "source_system": "PSA 2024 Census Table C export",
        "provenance_class": "D",
        "provenance": "Combined/test CSV derived from 18 PSA workbooks; original file, sheet, and row lineage is unverified unless present in the CSV.",
        "grain": "one exported Table C source row, including known BARMM copies",
        "reference_rows": 45_611,
        "known_duplicate_rows": 1_861,
        "required_any_columns": [
            "population_parsed",
            "population_2024",
            "population",
            "total_population",
        ],
    },
    "boundaries": {
        "table": "boundaries",
        "file_name": "boundary_bettergov.csv",
        "source_system": "BetterGov Philippine boundary export",
        "provenance_class": "D",
        "provenance": "Combined CSV derived from geographic boundary data; original seven-file lineage is unverified unless present in the CSV.",
        "grain": "one exported geographic shape row",
        "reference_rows": 43_760,
        "required_any_columns": [
            "source_feature_json",
            "geometry",
            "geometry_wkt",
            "wkt",
            "geom",
        ],
    },
    "flood_susceptibility": {
        "table": "flood_susceptibility",
        "file_name": "flood_susceptibility.csv",
        "source_system": "DENR MGB flood susceptibility approved extract",
        "provenance_class": "C",
        "provenance": "Approved trimmed extract containing project-required fields; not the complete original MGB service response.",
        "grain": "one source flood-area row in the approved extract",
        "reference_rows": 63_684,
        "rating_reference": {
            "very high": 6_156,
            "high": 15_111,
            "moderate": 25_302,
            "low": 17_092,
            "missing": 23,
        },
        "required_any_columns": [
            "susceptibility",
            "flood_susceptibility",
            "rating",
            "hazard",
            "hazard_rating",
        ],
    },
}

SOURCE_ORDER = (
    "dpwh_projects",
    "flood_control_projects",
    "psgc",
    "census_2024_table_c",
    "boundaries",
    "flood_susceptibility",
)

INGEST_METADATA_COLUMNS = (
    "_source_system",
    "_source_path",
    "_source_file",
    "_source_format",
    "_source_snapshot_id",
    "_ingest_run_id",
    "_ingested_at",
    "_source_file_size_bytes",
    "_source_modified_ns",
    "_source_modified_at",
)

TABLE_C_FILE_COUNT = 18
TABLE_C_EXPECTED_ROWS = 45_611
TABLE_C_DUPLICATE_ROWS = 1_861
TABLE_C_ANALYSIS_ROWS = 43_750
TABLE_C_POPULATION_EXCLUDING_EMBASSIES = 112_727_776
BOUNDARY_EXPECTED_ROWS = 43_760
FLOOD_SUSCEPTIBILITY_EXPECTED_ROWS = 63_684

PH_LAT = (4.2, 21.3)
PH_LON = (116.0, 127.0)


def source_config(source_name):
    """Return one source config with its absolute volume path."""
    if source_name not in SOURCES:
        raise KeyError(
            f"Unknown source {source_name!r}. Expected one of {tuple(SOURCES)}"
        )
    source = dict(SOURCES[source_name])
    source["name"] = source_name
    source["path"] = f"{SOURCE_VOLUME_PATH}/{source['file_name']}"
    return source
