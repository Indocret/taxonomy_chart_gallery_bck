from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "gallery.json"
OUTPUT_DIR = ROOT / "charts"
SAMPLES_DIR = OUTPUT_DIR / "samples"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"


def href_for(path: Path) -> str:
    relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    return f"./{quote(relative, safe='/._-~()%')}"


def chart_relative_path(path: Path) -> str:
    return path.resolve().relative_to(OUTPUT_DIR.resolve()).as_posix()


def workbook_viewer_href(workbook_path: Path, title: str) -> str:
    query = (
        f"workbook={quote(chart_relative_path(workbook_path), safe='/._-~()%')}"
        f"&title={quote(title)}"
    )
    return f"./charts/workbook-viewer.html?{query}"


def reset_generated_dir(path: Path) -> None:
    resolved = path.resolve()
    output_root = OUTPUT_DIR.resolve()

    if resolved != output_root and output_root not in resolved.parents:
        raise RuntimeError(f"Refusing to reset a directory outside {OUTPUT_DIR}: {path}")

    if path.exists():
        shutil.rmtree(path)

    path.mkdir(parents=True, exist_ok=True)


def remove_generated_dir(path: Path) -> None:
    resolved = path.resolve()
    output_root = OUTPUT_DIR.resolve()

    if output_root not in resolved.parents:
        raise RuntimeError(f"Refusing to remove a directory outside {OUTPUT_DIR}: {path}")

    if path.exists():
        shutil.rmtree(path)
