"""Export the Iloilo SUMO net as GeoJSON layers for the web frontend (CR-007 PR 7).

Generates two files in app/apps/web/public/layers/:

  edges.geojson       — LineString per trafficked SUMO edge, keyed by the real
                        SUMO edge id (must match Trajectory.edge_counts keys).
                        Replaces the PROVISIONAL placeholder edge ids.

  confidence.geojson  — Regular grid of 500 m polygon cells covering the pilot
                        area bounding box.  Every cell is tier M (the conservative
                        overall simulation confidence, pending mode-share calibration
                        in PR 9).  BEH-1/BEH-3/ECO-1 are H along network corridors,
                        but mapping that spatially requires a network-edge intersection
                        pass that is not yet wired; a uniform-M grid is more honest
                        than the previous hand-drawn H/M/L polygons.

Filters edges.geojson to the baseline-trafficked set (those with demand in Redis)
to keep the file size manageable (~6,600 edges vs. 36,557 total).  Falls back to
ALL non-internal named edges if Redis is unavailable.

Run (Docker + Redis up, baseline already seeded):
    cd app/packages/kernel
    uv run python ../../packages/data/export_net_geojson.py

Or from repo root:
    cd app/packages/kernel && uv run python ../data/export_net_geojson.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── resolve output path (repo-agnostic) ──────────────────────────────────────
_HERE = Path(__file__).resolve()
# packages/data/ -> packages/ -> app/ -> project root
_APP_ROOT = _HERE.parents[2]   # app/
_LAYERS_DIR = _APP_ROOT / "apps" / "web" / "public" / "layers"
_EDGES_OUT = _LAYERS_DIR / "edges.geojson"
_CONF_OUT = _LAYERS_DIR / "confidence.geojson"

_COORD_PLACES = 6   # ~10 cm precision; keeps file size down


def _round_coord(lonlat: tuple[float, float]) -> list[float]:
    return [round(lonlat[0], _COORD_PLACES), round(lonlat[1], _COORD_PLACES)]


def export_edges(net, trafficked_ids: set[str] | None) -> dict:
    """Build the edges FeatureCollection from the SUMO net."""
    features: list[dict] = []
    skipped_no_shape = 0
    skipped_not_in_net = 0

    candidates = trafficked_ids if trafficked_ids else None

    for edge in net.getEdges():
        eid = edge.getID()
        # Skip internal junction connectors
        if eid.startswith(":"):
            continue
        # Filter to trafficked if we have a set
        if candidates is not None and eid not in candidates:
            continue

        shape = edge.getShape()
        if not shape:
            skipped_no_shape += 1
            continue

        try:
            coords = [_round_coord(net.convertXY2LonLat(x, y)) for x, y in shape]
        except Exception:
            skipped_no_shape += 1
            continue

        name = edge.getName() or None
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "edge_id": eid,
                "name": name,
                "length_m": round(edge.getLength(), 1),
                "num_lanes": edge.getLaneNumber(),
            },
        })

    print(f"[edges] exported {len(features)} features "
          f"(skipped {skipped_no_shape} no-shape, {skipped_not_in_net} not-in-net)",
          file=sys.stderr)

    return {
        "type": "FeatureCollection",
        "_provenance": {
            "status": "REAL",
            "source": "Iloilo SUMO net (iloilo.net.xml, built by build_network.py "
                      "--output.street-names); see CR-007 PR 5a for street-name rationale "
                      "and CR-007 PR 7 for this export.",
            "filter": ("baseline-trafficked edges (those with demand in Redis nightly "
                       "baseline)" if candidates else
                       "all non-internal named edges (Redis unavailable — fallback)"),
            "coordinate_precision": f"{_COORD_PLACES} decimal places (~10 cm)",
            "generated": datetime.now(timezone.utc).isoformat(),
            "n_features": len(features),
        },
        "features": features,
    }


def _bbox_to_grid(lon_min: float, lat_min: float, lon_max: float, lat_max: float,
                  cell_deg: float) -> list[dict]:
    """Regular polygon grid over [lon_min,lon_max] × [lat_min,lat_max].

    Returns one GeoJSON Polygon Feature per cell.
    """
    cells: list[dict] = []
    lon = lon_min
    while lon < lon_max:
        lat = lat_min
        while lat < lat_max:
            lon_e = min(round(lon + cell_deg, _COORD_PLACES), lon_max)
            lat_n = min(round(lat + cell_deg, _COORD_PLACES), lat_max)
            ring = [
                [round(lon, _COORD_PLACES), round(lat, _COORD_PLACES)],
                [lon_e,                     round(lat, _COORD_PLACES)],
                [lon_e,                     lat_n],
                [round(lon, _COORD_PLACES), lat_n],
                [round(lon, _COORD_PLACES), round(lat, _COORD_PLACES)],
            ]
            cells.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "properties": {
                    "confidence": "M",
                    "basis": "M-overall (see _provenance; CR-007 PR 7)",
                },
            })
            lat = round(lat + cell_deg, _COORD_PLACES)
        lon = round(lon + cell_deg, _COORD_PLACES)
    return cells


def export_confidence(net) -> dict:
    """Build the confidence grid from the net's bounding box."""
    # net.getBBoxXY() returns ((xmin,ymin),(xmax,ymax)) in SUMO projection
    (xmin, ymin), (xmax, ymax) = net.getBBoxXY()
    lon_min, lat_min = net.convertXY2LonLat(xmin, ymin)
    lon_max, lat_max = net.convertXY2LonLat(xmax, ymax)
    # Ensure correct order (convertXY2LonLat is monotone but let's be safe)
    if lon_min > lon_max:
        lon_min, lon_max = lon_max, lon_min
    if lat_min > lat_max:
        lat_min, lat_max = lat_max, lat_min

    # ~500 m cell at ~11° N latitude: 500 m ≈ 0.0045° lon, 0.0045° lat
    cell_deg = 0.0045

    cells = _bbox_to_grid(lon_min, lat_min, lon_max, lat_max, cell_deg)
    print(f"[confidence] exported {len(cells)} grid cells "
          f"({lon_min:.4f},{lat_min:.4f})→({lon_max:.4f},{lat_max:.4f}) "
          f"cell={cell_deg}°",
          file=sys.stderr)

    return {
        "type": "FeatureCollection",
        "_provenance": {
            "status": "REAL",
            "source": "Generated from Iloilo SUMO net bounding box (iloilo.net.xml); CR-007 PR 7.",
            "tier_rationale": (
                "All cells are M (conservative overall simulation confidence). "
                "Data inputs CCHAIN/OSM/LIPAD are H, but uncalibrated mode-share (PR 9) "
                "and literature-calibrated methods cap most results at M (methods §2 "
                "method_capped_confidence rule, ratified CR-007 PR 6). "
                "BEH-1/BEH-3 and ECO-1 are H along the network corridors; a "
                "spatially-varying H/M grid requires a network-edge intersection pass "
                "not yet wired — uniform M is the honest floor until calibration lands (PR 9)."
            ),
            "generated": datetime.now(timezone.utc).isoformat(),
            "n_cells": len(cells),
            "cell_size_deg": cell_deg,
            "cell_size_approx_m": 500,
        },
        "features": cells,
    }


def main() -> int:
    # Import the kernel's net loader (handles SUMO env setup)
    try:
        from matrix_kernel.runner import _net
    except ImportError as e:
        print(f"[error] kernel import failed — run from kernel venv: {e}", file=sys.stderr)
        return 1

    print("[net] loading iloilo.net.xml ...", file=sys.stderr)
    net = _net()

    # Try to load the baseline for the trafficked-edge filter
    trafficked: set[str] | None = None
    try:
        from matrix_kernel.baseline import load_baseline
        bl = load_baseline()
        trafficked = set(bl.edge_counts.keys())
        print(f"[baseline] {len(trafficked)} trafficked edge ids loaded from Redis",
              file=sys.stderr)
    except Exception as exc:
        print(f"[baseline] unavailable ({exc}); exporting all non-internal named edges",
              file=sys.stderr)

    _LAYERS_DIR.mkdir(parents=True, exist_ok=True)

    # ── edges.geojson ──
    edges_geojson = export_edges(net, trafficked)
    _EDGES_OUT.write_text(
        json.dumps(edges_geojson, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    size_kb = _EDGES_OUT.stat().st_size // 1024
    print(f"[ok] wrote {_EDGES_OUT}  ({size_kb} KB)", file=sys.stderr)

    # ── confidence.geojson ──
    conf_geojson = export_confidence(net)
    _CONF_OUT.write_text(
        json.dumps(conf_geojson, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    size_kb = _CONF_OUT.stat().st_size // 1024
    print(f"[ok] wrote {_CONF_OUT}  ({size_kb} KB)", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
