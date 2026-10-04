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
    revised, mapping = bronze._column_mapping(["contractId", "Project Name", "budget-peso"])

    assert revised == ["contractId", "Project_Name", "budget-peso"]
    assert mapping == {"Project Name": "Project_Name"}


def test_parse_bool_is_explicit():
    assert bronze.parse_bool("true") is True
    assert bronze.parse_bool("FALSE") is False
    with pytest.raises(ValueError):
        bronze.parse_bool("sometimes")
