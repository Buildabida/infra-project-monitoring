"""Tests for src/xlsx.py, the Excel reader behind the PSGC, Table B and Table C loads."""

import json
import zipfile

from src import xlsx

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOCUMENT_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def make_book(path, shared_strings, rows_xml):
    """Write the smallest workbook we can read: one sheet named PSGC."""
    with zipfile.ZipFile(path, "w") as book:
        book.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{MAIN}" xmlns:r="{DOCUMENT_REL}">'
            '<sheets><sheet name="PSGC" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>",
        )
        book.writestr(
            "xl/_rels/workbook.xml.rels",
            f'<Relationships xmlns="{PACKAGE_REL}">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml" '
            f'Type="{DOCUMENT_REL}/worksheet"/>'
            "</Relationships>",
        )
        items = "".join(
            f'<si><t xml:space="preserve">{text}</t></si>' for text in shared_strings
        )
        book.writestr("xl/sharedStrings.xml", f'<sst xmlns="{MAIN}">{items}</sst>')
        book.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{MAIN}"><sheetData>{rows_xml}</sheetData></worksheet>',
        )


def test_reads_shared_inline_sparse_scientific_and_cached_formula(tmp_path):
    path = tmp_path / "fixture.xlsx"
    make_book(
        path,
        ["shared"],
        '<row r="1">'
        '<c r="A1" t="s"><v>0</v></c>'
        '<c r="C1" t="inlineStr"><is><t>inline</t></is></c>'
        '<c r="D1"><v>1.1855975E7</v></c>'
        '<c r="E1"><f>1+1</f><v>2</v></c>'
        "</row>",
    )

    assert xlsx.sheet_names(path) == ["PSGC"]
    assert xlsx.read_sheet(path, "PSGC") == [
        (1, ["shared", "", "inline", "1.1855975E7", "2"])
    ]


def test_keeps_the_exact_cell_text(tmp_path):
    path = tmp_path / "fixture.xlsx"
    make_book(
        path,
        ["CITY OF LAMITAN ", "Total \nPopulation"],
        '<row r="4"><c r="D4" t="s"><v>1</v></c></row>'
        '<row r="8"><c r="B8" t="s"><v>0</v></c><c r="D8"><v>116652</v></c></row>',
    )

    assert xlsx.read_sheet(path) == [
        (4, ["", "", "", "Total \nPopulation"]),
        (8, ["", "CITY OF LAMITAN ", "", "116652"]),
    ]
    assert xlsx.one_line("Total \nPopulation") == "total population"


def test_turns_cell_text_into_numbers():
    assert xlsx.to_number("92,337,852 a") == 92_337_852
    assert xlsx.to_number("1.1855975E7") == 11_855_975
    assert xlsx.to_number("-25.5") == -25.5
    assert xlsx.to_number("not a number") is None
    assert xlsx.to_number("") is None
    assert xlsx.to_number(None) is None
    assert xlsx.to_count(" 1224 ") == 1224
    assert xlsx.to_count("12.5") is None


def read_table_c_row(cells):
    """The Table C rule, as in the notebook: a place in column B and a whole number in column D."""
    first, place, middle, count = cells
    if first.strip() or middle.strip():
        return "has text in column A or C"
    if not place.strip():
        return "has no place in column B"
    if xlsx.to_count(count) is None:
        return "has no whole number in column D"
    return None


def manifest(row):
    """A manifest row with its column names, so the test reads like the table."""
    names = [column.split()[0] for column in xlsx.MANIFEST_COLUMNS.split(", ")]
    return dict(zip(names, row, strict=True))


def test_sorts_every_row_of_a_sheet_once():
    rows = [
        (1, ["Total Population by Province, City, Municipality, and Barangay"]),
        (2, ["as of 01 July 2024"]),
        (4, ["Province, City, Municipality", "", "", "Total \nPopulation"]),
        (6, ["", "BASILAN *", "", "541947"]),
        (7, ["", "", "", "", "", "", "", "1"]),
        (8, ["", "CITY OF LAMITAN ", "", "116652", "", "", "check", "1"]),
        (9, ["", "Arco", "", "not counted"]),
        (11, ["Note:"]),
        (12, ["* Excludes City of Isabela."]),
        (14, ["Source:", "", "", ""]),
    ]

    data, manifest_row, issues = xlsx.sort_sheet(
        "BARMM_1.xlsx", "Basilan", rows, 2, 4, read_table_c_row
    )

    assert data == [
        (6, ["", "BASILAN *", "", "541947"]),
        (8, ["", "CITY OF LAMITAN ", "", "116652"]),
    ]
    assert manifest(manifest_row) == {
        "source_file": "BARMM_1.xlsx",
        "sheet_name": "Basilan",
        "is_data_sheet": True,
        "skip_reason": None,
        "physical_row_count": 10,
        "header_row_number": 4,
        "title_and_header_row_count": 3,
        "blank_row_count": 1,
        "note_row_count": 3,
        "expected_non_data_row_count": 7,
        "parsed_data_row_count": 2,
        "parse_issue_row_count": 1,
    }
    assert issues == [
        (
            "BARMM_1.xlsx",
            "Basilan",
            9,
            json.dumps(["", "Arco", "", "not counted"]),
            "has no whole number in column D",
        )
    ]


def test_text_before_the_notes_is_a_parse_issue():
    rows = [
        (1, ["Place", "", "", "Total Population"]),
        (2, ["stray text"]),
        (3, ["Note:"]),
        (4, ["a note"]),
    ]

    _, manifest_row, issues = xlsx.sort_sheet(
        "file.xlsx", "Sheet", rows, 0, 4, read_table_c_row
    )

    assert [issue[2] for issue in issues] == [2]
    assert manifest(manifest_row)["note_row_count"] == 2


def test_a_skipped_sheet_counts_all_its_rows_as_non_data():
    rows = [(1, ["B. POPULATION AND ANNUAL POPULATION GROWTH RATE"]), (4, ["REGION"])]

    row = manifest(xlsx.skipped_sheet("NCR_2.xlsx", "Table B", rows, "not Table C"))

    assert row["is_data_sheet"] is False
    assert row["skip_reason"] == "not Table C"
    assert row["physical_row_count"] == row["expected_non_data_row_count"] == 2
    assert row["parsed_data_row_count"] == row["parse_issue_row_count"] == 0
