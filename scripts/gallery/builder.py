from __future__ import annotations

import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .geojson import (
    is_geojson_file,
    polygon_geojson_from_config,
    polygon_metadata,
    polygon_metadata_from_payload,
)
from .names import (
    build_alias_index,
    chart_kind,
    chart_label,
    pretty_stem,
    sample_for_file,
    title_from_slug,
)
from .paths import (
    CONFIG_PATH,
    MANIFEST_PATH,
    OUTPUT_DIR,
    ROOT,
    SAMPLES_DIR,
    href_for,
    remove_generated_dir,
    reset_generated_dir,
    workbook_viewer_href,
)
from .workbook import workbook_sheet_count


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {
            "title": "Taxonomic Chart Gallery",
            "description": "Interactive taxonomic visualizations.",
            "sourceDirectories": ["."],
            "samples": {},
        }

    return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))


def classify_file(path: Path) -> str | None:
    suffix = path.suffix.lower()

    if suffix == ".xlsx":
        return "workbook"

    if suffix == ".html":
        return "chart"

    if suffix in {".geojson", ".json"} and is_geojson_file(path):
        return "polygon"

    return None


def discover_source_files(config: dict) -> list[Path]:
    source_files = []

    for source in config.get("sourceDirectories") or ["."]:
        source_path = (ROOT / source).resolve()

        if not source_path.exists():
            print(f"Warning: source directory does not exist: {source}")
            continue

        for path in source_path.rglob("*"):
            if not path.is_file():
                continue

            resolved = path.resolve()

            if OUTPUT_DIR.resolve() in resolved.parents:
                continue

            if "_reference" in resolved.parts:
                continue

            if classify_file(path):
                source_files.append(path)

    return source_files


def ensure_sample_definition(samples: dict, slug: str) -> dict:
    if slug not in samples:
        samples[slug] = {
            "slug": slug,
            "title": title_from_slug(slug),
            "description": "",
            "aliases": [slug],
        }

    return samples[slug]


def copy_source_file(path: Path, sample_dir: Path) -> Path:
    sample_dir.mkdir(parents=True, exist_ok=True)
    destination = sample_dir / path.name
    shutil.copy2(path, destination)
    return destination


def chart_links_for(files: list[Path], sample_output_dir: Path) -> list[dict]:
    chart_files = sorted(files, key=lambda item: item.name.lower())
    kind_counts = Counter(chart_kind(path) for path in chart_files)
    links = []

    for chart in chart_files:
        copied = copy_source_file(chart, sample_output_dir)
        kind = chart_kind(chart)
        label = chart_label(chart)

        if kind_counts[kind] > 1:
            label = f"{label}: {pretty_stem(chart)}"

        links.append(
            {
                "kind": kind,
                "label": label,
                "fileName": chart.name,
                "href": href_for(copied),
            }
        )

    return links


def copied_workbooks_for(files: list[Path], sample_output_dir: Path) -> list[dict]:
    workbooks = []

    for workbook in sorted(files, key=lambda item: item.name.lower()):
        copied = copy_source_file(workbook, sample_output_dir)
        workbooks.append(
            {
                "fileName": workbook.name,
                "href": href_for(copied),
                "path": copied,
                "sheetCount": workbook_sheet_count(workbook),
            }
        )

    return workbooks


def polygon_for(files: list[Path], slug: str, definition: dict, sample_output_dir: Path) -> dict | None:
    for polygon_file in sorted(files, key=lambda item: item.name.lower()):
        copied = copy_source_file(polygon_file, sample_output_dir)
        metadata = polygon_metadata(polygon_file, href_for(copied))

        if metadata:
            return metadata

    config_polygon = polygon_geojson_from_config(slug, definition)

    if not config_polygon:
        return None

    sample_output_dir.mkdir(parents=True, exist_ok=True)
    polygon_path = sample_output_dir / f"{slug}.geojson"
    polygon_path.write_text(
        json.dumps(config_polygon, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return polygon_metadata_from_payload(config_polygon, polygon_path.name, href_for(polygon_path))


def sample_links(chart_links: list[dict], copied_workbooks: list[dict], title: str) -> list[dict]:
    links = [*chart_links]

    for workbook in copied_workbooks:
        label = "Entire Taxonomy"

        if len(copied_workbooks) > 1:
            label = f"Entire Taxonomy: {Path(workbook['fileName']).stem}"

        links.append(
            {
                "kind": "viewer",
                "label": label,
                "href": workbook_viewer_href(workbook["path"], title),
            }
        )

    return links


def build_gallery() -> dict:
    config = load_config()
    sample_defs, aliases = build_alias_index(config)
    grouped_files: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))

    for path in discover_source_files(config):
        kind = classify_file(path)

        if not kind:
            continue

        slug = sample_for_file(path, aliases)
        ensure_sample_definition(sample_defs, slug)
        grouped_files[slug][kind].append(path)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reset_generated_dir(SAMPLES_DIR)
    remove_generated_dir(OUTPUT_DIR / "data")

    samples = []

    for slug in sorted(grouped_files):
        definition = sample_defs[slug]
        files = grouped_files[slug]
        sample_output_dir = SAMPLES_DIR / slug

        chart_links = chart_links_for(files.get("chart", []), sample_output_dir)
        copied_workbooks = copied_workbooks_for(files.get("workbook", []), sample_output_dir)
        polygon = polygon_for(files.get("polygon", []), slug, definition, sample_output_dir)
        links = sample_links(chart_links, copied_workbooks, definition["title"])
        description = (
            "Interactive charts, boundary preview, and entire taxonomy."
            if polygon
            else "Interactive charts and entire taxonomy."
        )

        samples.append(
            {
                "slug": slug,
                "title": definition["title"],
                "description": definition.get("description") or description,
                "aliases": definition.get("aliases", []),
                "geojson": {"href": polygon["href"]} if polygon else None,
                "polygon": polygon,
                "charts": chart_links,
                "workbooks": [
                    {
                        "fileName": workbook["fileName"],
                        "href": workbook["href"],
                        "sheetCount": workbook["sheetCount"],
                    }
                    for workbook in copied_workbooks
                ],
                "workbook": {
                    "fileName": copied_workbooks[0]["fileName"] if copied_workbooks else "",
                    "href": copied_workbooks[0]["href"] if copied_workbooks else "",
                    "sheetCount": copied_workbooks[0]["sheetCount"] if copied_workbooks else 0,
                },
                "links": links,
            }
        )

    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "title": config.get("title") or "Taxonomic Chart Gallery",
        "description": config.get("description") or "",
        "samples": samples,
    }

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest
