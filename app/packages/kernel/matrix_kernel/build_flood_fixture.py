"""Build flood fixtures from open extents (CR-016).

Event path (VAL-02):
  MATRIX_FLOOD_EXTENT or data/raw/flood/s1_gfm_iloilo_2024.geojson
  -> overwrites validation_fixtures/flood2024_closures.json (non-provisional)

Hazard path (open LiPAD — not a 2024-event claim):
  data/raw/flood/lipad_iloilo_fh25yr.geojson
  -> writes validation_fixtures/flood_hazard_lipad_closures.json
  -> leaves VAL-02 provisional fixture untouched

  uv run python -m matrix_kernel.build_flood_fixture
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from matrix_kernel.validation import FLOOD_FIXTURE, FIXTURE_DIR, flood_closures_from_geojson

_REPO = Path(__file__).resolve().parents[4]
_S1_EXTENT = _REPO / "data" / "raw" / "flood" / "s1_gfm_iloilo_2024.geojson"
_LIPAD_EXTENT = _REPO / "data" / "raw" / "flood" / "lipad_iloilo_fh25yr.geojson"
HAZARD_FIXTURE = FIXTURE_DIR / "flood_hazard_lipad_closures.json"


def _dissolve_geometry(geojson: dict) -> dict:
    """Merge FeatureCollection polygons into one MultiPolygon (or return single geom)."""
    if geojson.get("type") == "Feature":
        return geojson["geometry"]
    if geojson.get("type") != "FeatureCollection":
        return geojson
    feats = geojson.get("features") or []
    if not feats:
        raise ValueError("empty FeatureCollection")
    coords: list = []
    for feat in feats:
        g = feat.get("geometry") or {}
        t = g.get("type")
        if t == "Polygon":
            coords.append(g["coordinates"])
        elif t == "MultiPolygon":
            coords.extend(g["coordinates"])
    if not coords:
        raise ValueError("no polygon geometries in FeatureCollection")
    if len(coords) == 1:
        return {"type": "Polygon", "coordinates": coords[0]}
    return {"type": "MultiPolygon", "coordinates": coords}


def resolve_event_extent_path() -> Path | None:
    raw = os.environ.get("MATRIX_FLOOD_EXTENT")
    path = Path(raw) if raw else _S1_EXTENT
    return path if path.is_file() else None


def resolve_lipad_path() -> Path | None:
    return _LIPAD_EXTENT if _LIPAD_EXTENT.is_file() else None


def build_event_fixture(geojson: dict, *, event: str, source_id: str) -> dict:
    closures = flood_closures_from_geojson(geojson)
    if not closures:
        raise RuntimeError(
            "flood_closures_from_geojson returned no edges — check net + geometry"
        )
    observations = [
        {"segment_id": eid, "name": eid, "length_m": round(length, 1)}
        for eid, length in sorted(closures.items())
    ]
    return {
        "fixture_id": "flood2024_closures",
        "gate_id": "VAL-02",
        "title": "2024 Iloilo City flood — sourced extent ∩ SUMO road closures",
        "provisional": False,
        "provenance": (
            f"SOURCED — {source_id} flood extent intersected with SUMO-ILO "
            f"via flood_closures_from_geojson ({len(observations)} edges). "
            f"Built {datetime.now(timezone.utc).date().isoformat()}."
        ),
        "source_dataset_id": source_id,
        "event": event,
        "unit": "length-weighted IoU over closed road segments",
        "transcribed": datetime.now(timezone.utc).date().isoformat(),
        "observations": observations,
        "notes": "Event GT for VAL-02 IoU — not the LiPAD hazard-skill fixture.",
    }


def build_hazard_fixture(geojson: dict) -> dict:
    closures = flood_closures_from_geojson(geojson)
    if not closures:
        raise RuntimeError(
            "LiPAD intersect returned no edges — check net + geometry CRS"
        )
    observations = [
        {"segment_id": eid, "name": eid, "length_m": round(length, 1)}
        for eid, length in sorted(closures.items())
    ]
    return {
        "fixture_id": "flood_hazard_lipad_closures",
        "gate_id": "HAZARD-LIPAD",
        "title": "LiPAD 25yr 10m flood hazard ∩ SUMO roads (open, not 2024-event GT)",
        "provisional": False,
        "provenance": (
            f"SOURCED — LiPAD Phil-LiDAR fh25yr_10m (geonode:ph063022000_fh25yr_10m) "
            f"∩ SUMO-ILO ({len(observations)} edges). "
            f"Built {datetime.now(timezone.utc).date().isoformat()} (CR-016). "
            "Not a substitute for VAL-02 2024-event validation."
        ),
        "source_dataset_id": "LIPAD",
        "event": "hazard_25yr_return",
        "unit": "length-weighted closed road segments",
        "transcribed": datetime.now(timezone.utc).date().isoformat(),
        "observations": observations,
        "notes": (
            "Use for flood-scenario closed_edges / ECO-4 redistribution context. "
            "Classic VAL-02 event gate stays NOT_RUN until an open event extent exists."
        ),
    }


def main() -> int:
    wrote = 0
    lipad = resolve_lipad_path()
    if lipad is not None:
        raw = json.loads(lipad.read_text(encoding="utf-8"))
        geom = _dissolve_geometry(raw)
        fixture = build_hazard_fixture(geom)
        HAZARD_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        HAZARD_FIXTURE.write_text(json.dumps(fixture, indent=2), encoding="utf-8")
        print(
            f"[flood-fixture] hazard wrote {HAZARD_FIXTURE} "
            f"({len(fixture['observations'])} segments)"
        )
        wrote += 1

    event_path = resolve_event_extent_path()
    if event_path is not None:
        # Only treat as VAL-02 event if it is the S1 path or MATRIX_FLOOD_EXTENT
        # explicitly set — not when the only file is LiPAD.
        if event_path.resolve() == _LIPAD_EXTENT.resolve() and not os.environ.get(
            "MATRIX_FLOOD_EXTENT"
        ):
            pass
        else:
            raw = json.loads(event_path.read_text(encoding="utf-8"))
            geom = _dissolve_geometry(raw)
            src = "S1-GFM" if "s1_gfm" in event_path.name.lower() else "FLOOD-EXTENT"
            fixture = build_event_fixture(
                geom,
                event=f"flood event ({event_path.name})",
                source_id=src,
            )
            FLOOD_FIXTURE.write_text(json.dumps(fixture, indent=2), encoding="utf-8")
            print(
                f"[flood-fixture] VAL-02 wrote {FLOOD_FIXTURE} "
                f"({len(fixture['observations'])} segments)"
            )
            wrote += 1

    if wrote == 0:
        print(
            f"[flood-fixture] no extent at {_LIPAD_EXTENT.name} / "
            f"MATRIX_FLOOD_EXTENT / {_S1_EXTENT.name}; "
            "leaving provisional VAL-02 unchanged "
            "(see data/fetch/fetch_lipad_flood.py)",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
