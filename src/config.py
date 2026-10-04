"""Single source of truth for the six-source R2-to-Bronze batch.

The module separates source differences from shared ingestion mechanics. Catalog,
schema, volume, file, table, grain, provenance, identifier aliases, and documented
references live here so notebooks do not repeat paths or business contracts.

Adding another CSV source requires one readable configuration entry, one thin source
notebook, source-specific validation, and focused tests. It does not require another
copy of the ingestion engine.
"""

# Stable namespace contract shared by setup, ingestion, validation, and documentation.
CATALOG = "buildabida-capstone"
SOURCE = "00-source"
BRONZE = "01-bronze"
VALIDATION = "04-validation"

# Unity Catalog exposes the durable Cloudflare R2 source boundary through this volume.
SOURCE_VOLUME = "cloudflare-r2"
# The six project source CSVs live under this subdirectory inside the R2 volume.
SOURCE_SUBDIR = "buildabida"
SOURCE_VOLUME_PATH = f"/Volumes/{CATALOG}/{SOURCE}/{SOURCE_VOLUME}/{SOURCE_SUBDIR}"

# provenance_class: A original publisher artifact; B lossless export;
# C approved trimmed extract; D preprocessed/derived artifact; E unknown.
# The first five originals were API JSON, XLSX, or GeoJSON. Their CSV export
# process is not recorded, so the CSVs are not claimed to be lossless.
# Each source entry documents both mechanics and meaning:
# - table/file_name/source_system route the artifact without notebook hardcoding;
# - provenance/grain explain what one raw row represents and what can be claimed;
# - key_candidates drive source-grain validation only where uniqueness is justified;
# - required_any_columns protect the current table before a structurally wrong CSV write;
# - reference counts support non-destructive FLAG checks, never row filtering.
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
            "geometry_json",
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
            "flood_susceptibility_code",
            "rating",
            "hazard",
            "hazard_rating",
        ],
    },
}

# The authoritative six-source sequence used by precheck, orchestration, and validation.
SOURCE_ORDER = (
    "dpwh_projects",
    "flood_control_projects",
    "psgc",
    "census_2024_table_c",
    "boundaries",
    "flood_susceptibility",
)

# Required technical lineage added to every business-source Bronze row. These names are
# reserved so a source column cannot silently overwrite ingestion metadata.
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
    """Return an isolated source contract with its absolute volume path.

    Copying the dictionary keeps notebook-level overrides local. The default path is
    always derived from the centralized catalog, schema, volume, and file name.
    """
    if source_name not in SOURCES:
        raise KeyError(
            f"Unknown source {source_name!r}. Expected one of {tuple(SOURCES)}"
        )
    source = dict(SOURCES[source_name])
    source["name"] = source_name
    source["path"] = f"{SOURCE_VOLUME_PATH}/{source['file_name']}"
    return source
