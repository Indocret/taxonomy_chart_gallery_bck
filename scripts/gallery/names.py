from __future__ import annotations

import re
from pathlib import Path


def normalize_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def title_from_slug(slug: str) -> str:
    return " ".join(part.upper() if len(part) <= 3 else part.title() for part in slug.split("_"))


def build_alias_index(config: dict) -> tuple[dict, list[tuple[str, str]]]:
    samples = {}
    alias_entries = []

    for slug, sample_config in (config.get("samples") or {}).items():
        canonical_slug = normalize_key(slug)
        aliases = {
            canonical_slug,
            normalize_key(sample_config.get("title", "")),
            *(normalize_key(alias) for alias in sample_config.get("aliases", [])),
        }
        aliases = {alias for alias in aliases if alias}

        samples[canonical_slug] = {
            "slug": canonical_slug,
            "title": sample_config.get("title") or title_from_slug(canonical_slug),
            "description": sample_config.get("description") or "",
            "aliases": sorted(aliases),
            "polygon": sample_config.get("polygon"),
        }

        for alias in aliases:
            alias_entries.append((alias, canonical_slug))

    alias_entries.sort(key=lambda entry: len(entry[0]), reverse=True)
    return samples, alias_entries


def alias_matches(key: str, alias: str) -> bool:
    if not key or not alias:
        return False

    padded_key = f"_{key}_"
    padded_alias = f"_{alias}_"
    return key == alias or key.startswith(f"{alias}_") or padded_alias in padded_key


def infer_slug_from_name(name: str) -> str:
    base = normalize_key(Path(name).stem)
    suffixes = [
        r"_sankey(_plot|_plots|plot|plots)?$",
        r"_krona(_chart|_plot|_plots|chart|plot|plots)?$",
        r"_taxonomy$",
        r"_chart$",
        r"_plot$",
        r"_plots$",
    ]

    changed = True
    while changed:
        changed = False
        for suffix in suffixes:
            next_base = re.sub(suffix, "", base)
            if next_base != base:
                base = next_base
                changed = True

    return base or "sample"


def sample_for_file(path: Path, aliases: list[tuple[str, str]]) -> str:
    file_keys = [normalize_key(path.stem), normalize_key(path.name)]
    folder_keys = [normalize_key(path.parent.name)]

    for alias, slug in aliases:
        if any(alias_matches(key, alias) for key in file_keys):
            return slug

    for alias, slug in aliases:
        if any(alias_matches(key, alias) for key in folder_keys):
            return slug

    return infer_slug_from_name(path.name)


def chart_kind(path: Path) -> str:
    key = normalize_key(path.stem)

    if "sankey" in key:
        return "sankey"

    if "krona" in key:
        return "krona"

    return "chart"


def chart_label(path: Path) -> str:
    kind = chart_kind(path)

    if kind == "sankey":
        return "Sankey Chart"

    if kind == "krona":
        return "Krona Chart"

    return pretty_stem(path)


def pretty_stem(path: Path) -> str:
    return (
        path.stem
        .replace("_", " ")
        .replace("-", " ")
        .strip()
        .title()
    )
