from __future__ import annotations

from gallery import build_gallery
from gallery.paths import MANIFEST_PATH, ROOT


def main() -> None:
    manifest = build_gallery()
    print(f"Wrote {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"Generated {len(manifest['samples'])} sample(s).")

    for sample in manifest["samples"]:
        print(
            f"- {sample['slug']}: "
            f"{len(sample.get('charts') or [])} chart(s), "
            f"{len(sample.get('workbooks') or [])} workbook(s), "
            f"{'polygon' if sample.get('geojson') else 'no polygon'}"
        )


if __name__ == "__main__":
    main()
