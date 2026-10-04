import pytest

from src import bronze


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
    with pytest.raises(ValueError, match="None of the documented"):
        bronze.validate_source_header(source, ["name", "value"])


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
