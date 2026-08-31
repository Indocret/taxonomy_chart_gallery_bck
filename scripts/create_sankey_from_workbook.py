from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path

from gallery.xlsx_table import first_value_column, normalized_header, numeric_value, read_sheet


def lineage_parts(value: object) -> list[str]:
    text = html.unescape(str(value or "")).replace("\xa0", " ").strip()
    return [part.strip() for part in text.split(">") if part.strip()]


def build_sankey(rows: list[list[object]], top: int, min_value: float) -> dict:
    if not rows:
        raise ValueError("No rows found")

    header = rows[0]
    header_map = normalized_header(header)
    lineage_index = header_map.get("lineage")
    value_index = first_value_column(header, rows)

    if lineage_index is None:
        raise ValueError("Workbook sheet must contain a lineage column")

    records = []

    for row in rows[1:]:
        name = str(row[0] if len(row) > 0 else "").strip()
        value = numeric_value(row[value_index] if value_index < len(row) else 0)

        if not name or value < min_value:
            continue

        path = [*lineage_parts(row[lineage_index] if lineage_index < len(row) else ""), name]

        if len(path) > 1:
            records.append((value, path))

    records.sort(key=lambda item: item[0], reverse=True)
    records = records[:top]
    node_ids = {}
    labels = []
    links = defaultdict(float)

    def node_index(parts: list[str]) -> int:
        node_id = " > ".join(parts)

        if node_id not in node_ids:
            node_ids[node_id] = len(labels)
            labels.append(parts[-1])

        return node_ids[node_id]

    for value, path in records:
        for index in range(len(path) - 1):
            source = node_index(path[: index + 1])
            target = node_index(path[: index + 2])
            links[(source, target)] += value

    return {
        "labels": labels,
        "source": [source for source, _ in links],
        "target": [target for _, target in links],
        "value": [value for value in links.values()],
    }


def write_sankey_html(payload: dict, output: Path, title: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    data_json = json.dumps(payload, ensure_ascii=False)
    title_json = json.dumps(title, ensure_ascii=False)

    output.write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    html, body, #chart {{
      width: 100%;
      height: 100%;
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
    }}
  </style>
</head>
<body>
  <div id="chart"></div>
  <script>
    const payload = {data_json};
    Plotly.newPlot('chart', [{{
      type: 'sankey',
      arrangement: 'snap',
      node: {{
        pad: 14,
        thickness: 14,
        line: {{ color: 'rgba(20, 34, 48, 0.25)', width: 0.5 }},
        label: payload.labels
      }},
      link: {{
        source: payload.source,
        target: payload.target,
        value: payload.value
      }}
    }}], {{
      title: {title_json},
      margin: {{ l: 20, r: 20, t: 55, b: 20 }},
      font: {{ size: 11 }}
    }}, {{ responsive: true }});
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a standalone Sankey HTML plot from a taxonomy workbook.")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument("--sheet", default="Species")
    parser.add_argument("--top", type=int, default=500)
    parser.add_argument("--min-value", type=float, default=1)
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    rows = read_sheet(args.workbook, args.sheet)
    payload = build_sankey(rows, args.top, args.min_value)
    title = args.title or f"{args.workbook.stem} Sankey Chart"
    write_sankey_html(payload, args.output, title)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
