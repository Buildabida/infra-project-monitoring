"""Read Excel files with only the Python standard library, so nothing has to be installed."""

import re
import zipfile
from xml.etree import ElementTree

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_RELS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


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
    """List the sheet names in the order Excel shows them."""
    with zipfile.ZipFile(path) as book:
        return list(_sheets(book))


def read_sheet(path, name=None):
    """Return one sheet as a list of (row number, cells). Every cell is text. No name means the first sheet."""
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
            cells[column] = text.strip()
        rows.append((int(row.get("r")), cells))
    return rows


def to_number(text):
    """Turn cell text like '92,337,852 a' or '1.1855975E7' into a number. Return None if it is not one."""
    match = re.match(r"^-?[\d,]*\.?\d+(?:[eE][-+]?\d+)?", (text or "").strip())
    if not match:
        return None
    number = float(match.group(0).replace(",", ""))
    return int(number) if number.is_integer() else number
