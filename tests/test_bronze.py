import pytest

from src import bronze, config


def test_snapshot_id_uses_metadata_not_file_contents(tmp_path):
    path = tmp_path / "source.csv"
    path.write_text("id,value\n1,a\n", encoding="utf-8")
    metadata = bronze.inspect_source(path)

    first = bronze.deterministic_snapshot_id("example", metadata)
    second = bronze.deterministic_snapshot_id("example", metadata)

    assert first == second
    assert first.startswith("metadata-")


def test_inspect_source_rejects_duplicate_headers(tmp_path):
    path = tmp_path / "duplicate.csv"
    path.write_text("id,ID\n1,2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate header"):
        bronze.inspect_source(path)


def test_column_mapping_changes_only_delta_invalid_characters():
    revised, mapping = bronze._column_mapping(
        ["contractId", "Project Name", "budget-peso"]
    )

    assert revised == ["contractId", "Project_Name", "budget-peso"]
    assert mapping == {"Project Name": "Project_Name"}


def test_parse_bool_is_explicit():
    assert bronze.parse_bool("true") is True
    assert bronze.parse_bool("FALSE") is False
    with pytest.raises(ValueError):
        bronze.parse_bool("sometimes")


def test_required_alias_match_is_case_insensitive():
    assert bronze._has_required_alias(
        ["ObjectID", "ContractID"],
        ["object_id", "objectid"],
    )
    assert not bronze._has_required_alias(["name", "value"], ["objectid"])


def test_source_header_contract_fails_before_write():
    source = {"required_any_columns": ["objectid", "object_id"]}

    bronze.validate_source_header(source, ["ObjectID", "name"])
    with pytest.raises(ValueError, match="Required source field groups are missing"):
        bronze.validate_source_header(source, ["name", "value"])


def test_every_required_source_field_group_must_be_present():
    source = {
        "required_column_groups": {
            "identifier": ["id", "source_id"],
            "geometry": ["geometry", "geometry_json"],
        }
    }

    bronze.validate_source_header(source, ["source_id", "geometry_json"])
    with pytest.raises(ValueError, match="geometry"):
        bronze.validate_source_header(source, ["source_id", "rating"])


def test_mgb_contract_requires_rating_and_geometry():
    source = config.source_config("flood_susceptibility")

    bronze.validate_source_header(
        source,
        ["flood_susceptibility_code", "geometry_json"],
    )
    with pytest.raises(ValueError, match="geometry"):
        bronze.validate_source_header(source, ["flood_susceptibility_code"])


def test_mgb_rating_codes_have_documented_canonical_levels():
    source = config.source_config("flood_susceptibility")

    assert source["rating_code_map"] == {
        "VHF": "very high",
        "HF": "high",
        "MF": "moderate",
        "LF": "low",
    }
    assert set(source["rating_code_map"].values()) == {
        name for name in source["rating_reference"] if name != "missing"
    }


def test_mgb_missing_rating_values_are_explicit():
    source = config.source_config("flood_susceptibility")

    assert source["missing_rating_values"] == ["No rating"]
    assert "No rating" not in source["rating_code_map"]
    assert source["rating_reference"]["missing"] == 23


def test_current_table_must_match_requested_snapshot_and_artifact():
    metadata = {
        "path": "/Volumes/catalog/source/volume/example.csv",
        "file_name": "example.csv",
        "size_bytes": 100,
        "modified_ns": 123456,
    }
    state = {
        "rows_loaded": 12,
        "identity_nulls": 0,
        "identity_is_single": True,
        "_source_snapshot_id": "snapshot-a",
        "_source_path": metadata["path"],
        "_source_file": metadata["file_name"],
        "_source_file_size_bytes": metadata["size_bytes"],
        "_source_modified_ns": metadata["modified_ns"],
    }

    assert bronze._same_current_table(state, metadata, "snapshot-a", expected_rows=12)
    assert not bronze._same_current_table(
        state, metadata, "snapshot-b", expected_rows=12
    )
    assert not bronze._same_current_table(
        state, metadata, "snapshot-a", expected_rows=13
    )


def test_historical_snapshot_is_not_current_after_a_new_snapshot():
    metadata = {
        "path": "/Volumes/catalog/source/volume/example.csv",
        "file_name": "example.csv",
        "size_bytes": 100,
        "modified_ns": 123456,
    }
    current_b = {
        "rows_loaded": 12,
        "identity_nulls": 0,
        "identity_is_single": True,
        "_source_snapshot_id": "snapshot-b",
        "_source_path": metadata["path"],
        "_source_file": metadata["file_name"],
        "_source_file_size_bytes": metadata["size_bytes"],
        "_source_modified_ns": metadata["modified_ns"],
    }

    assert not bronze._same_current_table(
        current_b,
        metadata,
        "snapshot-a",
        expected_rows=12,
    )


def test_parse_csv_line_preserves_quoted_commas_and_crlf():
    assert bronze._parse_csv_line('"geometry,with,commas",high\r', 2) == [
        "geometry,with,commas",
        "high",
    ]


def test_parse_csv_line_rejects_wrong_width_and_invalid_quotes():
    with pytest.raises(ValueError, match="expected exactly 2"):
        bronze._parse_csv_line("one,two,three", 2)
    with pytest.raises(ValueError, match="unreadable record"):
        bronze._parse_csv_line('"unterminated', 1)


def test_parse_csv_line_reads_geometry_over_default_field_limit():
    geometry = '{"rings":[' + "1" * 200_000 + "]}"
    line = '1,HF,"' + geometry.replace('"', '""') + '"\r'
    assert bronze._parse_csv_line(line, 3) == ["1", "HF", geometry]


def test_parse_csv_line_still_rejects_field_over_raised_limit(monkeypatch):
    monkeypatch.setattr(bronze, "CSV_FIELD_SIZE_LIMIT", 10)
    with pytest.raises(ValueError, match="unreadable record"):
        bronze._parse_csv_line('1,"' + "x" * 11 + '"', 2)


def test_snapshot_conflict_does_not_poison_the_canonical_claim():
    canonical_a = {
        "status": "SUCCESS",
        "rows_loaded": 12,
        "source_path": "/source/a.csv",
    }
    rejected_b = {
        "status": "FAILED",
        "rows_loaded": None,
        "source_path": "/source/b.csv",
    }

    canonical, completed = bronze._snapshot_audit_state([canonical_a, rejected_b])

    assert canonical is canonical_a
    assert completed is canonical_a
