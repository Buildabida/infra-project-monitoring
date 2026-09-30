"""Read Excel files with only the Python standard library, so nothing has to be installed.

Bronze keeps every cell as PSA wrote it. These helpers only read the file and sort its rows.
"""

import json
import re
import zipfile
from xml.etree import ElementTree

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_RELS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# PSA ends its sheets with notes and sources, in the first column.
NOTE_STARTS = ("note:", "notes:", "source:", "sources:")

# The columns of the sheet manifest and parse issue tables that bronze.save_parse_audit saves.
MANIFEST_COLUMNS = (
    "source_file string, sheet_name string, is_data_sheet boolean, skip_reason string, "
    "physical_row_count long, header_row_number long, title_and_header_row_count long, "
    "blank_row_count long, note_row_count long, expected_non_data_row_count long, "
    "parsed_data_row_count long, parse_issue_row_count long"
)
ISSUE_COLUMNS = (
    "source_file string, sheet_name string, source_row_number long, "
    "raw_cells_json string, reason string"
)


def _tag(name):
    return f"{{{MAIN}}}{name}"


def _column(ref):
    """Turn a cell name like C12 into a column number, starting at 0."""
    number = 0
    for letter in re.match(r"[A-Z]+", ref).group(0):
        number = number * 26 + ord(letter) - 64
    return number - 1


def _sheets(book):
    workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
    links = ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    targets = {
        link.get("Id"): link.get("Target")
        for link in links.iter(f"{{{RELS}}}Relationship")
    }
    sheets = {}
    for sheet in workbook.iter(_tag("sheet")):
        target = targets[sheet.get(f"{{{DOC_RELS}}}id")].lstrip("/")
        sheets[sheet.get("name")] = (
            target if target.startswith("xl/") else f"xl/{target}"
        )
    return sheets


def sheet_names(path):
    """List the sheet names in the order Excel shows them, exactly as they are written."""
    with zipfile.ZipFile(path) as book:
        return list(_sheets(book))


def read_sheet(path, name=None):
    """Return one sheet as a list of (row number, cells). No name means the first sheet.

    Every cell is its exact text, with any spaces. Excel leaves out rows that have
    nothing in them, so the row numbers can skip.
    """
    with zipfile.ZipFile(path) as book:
        sheets = _sheets(book)
        target = sheets[name] if name else next(iter(sheets.values()))
        shared = []
        if "xl/sharedStrings.xml" in book.namelist():
            strings = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
            shared = [
                "".join(t.text or "" for t in item.iter(_tag("t")))
                for item in strings.iter(_tag("si"))
            ]
        sheet = ElementTree.fromstring(book.read(target))

    rows = []
    for row in sheet.iter(_tag("row")):
        cells = []
        for cell in row.iter(_tag("c")):
            ref = cell.get("r")
            column = _column(ref) if ref else len(cells)
            kind = cell.get("t")
            value = cell.find(_tag("v"))
            if kind == "s":
                text = shared[int(value.text)]
            elif kind == "inlineStr":
                text = "".join(t.text or "" for t in cell.iter(_tag("t")))
            else:
                text = value.text if value is not None and value.text else ""
            cells.extend([""] * (column + 1 - len(cells)))
            cells[column] = text
        rows.append((int(row.get("r")), cells))
    return rows


def to_number(text):
    """Turn cell text like '92,337,852 a' or '1.1855975E7' into a number. Return None if it is not one."""
    match = re.match(r"^-?[\d,]*\.?\d+(?:[eE][-+]?\d+)?", (text or "").strip())
    if not match:
        return None
    number = float(match.group(0).replace(",", ""))
    return int(number) if number.is_integer() else number


def to_count(text):
    """Turn cell text into a whole number, like a population. Return None if it is not one."""
    number = to_number(text)
    return number if isinstance(number, int) else None


def one_line(text):
    """The text on one line and in lower case, so a header that breaks over two lines still matches."""
    return " ".join(text.split()).casefold()


def is_blank(cells):
    """True if every cell is empty or only spaces."""
    return not any(cell.strip() for cell in cells)


def starts_notes(cells):
    """True if the row starts the notes at the end of a PSA sheet, like "Note:" or "Source:"."""
    return bool(cells) and one_line(cells[0]).startswith(NOTE_STARTS)


def sort_sheet(source_file, sheet_name, rows, header_position, width, read_row):
    """Sort the rows of one sheet, so every row is counted once.

    The rows down to the header are titles and headers. Each row under the header is blank,
    a data row, a note at the end of the sheet, or a parse issue. Only the first `width`
    columns are the table. read_row(cells) is the rule for one source: it returns None for
    a data row, or the reason it can't read the row.

    Returns (data rows as (row number, table cells), the manifest row, the parse issue rows).
    """
    data, issues = [], []
    blank = notes = 0
    in_notes = False
    for row_number, cells in rows[header_position + 1 :]:
        table = (cells + [""] * width)[:width]
        if is_blank(table):
            blank += 1
            continue
        reason = read_row(table)
        if reason is None:
            data.append((row_number, table))
            continue
        in_notes = in_notes or starts_notes(table)
        if in_notes and is_blank(table[1:]):
            notes += 1
            continue
        raw_cells = json.dumps(cells, ensure_ascii=False)
        issues.append((source_file, sheet_name, row_number, raw_cells, reason))

    titles = header_position + 1
    non_data = titles + blank + notes
    if non_data + len(data) + len(issues) != len(rows):
        raise RuntimeError(f"The rows of {source_file} / {sheet_name} don't add up.")
    manifest_row = (
        source_file,
        sheet_name,
        True,
        None,
        len(rows),
        rows[header_position][0],
        titles,
        blank,
        notes,
        non_data,
        len(data),
        len(issues),
    )
    return data, manifest_row, issues


def skipped_sheet(source_file, sheet_name, rows, reason):
    """The manifest row for a sheet we don't load. All its rows count as non-data rows."""
    return (
        source_file,
        sheet_name,
        False,
        reason,
        len(rows),
        None,
        0,
        0,
        0,
        len(rows),
        0,
        0,
    )
