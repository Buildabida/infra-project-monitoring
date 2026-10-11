# Silver MGB flood areas

This table is `02-silver.silver_mgb_flood_area`. It parses every selected MGB
flood-susceptibility polygon once and stores the geometry for every reader.

Table 14 (`silver_region_flood_exposure`), Table 15
(`silver_project_flood_map`), and their validators read this table. None of
them parses `geometry_json` again.

It is a Silver matching table. It is not part of the Gold star schema, and no
Gold notebook reads it.

## Why it exists

Tables 14 and 15 used to parse the MGB geometry inside their own temporary
views. Those views are lazy, so Databricks parsed every polygon again inside the
spatial stage that clips or matches it.

After the October 10 Bronze reload, the selected snapshot holds 1,815 geometry
fields longer than 131,072 characters. The largest has 34,352,521 characters.
Parsing them in the same query as the clip-and-dissolve stage ran out of
executor memory on Databricks Free Edition serverless compute.

A test on October 11 saved the parsed geometry first. Notebook 09 then
published Table 14 without errors. The parse alone took about 76 seconds, and
the clip-and-dissolve table took about 15 minutes. The two together had failed
with out-of-memory errors after 19 minutes to about an hour.

## Grain

One MGB flood-susceptibility polygon (one Bronze source row) per Bronze
snapshot per parse rule version.

## Columns

| Key | Column | Type | Meaning |
| --- | --- | --- | --- |
| PK | `mgb_flood_area_key` | STRING | SHA-256 of `object_id`, the MGB snapshot, and `parse_rule_version` |
| | `object_id` | STRING | MGB `OBJECTID`, the source key of the polygon |
| | `raw_susceptibility_code` | STRING | Trimmed, uppercased source code; blank becomes `NULL` |
| | `geometry_wkb` | BINARY | Parsed geometry as WKB; `NULL` when blank or unparseable |
| | `geometry_srid` | INT | SRID of the parsed geometry, 4326 |
| | `geometry_parse_method` | STRING | The parser path that succeeded |
| | `source_geometry_status` | STRING | One governed geometry status |
| | `mgb_source_snapshot_id` | STRING | Selected Bronze snapshot |
| | `mgb_source_ingest_run_id` | STRING | Bronze ingest run that loaded the snapshot |
| | `mgb_source_version` | STRING | Optional publisher version from `load_log` |
| | `parse_rule_version` | STRING | Version of the parser below |
| | `run_id` | STRING | Deterministic hash of the snapshot, ingest run, publisher version, and parse rule version |
| | `source_load_ts` | TIMESTAMP | Bronze ingest time |

Required uniqueness:

```text
silver_mgb_flood_area:
UNIQUE(
    object_id,
    mgb_source_snapshot_id,
    parse_rule_version
)
```

Bronze does not check `object_id` for this source. Notebook `09a` stops when an
`object_id` is blank or repeated, before it builds any key.

The table does not map codes to levels. Tables 14 and 15 apply the approved
mapping from `config_mgb_susceptibility_mapping`. A new mapping version
therefore never forces a new parse.

## Parser

The parser tries three controlled paths:

1. parse the geometry as published
2. apply the targeted quoted-number normalization
3. convert Esri `rings` JSON

A row with a `rings` key skips the first two paths, since Esri JSON is never
GeoJSON. The targeted normalization removes quotes only around numeric tokens
and bracketed coordinate strings. It never strips JSON quotes globally.

The Esri path builds its first reading from the `rings` text with string
functions, with every ring as its own polygon. It reads the rings into arrays
with `FROM_JSON` only when that reading is OGC-invalid. Then it reads the
counterclockwise rings as holes and subtracts them from the clockwise rings, as
the Esri format defines them (issue #92). A valid first reading is never
changed. This follows the source format; it is not a repair.

Each row receives one geometry status: `BLANK_GEOMETRY`,
`UNPARSEABLE_GEOMETRY`, `EMPTY_GEOMETRY`, `UNSUPPORTED_GEOMETRY_TYPE`,
`INVALID_GEOMETRY`, or `USABLE_GEOMETRY`. Only a nonempty, OGC-valid Polygon or
MultiPolygon is usable. Invalid geometry is kept with its status and never
repaired.

Change `parse_rule_version` whenever a parser change can change a geometry or a
status. The new version makes the next run parse again.

## Skip rule

Notebook `09a` keeps the published table when it already holds the selected
run: every row carries the selected `run_id`, and the row count equals the
audited Bronze count. Otherwise it parses the snapshot and replaces the table
with `INSERT OVERWRITE`.

A reconciliation gate runs after both paths. It stops when the table does not
hold every Bronze row exactly once, when keys repeat, or when usable geometry is
missing or not in SRID 4326. A skip can therefore never publish a stale or
partial table.

## Readers

Tables 14 and 15 rebuild the geometry with
`ST_SETSRID(ST_GEOMFROMWKB(geometry_wkb), source_geometry_srid)`. Each reads
only the run whose `run_id` it hashes into its own run ID, and each stops when
validation `06a` is missing or has a blocking failure.

## Run order

```text
01-bronze.flood_susceptibility
        ↓
02_silver/09a_silver_mgb_flood_area
        ↓
04_validation/06a_validation_silver_mgb_flood_area
        ↓
02_silver/09_silver_region_flood_exposure → 04_validation/07_...
02_silver/10_silver_project_flood_map     → 04_validation/08_...
```

Run `09a` and `06a` after every MGB Bronze load. When nothing changed, `09a`
skips the parse and finishes quickly.

## Validation

`notebooks/04_validation/06a_validation_silver_mgb_flood_area.ipynb` compares
the table with the selected Bronze snapshot on `object_id` in one full outer
join. It reads Bronze lineage and codes only, never `geometry_json`.

STOP checks cover:

- the newest MGB load and its Bronze validation
- the published snapshot being the latest validated snapshot
- one deterministic run and complete lineage
- every Bronze row published once, and no published row without Bronze
- raw codes equal to Bronze
- unique and deterministic keys
- the governed status and parse-method vocabularies
- WKB presence that matches the status
- usable geometry that rebuilds from WKB as a valid, nonempty polygon in SRID 4326

FLAG checks keep unusable geometry, blank codes, geometry outside the degree
screen, and differences from the 63,684-row reference visible.

## Runtime

Requires Databricks execution with native spatial SQL (`ST_TRANSFORM` requires
Databricks Runtime 17.1 or later) and `EXECUTE IMMEDIATE`. The notebooks were
tested on local Spark with shapely standing in for the `ST_` functions. They
have not run on Databricks yet.
