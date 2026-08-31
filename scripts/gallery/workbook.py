from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


XML_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def workbook_sheet_count(path: Path) -> int:
    with ZipFile(path) as zip_file:
        workbook = ET.fromstring(zip_file.read("xl/workbook.xml"))
        return len(workbook.findall("main:sheets/main:sheet", XML_NS))
