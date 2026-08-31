# BCK Taxonomic Chart Gallery

Static GitHub Pages gallery for BCK taxonomy outputs.

The site is generated from files in `source/` and publishes:

- sample cards for `BCKK-H`, `BCKK-L`, `BCKOT-Hi`, and `BCKOT-Ti`
- farm boundary previews from GeoJSON polygons
- links to each Krona and Sankey HTML chart
- an `Entire Taxonomy` workbook viewer for each XLSX file

## Local Preview

```powershell
python scripts\generate_gallery.py
python -m http.server 5500
```

Open `http://localhost:5500/`.

## Project Layout

```text
config/gallery.json                    sample names and aliases
source/                                source XLSX, HTML, and GeoJSON files
scripts/generate_gallery.py            static gallery generator
scripts/gallery/                       generator modules
scripts/gallery-page.js                homepage renderer
charts/manifest.json                   generated gallery manifest
charts/samples/<sample>/               generated sample artifacts
charts/workbook-viewer.html            shared XLSX viewer
```

## Deployment

The GitHub Actions workflow in `.github/workflows/pages.yml` regenerates the gallery on every push to `main` and deploys the generated `dist/` artifact to GitHub Pages.
