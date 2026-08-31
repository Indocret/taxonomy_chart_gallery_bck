from __future__ import annotations

import argparse
import html
from pathlib import Path

from gallery.xlsx_table import first_value_column, normalized_header, numeric_value, read_sheet


def lineage_parts(value: object) -> list[str]:
    text = html.unescape(str(value or "")).replace("\xa0", " ").strip()
    return [part.strip() for part in text.split(">") if part.strip()]


def export_krona_text(workbook: Path, output: Path, sheet: str) -> None:
    rows = read_sheet(workbook, sheet)

    if not rows:
        raise ValueError(f"No rows found in {workbook}")

    header = rows[0]
    header_map = normalized_header(header)
    lineage_index = header_map.get("lineage")
    value_index = first_value_column(header, rows)

    if lineage_index is None:
        raise ValueError("Workbook sheet must contain a lineage column")

    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows[1:]:
            if not row:
                continue

            name = str(row[0] if len(row) > 0 else "").strip()
            value = numeric_value(row[value_index] if value_index < len(row) else 0)

            if not name or value <= 0:
                continue

            path = [*lineage_parts(row[lineage_index] if lineage_index < len(row) else ""), name]
            handle.write("\t".join([str(int(value) if value.is_integer() else value), *path]) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export KronaTools ktImportText input from a taxonomy workbook.")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument("--sheet", default="Species")
    args = parser.parse_args()

    export_krona_text(args.workbook, args.output, args.sheet)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
