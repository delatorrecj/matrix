# Outreach / acquisition — Copernicus GFM Sentinel-1 2024 Iloilo flood (VAL-02)

> **Blocks:** publishing VAL-02 IoU. Until a sourced extent lands, VAL-02 stays **NOT_RUN**
> (never compute IoU against the provisional street-name fixture — PRD-F14).

| | |
|---|---|
| **Product** | Copernicus Global Flood Monitoring (GFM) — Sentinel-1 derived flood extent |
| **Target event** | 2024 Iloilo City significant flood (match CDRRMO / news dates when selecting the product) |
| **INVENTORY id** | `S1-GFM` (⏳) |
| **Save target** | `data/raw/flood/s1_gfm_iloilo_2024.geojson` (or `.tif` + polygonize) |
| **License** | Copernicus open; attribute GFM / ESA as required |

## Download steps (human)

1. Open the Copernicus Emergency / GFM portal (or WEkEO / Copernicus Data Space) and search
   **flood extent** products covering **Iloilo City** (~bbox 10.65–10.78 N, 122.50–122.61 E)
   for the **2024** flood window used in MATRIX validation.
2. Export flood extent as **GeoJSON** (Polygon/MultiPolygon) or GeoTIFF → polygonize to GeoJSON.
3. Save to `data/raw/flood/s1_gfm_iloilo_2024.geojson` (create `data/raw/flood/` if missing).
4. Set env for the report builder (optional override):
   `MATRIX_FLOOD_EXTENT=path/to/s1_gfm_iloilo_2024.geojson`
5. Rebuild the observed fixture + validation report:
   ```bash
   cd app/packages/kernel
   uv run python -m matrix_kernel.build_flood_fixture   # writes non-provisional flood2024_closures.json
   uv run python -m matrix_kernel.build_validation_report
   ```

## What the code does once the file exists

- `flood_closures_from_geojson` intersects the extent with the SUMO net → `edge_id → length_m`.
- Observed fixture `validation_fixtures/flood2024_closures.json` is rewritten with those edges,
  `provisional: false`, and sourced provenance (no `PROVISIONAL_MARK`).
- `generate()` runs a flood-closure simulated side and passes `flood_simulated` into
  `run_validation_gates` → live IoU PASS/FAIL.

Until the GeoJSON exists, `generate()` keeps VAL-02 **NOT_RUN**.

## Automated attempt (2026-08-05)

Script: [`data/fetch/fetch_s1_gfm_iloilo.py`](../fetch/fetch_s1_gfm_iloilo.py) (EODC STAC `GFM`, Equi7→WGS84 window).

**Result: BLOCKED** — see [`data/raw/flood/S1_GFM_ACQUISITION.md`](../raw/flood/S1_GFM_ACQUISITION.md).
City Proper windows are mostly GFM exclusion/nodata (`255`); best 2024 flood pixel count
inside the bbox was **1** (below the script’s usability floor). Documented CDRRMO urban
pluvial events are not represented as usable GFM observed-flood polygons for VAL-02.

**Next human options:** GFM portal max-flood GeoJSON (account) for a multi-month AOI; or
CDRRMO closed-road list as an independent observed side (still do not use the provisional
street-name fixture as GT).
