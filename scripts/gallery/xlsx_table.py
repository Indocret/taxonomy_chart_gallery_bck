from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


XML_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def package_path(target: str) -> str:
    target = target.lstrip("/")
    return target if target.startswith("xl/") else f"xl/{target}"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def column_index(reference: str) -> int | None:
    match = re.match(r"[A-Z]+", reference or "")

    if not match:
        return None

    index = 0

    for character in match.group(0):
        index = index * 26 + (ord(character) - 64)

    return index - 1


def read_shared_strings(zip_file: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zip_file.read("xl/sharedStrings.xml"))
    except KeyError:
        return []

    strings = []

    for item in root.findall("main:si", XML_NS):
        strings.append("".join(text.text or "" for text in item.findall(".//main:t", XML_NS)))

    return strings


def sheet_targets(zip_file: ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(zip_file.read("xl/workbook.xml"))
    relationships = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels"))
    relationship_map = {
        relationship.attrib["Id"]: relationship.attrib["Target"]
        for relationship in relationships
        if local_name(relationship.tag) == "Relationship"
    }

    sheets = []

    for sheet in workbook.findall("main:sheets/main:sheet", XML_NS):
        relationship_id = sheet.attrib[f"{{{XML_NS['rel']}}}id"]
        sheets.append((sheet.attrib["name"], package_path(relationship_map[relationship_id])))

    return sheets


def cell_value(cell: ET.Element, shared_strings: list[str]) -> object:
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//main:t", XML_NS))

    value_node = cell.find("main:v", XML_NS)

    if value_node is None:
        return ""

    raw_value = value_node.text or ""

    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except (IndexError, ValueError):
            return raw_value

    if cell_type == "b":
        return raw_value == "1"

    try:
        number = float(raw_value)
    except ValueError:
        return raw_value

    if number.is_integer():
        return int(number)

    return number


def trim_row(row: list[object]) -> list[object]:
    while row and row[-1] in ("", None):
        row.pop()
    return row


def read_rows_from_target(zip_file: ZipFile, target: str, shared_strings: list[str]) -> list[list[object]]:
    root = ET.fromstring(zip_file.read(target))
    rows = []

    for row_node in root.findall("main:sheetData/main:row", XML_NS):
        values: list[object] = []

        for cell in row_node.findall("main:c", XML_NS):
            index = column_index(cell.attrib.get("r", ""))

            if index is None:
                index = len(values)

            while len(values) <= index:
                values.append("")

            values[index] = cell_value(cell, shared_strings)

        rows.append(trim_row(values))

    return rows


def read_sheet(path: Path, sheet_name: str) -> list[list[object]]:
    with ZipFile(path) as zip_file:
        shared_strings = read_shared_strings(zip_file)
        targets = dict(sheet_targets(zip_file))

        if sheet_name not in targets:
            available = ", ".join(targets)
            raise ValueError(f"Sheet {sheet_name!r} not found. Available sheets: {available}")

        return read_rows_from_target(zip_file, targets[sheet_name], shared_strings)


def numeric_value(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value or "").replace(",", "").strip()

    if not text:
        return 0

    try:
        return float(text)
    except ValueError:
        return 0


def normalized_header(row: list[object]) -> dict[str, int]:
    return {
        re.sub(r"[^a-z0-9]+", "_", str(label).lower()).strip("_"): index
        for index, label in enumerate(row)
    }


def first_value_column(header: list[object], rows: list[list[object]]) -> int:
    ignored = {"taxrank", "taxid", "lineage"}

    for index, label in enumerate(header):
        key = re.sub(r"[^a-z0-9]+", "_", str(label).lower()).strip("_")

        if index == 0 or key in ignored or not key:
            continue

        if any(index < len(row) and numeric_value(row[index]) > 0 for row in rows[1:25]):
            return index

    raise ValueError("Could not find a numeric abundance/count column")
