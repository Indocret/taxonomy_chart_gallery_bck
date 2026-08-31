from __future__ import annotations

import json
import re
from pathlib import Path


def is_geojson_file(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        return False

    return isinstance(payload, dict) and payload.get("type") in {
        "FeatureCollection",
        "Feature",
        "Polygon",
        "MultiPolygon",
        "GeometryCollection",
    }


def valid_coordinate(coordinate: object) -> bool:
    return (
        isinstance(coordinate, list)
        and len(coordinate) >= 2
        and isinstance(coordinate[0], (int, float))
        and isinstance(coordinate[1], (int, float))
    )


def collect_polygon_rings(geojson: dict, rings: list, geometry_types: set[str]) -> None:
    geo_type = geojson.get("type")

    if geo_type:
        geometry_types.add(geo_type)

    if geo_type == "FeatureCollection":
        for feature in geojson.get("features") or []:
            if isinstance(feature, dict):
                collect_polygon_rings(feature, rings, geometry_types)
        return

    if geo_type == "Feature":
        geometry = geojson.get("geometry")
        if isinstance(geometry, dict):
            collect_polygon_rings(geometry, rings, geometry_types)
        return

    if geo_type == "GeometryCollection":
        for geometry in geojson.get("geometries") or []:
            if isinstance(geometry, dict):
                collect_polygon_rings(geometry, rings, geometry_types)
        return

    if geo_type == "Polygon":
        for ring in geojson.get("coordinates") or []:
            coordinates = [point[:2] for point in ring if valid_coordinate(point)]
            if len(coordinates) > 1:
                rings.append(coordinates)
        return

    if geo_type == "MultiPolygon":
        for polygon in geojson.get("coordinates") or []:
            for ring in polygon:
                coordinates = [point[:2] for point in ring if valid_coordinate(point)]
                if len(coordinates) > 1:
                    rings.append(coordinates)


def polygon_metadata_from_payload(payload: dict, file_name: str, href: str) -> dict | None:
    rings: list[list[list[float]]] = []
    geometry_types: set[str] = set()

    collect_polygon_rings(payload, rings, geometry_types)

    if not rings:
        return None

    longitudes = [point[0] for ring in rings for point in ring]
    latitudes = [point[1] for ring in rings for point in ring]

    return {
        "fileName": file_name,
        "href": href,
        "ringCount": len(rings),
        "geometryTypes": sorted(geometry_types),
        "bounds": {
            "minLon": min(longitudes),
            "maxLon": max(longitudes),
            "minLat": min(latitudes),
            "maxLat": max(latitudes),
        },
    }


def polygon_metadata(path: Path, href: str) -> dict | None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return polygon_metadata_from_payload(payload, path.name, href)


def parse_wkt_polygon(wkt: str) -> list[list[list[float]]]:
    text = str(wkt or "").strip()
    match = re.match(r"^POLYGON\s*\(\((.*)\)\)\s*$", text, flags=re.IGNORECASE | re.DOTALL)

    if not match:
        raise ValueError("Only POLYGON WKT is supported in config/gallery.json polygon.wkt")

    rings = []

    for ring_text in re.split(r"\)\s*,\s*\(", match.group(1)):
        ring = []

        for pair in ring_text.split(","):
            parts = pair.strip().split()

            if len(parts) < 2:
                continue

            ring.append([float(parts[0]), float(parts[1])])

        if ring and ring[0] != ring[-1]:
            ring.append(ring[0])

        if len(ring) > 3:
            rings.append(ring)

    if not rings:
        raise ValueError("No valid polygon coordinates found in WKT")

    return rings


def polygon_geojson_from_config(slug: str, sample_definition: dict) -> dict | None:
    polygon_config = sample_definition.get("polygon")

    if not isinstance(polygon_config, dict):
        return None

    if polygon_config.get("geojson"):
        return polygon_config["geojson"]

    coordinates = polygon_config.get("coordinates")

    if not coordinates and polygon_config.get("wkt"):
        coordinates = parse_wkt_polygon(polygon_config["wkt"])

    if not coordinates:
        return None

    properties = {
        "sample": slug,
        "name": sample_definition.get("title") or slug,
        **(polygon_config.get("properties") or {}),
    }

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": properties,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coordinates,
                },
            }
        ],
    }
