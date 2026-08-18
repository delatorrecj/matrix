#!/usr/bin/env python3
"""Subset data/raw/osm/iloilo_osm.json into the committed CI OSM fixture.

The Overpass dump is gitignored (~11 MB). CI does not run this script — it
consumes the committed app/packages/data/fixtures/iloilo_city_proper.osm.
"""
from __future__ import annotations

import json
import xml.sax.saxutils as sax
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "data" / "raw" / "osm" / "iloilo_osm.json"
OUT = Path(__file__).resolve().parent / "fixtures" / "iloilo_city_proper.osm"

# City Proper + inner Diversion (lat_min, lon_min, lat_max, lon_max)
BBOX = (10.690, 122.548, 10.732, 122.576)

KEEP_HIGHWAY = frozenset({
    "motorway", "motorway_link", "trunk", "trunk_link",
    "primary", "primary_link", "secondary", "secondary_link",
    "tertiary", "tertiary_link", "residential", "living_street",
    "unclassified", "service",
})


def _in_bbox(lat: float, lon: float) -> bool:
    lat_min, lon_min, lat_max, lon_max = BBOX
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def _enrich_name(tags: dict[str, str]) -> dict[str, str]:
    """Keep colloquial / Calderon aliases on `name` so keyword tests resolve."""
    tags = dict(tags)
    name = tags.get("name", "")
    old = tags.get("old_name", "")
    if "iznart" in old.lower() and "iznart" not in name.lower():
        name = f"{name};Iznart Street" if name else "Iznart Street"
    if "aquino jr" in name.lower() and "diversion" not in name.lower():
        name = f"{name};Diversion Road" if name else "Diversion Road"
    if name:
        tags["name"] = name
    return tags


def main() -> int:
    if not SRC.is_file():
        print(f"missing {SRC} — run data/fetch/fetch_open.py first", flush=True)
        return 1

    data = json.loads(SRC.read_text(encoding="utf-8"))
    elements = data["elements"]

    node_coords: dict[int, tuple[float, float]] = {}
    node_tags: dict[int, dict[str, str]] = {}
    for e in elements:
        if e["type"] == "node":
            node_coords[e["id"]] = (e["lat"], e["lon"])
            if e.get("tags"):
                node_tags[e["id"]] = e["tags"]
    for e in elements:
        if e["type"] == "way":
            for nid, g in zip(e.get("nodes", []), e.get("geometry", [])):
                node_coords.setdefault(nid, (g["lat"], g["lon"]))

    ways = []
    used_nodes: set[int] = set()
    for e in elements:
        if e["type"] != "way":
            continue
        tags = e.get("tags") or {}
        if tags.get("highway") not in KEEP_HIGHWAY:
            continue
        geom = e.get("geometry") or []
        if not any(_in_bbox(g["lat"], g["lon"]) for g in geom):
            continue
        nids = [nid for nid in e.get("nodes", []) if nid in node_coords]
        if len(nids) < 2:
            continue
        ways.append({"id": e["id"], "nodes": nids, "tags": _enrich_name(tags)})
        used_nodes.update(nids)

    def esc(s: object) -> str:
        return sax.escape(str(s)).replace('"', "&quot;")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    lat_min, lon_min, lat_max, lon_max = BBOX
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write("<!-- MATRIX CI fixture. Source: OSM ODbL (OSM-ILO). -->\n")
        f.write(f"<!-- bbox: {lat_min},{lon_min},{lat_max},{lon_max} -->\n")
        f.write('<osm version="0.6" generator="MATRIX/extract_ci_osm.py">\n')
        for nid in sorted(used_nodes):
            lat, lon = node_coords[nid]
            tags = node_tags.get(nid)
            if tags:
                f.write(f'  <node id="{nid}" lat="{lat}" lon="{lon}" version="1">\n')
                for k, v in tags.items():
                    f.write(f'    <tag k="{esc(k)}" v="{esc(v)}"/>\n')
                f.write("  </node>\n")
            else:
                f.write(f'  <node id="{nid}" lat="{lat}" lon="{lon}" version="1"/>\n')
        for way in ways:
            f.write(f'  <way id="{way["id"]}" version="1">\n')
            for nid in way["nodes"]:
                f.write(f'    <nd ref="{nid}"/>\n')
            for k, v in way["tags"].items():
                f.write(f'    <tag k="{esc(k)}" v="{esc(v)}"/>\n')
            f.write("  </way>\n")
        f.write("</osm>\n")

    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)  "
          f"nodes={len(used_nodes):,} ways={len(ways):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
