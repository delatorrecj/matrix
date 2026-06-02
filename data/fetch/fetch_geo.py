#!/usr/bin/env python3
"""MATRIX — heavy geo fetch (run on demand; needs extra packages).

Overture Maps (buildings, POIs, transportation) for the Iloilo bbox, plus
pointers for raster layers (land cover, DEM) that need rasterio/GDAL.

    pip install overturemaps
    python fetch/fetch_geo.py

Rasters (WorldCover, GLO-30 DEM) are Cloud-Optimized GeoTIFFs — do a windowed
read with rasterio rather than downloading whole tiles. Snippets printed below.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

# overturemaps CLI writes GeoJSON with the OS default codec; on Windows that's
# cp1252 and it crashes on non-Latin1 chars (№, İ, …) in place names. Force UTF-8.
ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")

OUT = Path(__file__).resolve().parents[1] / "raw" / "overture"
# Overture bbox order is minx,miny,maxx,maxy = W,S,E,N
BBOX = "122.50,10.65,122.61,10.78"

# Overture type -> output filename
TYPES = {
    "building": "iloilo_buildings.geojson",
    "place": "iloilo_places_poi.geojson",
    "segment": "iloilo_transport_segments.geojson",
    "connector": "iloilo_transport_connectors.geojson",
    "land_use": "iloilo_land_use.geojson",
    "infrastructure": "iloilo_infrastructure.geojson",
}

RASTER_NOTE = f"""
== rasters (need: pip install rasterio) ==
WorldCover 10m land cover (CC BY 4.0), windowed read for the Iloilo bbox:
    import rasterio
    from rasterio.windows import from_bounds
    url = "https://esa-worldcover.s3.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N09E120_Map.tif"
    with rasterio.open(url) as ds:
        win = from_bounds(122.50, 10.65, 122.61, 10.78, ds.transform)
        arr = ds.read(1, window=win)   # -> save to raw/landcover/iloilo_worldcover.tif

Copernicus GLO-30 DEM (open) tile index:
    https://copernicus-dem-30m.s3.amazonaws.com/  (tile: Copernicus_DSM_COG_10_N10_00_E122_00_DEM)
"""


def have(cmd):
    return shutil.which(cmd) is not None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if not have("overturemaps"):
        print("overturemaps CLI not found.  pip install overturemaps")
        print(RASTER_NOTE)
        return 1
    for typ, fname in TYPES.items():
        dest = OUT / fname
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  skip  {typ}: exists")
            continue
        print(f"  fetch {typ} -> raw/overture/{fname}")
        cmd = ["overturemaps", "download", f"--bbox={BBOX}",
               "-f", "geojson", f"--type={typ}", "-o", str(dest)]
        try:
            subprocess.run(cmd, check=True, env=ENV)
        except subprocess.CalledProcessError as e:
            print(f"  FAIL  {typ}: {e}")
    print(RASTER_NOTE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
