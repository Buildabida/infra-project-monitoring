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


def test_dpwh_sources_enable_quoted_multiline_csv_parsing():
    for source_name in ("dpwh_projects", "flood_control_projects"):
        source = config.source_config(source_name)

        assert source["multi_line"] is True
        assert source["escape_char"] == "\\"


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


def test_failed_attempts_do_not_claim_a_snapshot_id():
    # issue #107: only a completed load claims an ID, so a fixed file can reuse it
    started = {"status": "STARTED", "rows_loaded": None, "source_path": "/a.csv"}
    failed = {"status": "FAILED", "rows_loaded": None, "source_path": "/a.csv"}

    canonical, completed = bronze._snapshot_audit_state([started, failed])

    assert canonical is None
    assert completed is None


def test_first_completed_load_is_the_claim_after_failed_attempts():
    failed = {"status": "FAILED", "rows_loaded": None, "source_path": "/old.csv"}
    success = {"status": "SUCCESS", "rows_loaded": 12, "source_path": "/new.csv"}
    skipped = {
        "status": "SKIPPED_IDEMPOTENT",
        "rows_loaded": 12,
        "source_path": "/new.csv",
    }

    canonical, completed = bronze._snapshot_audit_state([failed, success, skipped])

    assert canonical is success
    assert completed is skipped


def test_parse_csv_line_rejects_two_records_in_one_line():
    # issue #106: a bare line break outside quotes must fail, not drop the second record
    with pytest.raises(ValueError, match="more than one record"):
        bronze._parse_csv_line("a,b\nc,d", 2)


def test_parse_csv_line_keeps_a_line_break_inside_quotes():
    assert bronze._parse_csv_line('a,"two\nlines"', 2) == ["a", "two\nlines"]


def test_header_line_must_match_the_inspected_header():
    header = ["OBJECTID", "FloodSusc", "geometry"]
    bronze._check_header_line("OBJECTID,FloodSusc,geometry", header)
    bronze._check_header_line("﻿OBJECTID,FloodSusc,geometry", header)
    with pytest.raises(ValueError, match="not the CSV header"):
        bronze._check_header_line("1,HF,geometry", header)
    with pytest.raises(ValueError, match="no first line"):
        bronze._check_header_line(None, header)


def test_header_line_must_appear_exactly_once():
    # issue #106: a repeated header or an identical data line must fail, not vanish
    bronze._check_header_count(1)
    for count in (0, 2):
        with pytest.raises(RuntimeError, match="appears"):
            bronze._check_header_count(count)


def test_row_preservation_compares_the_file_with_the_parser_and_the_table():
    # issue #107: a record the parser drops now fails the load
    bronze._check_row_preservation(10, 10, 10)
    with pytest.raises(RuntimeError, match="File-to-parser"):
        bronze._check_row_preservation(11, 10, 10)
    with pytest.raises(RuntimeError, match="Source-to-Bronze"):
        bronze._check_row_preservation(10, 10, 9)
    with pytest.raises(RuntimeError, match="no data rows"):
        bronze._check_row_preservation(0, 0, 0)


def test_logical_csv_count_handles_multiline_fields_and_backslash_quotes(tmp_path):
    path = tmp_path / "multiline.csv"
    path.write_text(
        "id,description,payload\n"
        '1,"first line\nsecond line","{\\"key\\":\\"value\\"}"\n'
        '2,single-line,"{\\"key\\":2}"\n',
        encoding="utf-8",
    )

    assert (
        bronze._count_csv_records(
            path,
            ["id", "description", "payload"],
            escape_char="\\",
        )
        == 2
    )


def test_logical_csv_count_rejects_wrong_record_width(tmp_path):
    path = tmp_path / "wrong-width.csv"
    path.write_text("id,value\n1,valid\n2,too,many\n", encoding="utf-8")

    with pytest.raises(ValueError, match="logical record 2"):
        bronze._count_csv_records(path, ["id", "value"])


class _FakeCatalog:
    def __init__(self, exists):
        self.exists = exists

    def tableExists(self, name):
        return self.exists


class _FakeSpark:
    def __init__(self, exists, version=7):
        self.catalog = _FakeCatalog(exists)
        self.version = version
        self.statements = []

    def sql(self, statement):
        self.statements.append(statement)
        version = self.version

        class _Result:
            def first(self):
                return {"version": version}

        return _Result()


def test_failed_row_check_restores_the_previous_table_version():
    spark = _FakeSpark(exists=True, version=7)
    target = bronze.table_name("flood_susceptibility")

    previous = bronze._table_version(spark, target)
    bronze._undo_write(spark, target, previous)

    assert previous == 7
    assert spark.statements[-1] == f"RESTORE TABLE {target} TO VERSION AS OF 7"


def test_failed_first_load_drops_the_new_table():
    spark = _FakeSpark(exists=False)
    target = bronze.table_name("flood_susceptibility")

    previous = bronze._table_version(spark, target)
    bronze._undo_write(spark, target, previous)

    assert previous is None
    assert spark.statements == [f"DROP TABLE IF EXISTS {target}"]


def test_acceptance_evidence_names_match_the_bronze_validator():
    # issue #108: every check the evidence notebook filters on must exist
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    evidence = (
        root / "notebooks/04_validation/02_bronze_acceptance_evidence.sql"
    ).read_text(encoding="utf-8")
    validator = (root / "notebooks/04_validation/01_validation_bronze.py").read_text(
        encoding="utf-8"
    )
    block = evidence.split("data_quality_check IN (", 1)[1].split(")", 1)[0]
    names = re.findall(r"'([^']+)'", block)
    assert names
    for name in names:
        assert f'"{name}"' in validator, name
    patterns = re.findall(r"data_quality_check LIKE '([^']+)'", evidence)
    assert patterns
    written = re.findall(r'f?"([^"]*row count matches[^"]*)"', validator)
    for pattern in patterns:
        regex = "^" + ".*".join(map(re.escape, pattern.split("%"))) + "$"
        assert any(re.match(regex, name) for name in written), pattern


def test_header_drift_reports_new_and_missing_columns():
    previous = ["contractId", "budget", "status", "_source_snapshot_id"]
    added, removed = bronze.header_drift(["contractId", "budget", "region"], previous)
    assert added == ["region"]
    assert removed == ["status"]


def test_header_drift_sees_a_rename_as_one_removed_and_one_added_column():
    added, removed = bronze.header_drift(
        ["contractId", "contract_amount"], ["contractId", "budget"]
    )
    assert (added, removed) == (["contract_amount"], ["budget"])


def test_header_drift_ignores_case_and_ingestion_metadata():
    previous = ["ContractId", *config.INGEST_METADATA_COLUMNS]
    assert bronze.header_drift(["contractid"], previous) == ([], [])


def test_renamed_required_column_still_blocks_the_load():
    # #48: a renamed critical field is a STOP before any write, not only drift
    source = config.source_config("dpwh_projects")
    header = list(
        dict.fromkeys(
            name
            for aliases in source["required_column_groups"].values()
            for name in aliases[:1]
        )
    )
    bronze.validate_source_header(source, header)
    renamed = ["contract_amount" if name == "budget" else name for name in header]
    with pytest.raises(ValueError, match="reported budget"):
        bronze.validate_source_header(source, renamed)
