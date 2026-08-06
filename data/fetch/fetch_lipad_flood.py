#!/usr/bin/env python3
"""Download open LiPAD Iloilo 10 m flood-hazard (WFS GeoJSON) — no registration.

  python data/fetch/fetch_lipad_flood.py

Writes:
  data/raw/flood/lipad_iloilo_fh25yr.geojson

Layer: geonode:ph063022000_fh25yr_10m (City of Iloilo, 25-year return).
CR-016 open-data-only substitute for agency flood closures / GFM event GT.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "raw" / "flood" / "lipad_iloilo_fh25yr.geojson"
# Prefer GeoJSON; fall back documented in OPEN_REFRESH.md
WFS = (
    "https://lipad-fmc.dream.upd.edu.ph/geoserver/wfs"
    "?service=WFS&version=1.0.0&request=GetFeature"
    "&typeName=geonode:ph063022000_fh25yr_10m"
    "&outputFormat=application/json"
    "&srsName=EPSG:4326"
)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.is_file() and OUT.stat().st_size > 1000:
        # Re-fetch if stored CRS looks projected (not lon/lat)
        try:
            sample = json.loads(OUT.read_text(encoding="utf-8"))
            pos = sample["features"][0]["geometry"]["coordinates"]
            while isinstance(pos[0], (list, tuple)):
                pos = pos[0]
            if abs(float(pos[0])) <= 180 and abs(float(pos[1])) <= 90:
                print(f"  skip  LIPAD-FH25: exists ({OUT.stat().st_size:,} B)")
                return 0
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            pass
        print("  re-fetch LIPAD-FH25: existing file not EPSG:4326")
    req = urllib.request.Request(
        WFS,
        headers={"User-Agent": "MATRIX-data-fetch", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            payload = r.read()
    except Exception as e:
        print(f"  FAIL  LIPAD-FH25: {e}", file=sys.stderr)
        return 1
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        print("  FAIL  LIPAD-FH25: response not JSON", file=sys.stderr)
        return 1
    feats = data.get("features") or []
    if not feats:
        print("  FAIL  LIPAD-FH25: empty FeatureCollection", file=sys.stderr)
        return 1
    # Keep medium/high hazard classes (Var >= 1); drop no-hazard / low if coded below.
    kept = [
        f
        for f in feats
        if float((f.get("properties") or {}).get("Var") or 0) >= 1
    ]
    if kept:
        feats = kept
    meta = {
        "type": "FeatureCollection",
        "features": feats,
        "properties": {
            "source": "LiPAD / Phil-LiDAR (UP DREAM)",
            "layer": "geonode:ph063022000_fh25yr_10m",
            "srs": "EPSG:4326",
            "return_period_yr": 25,
            "resolution_m": 10,
            "hazard_filter": "Var>=1",
            "license": "open research product — attribute UP DREAM / Phil-LiDAR",
            "url": WFS.split("?")[0],
        },
    }
    OUT.write_text(json.dumps(meta), encoding="utf-8")
    print(f"  OK    LIPAD-FH25: {len(feats):,} features, {OUT.stat().st_size:,} B -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
