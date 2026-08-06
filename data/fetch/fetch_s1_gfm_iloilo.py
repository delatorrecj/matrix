"""Fetch Copernicus GFM Sentinel-1 ensemble flood extent for Iloilo → GeoJSON.

Queries the public EODC STAC (`GFM` collection), reprojects the City Proper
bbox into the Equi7 tile CRS, picks the 2024 scene with the most flood pixels
(value==1), polygonizes, writes:

  data/raw/flood/s1_gfm_iloilo_2024.geojson

Known limitation (2026-08-05 acquisition): GFM NRT ensemble over Iloilo City
Proper is dominated by exclusion/nodata (255); 2024 urban pluvial floods are
largely undetected (≤2 flood px metro-wide). Exit 2 = no usable extent.

Usage:
  cd app/packages/kernel
  uv run python ../../../data/fetch/fetch_s1_gfm_iloilo.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "raw" / "flood" / "s1_gfm_iloilo_2024.geojson"
STATUS = REPO / "data" / "raw" / "flood" / "S1_GFM_ACQUISITION.md"
# Iloilo City Proper (lon/lat)
BBOX = (122.50, 10.65, 122.61, 10.78)
DATETIME = "2024-01-01T00:00:00Z/2024-12-31T23:59:59Z"
MIN_FLOOD_PX = 50  # below this, extent is not useful for VAL-02 road IoU


def _post_search(*, limit: int = 100, token: str | None = None) -> dict:
    body: dict = {
        "collections": ["GFM"],
        "bbox": list(BBOX),
        "datetime": DATETIME,
        "limit": limit,
    }
    if token:
        body["token"] = token
    req = urllib.request.Request(
        "https://stac.eodc.eu/api/v1/search",
        data=json.dumps(body).encode(),
        headers={"User-Agent": "MATRIX-data-fetch", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def _all_features(max_pages: int = 5) -> list[dict]:
    data = _post_search()
    feats = list(data.get("features") or [])
    pages = 1
    while pages < max_pages:
        next_href = None
        for link in data.get("links") or []:
            if link.get("rel") == "next":
                next_href = link.get("href")
                break
        if not next_href:
            break
        req = urllib.request.Request(next_href, headers={"User-Agent": "MATRIX-data-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read().decode())
        feats.extend(data.get("features") or [])
        pages += 1
    return feats


def _window_flood_count(href: str) -> tuple[int, dict]:
    with rasterio.open(href) as ds:
        tb = transform_bounds("EPSG:4326", ds.crs, *BBOX)
        win = from_bounds(*tb, transform=ds.transform)
        arr = ds.read(1, window=win, boundless=True, fill_value=255)
        flood = int(np.sum(arr == 1))
        uniq = {int(v): int(c) for v, c in zip(*np.unique(arr, return_counts=True))}
        return flood, {"crs": str(ds.crs), "unique": uniq, "shape": list(arr.shape)}


def _polygonize(href: str) -> list:
    with rasterio.open(href) as ds:
        tb = transform_bounds("EPSG:4326", ds.crs, *BBOX)
        win = from_bounds(*tb, transform=ds.transform)
        arr = ds.read(1, window=win, boundless=True, fill_value=255)
        transform = ds.window_transform(win)
        mask = arr == 1
        coords = []
        for geom, val in shapes(arr, mask=mask, transform=transform):
            if int(val) != 1:
                continue
            # shapes emit Polygon in the raster CRS — reproject to WGS84
            from rasterio.warp import transform_geom

            g84 = transform_geom(ds.crs, "EPSG:4326", geom)
            if g84["type"] == "Polygon":
                coords.append(g84["coordinates"])
            elif g84["type"] == "MultiPolygon":
                coords.extend(g84["coordinates"])
        return coords


def _write_status(*, matched: int, best: dict | None, note: str) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# S1-GFM acquisition attempt — Iloilo 2024",
        "",
        f"- **Date:** 2026-08-05",
        f"- **STAC:** https://stac.eodc.eu/api/v1 (collection `GFM`)",
        f"- **Bbox (City Proper):** `{BBOX}`",
        f"- **Scenes scanned:** {matched}",
        f"- **Best flood pixel count in bbox:** {(best or {}).get('flood_px', 0)}",
        f"- **Best item:** `{(best or {}).get('id', '—')}`",
        f"- **Outcome:** {note}",
        "",
        "## Blocker",
        "",
        "GFM ensemble observed-flood tiles covering Iloilo are mostly **exclusion/nodata",
        "(255)** over the urban core. Documented 2024 urban pluvial floods (e.g. 2024-06-11,",
        "2024-07-17, 2024-09-17 CDRRMO events) do **not** appear as usable GFM flood polygons",
        "for VAL-02 road IoU. Portal max-flood GeoJSON (account) may still help; LiPAD 5/25yr",
        "hazard is a separate open substitute for ECO-4, not VAL-02 event GT.",
        "",
        "Until a sourced multi-segment extent lands at `s1_gfm_iloilo_2024.geojson`,",
        "`build_flood_fixture` stays exit-2 and VAL-02 remains **NOT_RUN**.",
        "",
    ]
    STATUS.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    feats = _all_features()
    if not feats:
        _write_status(matched=0, best=None, note="No STAC hits")
        print("[s1-gfm] no STAC hits", file=sys.stderr)
        return 1

    best: tuple[int, dict, str] | None = None
    for f in feats:
        href = (f.get("assets") or {}).get("ensemble_flood_extent", {}).get("href")
        if not href:
            continue
        try:
            n, meta = _window_flood_count(href)
        except Exception as e:
            print(f"[s1-gfm] skip {f.get('id')}: {e}", file=sys.stderr)
            continue
        if n > 0:
            print(f"[s1-gfm] {f.get('id')} flood_px={n} unique={meta['unique']}")
        if best is None or n > best[0]:
            best = (n, f, href)

    best_info = None
    if best is not None:
        best_info = {
            "flood_px": best[0],
            "id": best[1].get("id"),
            "href": best[2],
            "datetime": (best[1].get("properties") or {}).get("datetime"),
        }

    if best is None or best[0] < MIN_FLOOD_PX:
        note = (
            f"BLOCKED — best flood_px={0 if best is None else best[0]} "
            f"< MIN_FLOOD_PX={MIN_FLOOD_PX}; GeoJSON not written"
        )
        _write_status(matched=len(feats), best=best_info, note=note)
        print(f"[s1-gfm] {note}", file=sys.stderr)
        print(f"[s1-gfm] status -> {STATUS}")
        return 2

    n, f, href = best
    coords = _polygonize(href)
    if not coords:
        _write_status(matched=len(feats), best=best_info, note="polygonize empty")
        return 1

    out = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "source": "Copernicus GFM / EODC STAC",
                    "collection": "GFM",
                    "item_id": f.get("id"),
                    "datetime": (f.get("properties") or {}).get("datetime"),
                    "asset": "ensemble_flood_extent",
                    "bbox": list(BBOX),
                    "flood_pixel_count": n,
                    "href": href,
                    "license": "Copernicus open — attribute GFM / ESA",
                },
                "geometry": {"type": "MultiPolygon", "coordinates": coords},
            }
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out), encoding="utf-8")
    _write_status(
        matched=len(feats),
        best=best_info,
        note=f"OK — wrote {OUT.name} ({len(coords)} rings, {n} flood px)",
    )
    print(f"[s1-gfm] wrote {OUT} ({len(coords)} polygons, {n} flood px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
