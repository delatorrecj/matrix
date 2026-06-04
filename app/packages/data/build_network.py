#!/usr/bin/env python3
"""Phase 1.1 — Build SUMO network + barangay TAZ for Iloilo City pilot.

Glass-box provenance
--------------------
Network  input_dataset_ids: ["OSM-ILO"]   confidence: H
TAZ      input_dataset_ids: ["CCHAIN"]    confidence: H

Input datasets (raw/, gitignored, already fetched):
  data/raw/osm/iloilo_osm.json         OSM-ILO  Overpass API JSON (out geom fmt)
  data/raw/hdx/brgy_geography.csv      CCHAIN   barangay WKT polygons, 180 brgy

Outputs (written to packages/kernel/data/, committed):
  iloilo.net.xml   SUMO road network for Iloilo City Proper
  iloilo.taz.xml   barangay traffic assignment zones

Intermediate (temp, cleaned up after stage2):
  packages/kernel/data/iloilo.osm      OSM XML passed to netconvert

Requirements:
  Stage 1  pure Python (stdlib + json) — no deps
  Stage 2  Docker   ghcr.io/eclipse-sumo/sumo:latest  (for netconvert)
  Stage 3  sumolib  app/.venv  (coordinate projection lat/lon → SUMO XY)

Usage (from app/ directory):
  python packages/data/build_network.py          # full pipeline
  python packages/data/build_network.py --stage 1  # JSON  → iloilo.osm only
  python packages/data/build_network.py --stage 2  # netconvert (needs stage 1)
  python packages/data/build_network.py --stage 3  # TAZ (needs stage 2)

Canonical references:
  docs/methods-matrix.md  §2 (confidence rubric)
  docs/implementation-plan-matrix.md  Phase 1 / Gate 1
  docs/implementation-plan-critical-path.md  §2 S1
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
import subprocess
import sys
import xml.sax.saxutils as sax
from pathlib import Path

# ─── canonical paths ─────────────────────────────────────────────────────────

REPO        = Path(__file__).resolve().parents[3]   # D:\PROJECTS\matrix
APP         = Path(__file__).resolve().parents[2]   # …/app
DATA_RAW    = REPO / "data" / "raw"
KERNEL_DATA = APP / "packages" / "kernel" / "data"
VENV_SP     = APP / ".venv" / "Lib" / "site-packages"
SUMO_IMG    = "ghcr.io/eclipse-sumo/sumo:latest"

# ─── glass-box metadata stamped into every output ───────────────────────────

NET_PROVENANCE = {
    "input_dataset_ids": ["OSM-ILO"],
    "confidence": "H",
    "bbox_swne": "10.65,122.50,10.78,122.61",
    "generator": "build_network.py stage1+stage2 (Phase 1.1)",
}
TAZ_PROVENANCE = {
    "input_dataset_ids": ["CCHAIN"],
    "confidence": "H",
    "brgy_pcode_prefix": "PH063022",  # Iloilo City
    "generator": "build_network.py stage3 (Phase 1.1)",
}

# ─── stage 1 — Overpass JSON → OSM XML ──────────────────────────────────────

def stage1_json_to_osm() -> Path:
    """Convert iloilo_osm.json (Overpass out geom) to standard OSM XML.

    The Overpass query used `out geom`, so every way element has its node
    coordinates embedded inline — we reconstruct proper OSM node elements
    from those coordinates rather than re-fetching.  Explicit node elements
    (332) are preserved with their tags (PT stops, traffic signals, etc.).

    Returns the path to the written iloilo.osm file.
    """
    json_path = DATA_RAW / "osm" / "iloilo_osm.json"
    osm_path  = KERNEL_DATA / "iloilo.osm"
    KERNEL_DATA.mkdir(parents=True, exist_ok=True)

    print(f"[stage1] loading {json_path} …")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    elements = data["elements"]

    # ── Build node_id → (lat, lon) + tags from two sources ──
    node_coords: dict[int, tuple[float, float]] = {}
    node_tags:   dict[int, dict[str, str]]      = {}

    # Priority 1: explicit node elements (may carry extra tags)
    for e in elements:
        if e["type"] == "node":
            node_coords[e["id"]] = (e["lat"], e["lon"])
            if e.get("tags"):
                node_tags[e["id"]] = e["tags"]

    # Priority 2: inline geometry from ways (covers all way-internal nodes)
    for e in elements:
        if e["type"] == "way":
            for nid, g in zip(e.get("nodes", []), e.get("geometry", [])):
                if nid not in node_coords:
                    node_coords[nid] = (g["lat"], g["lon"])

    ways      = [e for e in elements if e["type"] == "way"]
    relations = [e for e in elements if e["type"] == "relation"]

    # Validate completeness — every way node must be in node_coords
    missing = 0
    for w in ways:
        for nid in w.get("nodes", []):
            if nid not in node_coords:
                missing += 1
    if missing:
        print(f"[stage1] WARNING: {missing} node refs have no coordinates — "
              f"they will be omitted from the OSM XML (may cause netconvert errors)")

    print(f"[stage1] nodes={len(node_coords):,}  ways={len(ways):,}  "
          f"relations={len(relations)}  (PT route rels: "
          f"{sum(1 for r in relations if r.get('tags',{}).get('route') in ('bus','tram','train','subway'))})")
    print(f"[stage1] writing -> {osm_path}")

    def esc(s: str) -> str:
        return sax.escape(str(s)).replace('"', "&quot;")

    with open(osm_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(f'<!-- MATRIX build_network.py — Phase 1.1 -->\n')
        f.write(f'<!-- input_dataset_ids: {NET_PROVENANCE["input_dataset_ids"]} -->\n')
        f.write(f'<!-- confidence: {NET_PROVENANCE["confidence"]} -->\n')
        f.write(f'<!-- bbox: {NET_PROVENANCE["bbox_swne"]} -->\n')
        f.write('<osm version="0.6" generator="MATRIX/build_network.py">\n')

        # ── nodes ──
        for nid, (lat, lon) in node_coords.items():
            tags = node_tags.get(nid)
            if tags:
                f.write(f'  <node id="{nid}" lat="{lat}" lon="{lon}" version="1">\n')
                for k, v in tags.items():
                    f.write(f'    <tag k="{esc(k)}" v="{esc(v)}"/>\n')
                f.write('  </node>\n')
            else:
                f.write(f'  <node id="{nid}" lat="{lat}" lon="{lon}" version="1"/>\n')

        # ── ways ──
        for way in ways:
            f.write(f'  <way id="{way["id"]}" version="1">\n')
            for nid in way.get("nodes", []):
                if nid in node_coords:           # only emit refs we have coords for
                    f.write(f'    <nd ref="{nid}"/>\n')
            for k, v in way.get("tags", {}).items():
                f.write(f'    <tag k="{esc(k)}" v="{esc(v)}"/>\n')
            f.write('  </way>\n')

        # ── relations (49 PT route relations) ──
        for rel in relations:
            f.write(f'  <relation id="{rel["id"]}" version="1">\n')
            for m in rel.get("members", []):
                role = esc(m.get("role", ""))
                f.write(f'    <member type="{m["type"]}" ref="{m["ref"]}" role="{role}"/>\n')
            for k, v in rel.get("tags", {}).items():
                f.write(f'    <tag k="{esc(k)}" v="{esc(v)}"/>\n')
            f.write('  </relation>\n')

        f.write('</osm>\n')

    size = osm_path.stat().st_size
    print(f"[stage1] OK wrote {osm_path.name} ({size:,} bytes)")
    return osm_path


# ─── stage 2 — netconvert (via Docker) ───────────────────────────────────────

# Highway types to keep — all modes MATRIX simulates: vehicle + pedestrian + bike
_KEEP_TYPES = ",".join([
    "highway.motorway", "highway.motorway_link",
    "highway.trunk", "highway.trunk_link",
    "highway.primary", "highway.primary_link",
    "highway.secondary", "highway.secondary_link",
    "highway.tertiary", "highway.tertiary_link",
    "highway.residential", "highway.living_street",
    "highway.unclassified", "highway.service",
    "highway.pedestrian", "highway.footway",
    "highway.cycleway", "highway.path",
])


def _windows_path_for_docker(p: Path) -> str:
    """Convert a Windows absolute path to the format Docker Desktop accepts.

    Docker Desktop on Windows (with WSL2 backend) accepts both `C:\\...` and
    `/c/...` forms.  We use the POSIX-style /drive/... form which works for
    both Git-Bash and PowerShell-launched Docker.
    """
    abs_str = str(p.resolve())
    # e.g. D:\\PROJECTS\\... → /d/PROJECTS/...
    drive, rest = os.path.splitdrive(abs_str)
    posix_rest  = rest.replace("\\", "/")
    return f"/{drive[0].lower()}{posix_rest}"


def stage2_netconvert(osm_path: Path, net_path: Path) -> Path:
    """Run netconvert inside the SUMO Docker image → iloilo.net.xml.

    Both osm_path and net_path must live in the same directory so a single
    Docker volume mount covers both.  The intermediate .osm is removed after
    a successful run to keep the committed data directory clean.
    """
    if not osm_path.exists():
        raise FileNotFoundError(f"stage1 output not found: {osm_path}")

    data_dir = net_path.parent
    data_dir.mkdir(parents=True, exist_ok=True)

    if osm_path.parent != data_dir:
        raise ValueError("osm_path and net_path must be in the same directory "
                         "so a single -v mount covers both")

    mount_src = _windows_path_for_docker(data_dir)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{mount_src}:/data",
        SUMO_IMG,
        "netconvert",
        # ── input / output ──
        "--osm-files",            f"/data/{osm_path.name}",
        "--output-file",          f"/data/{net_path.name}",
        # ── network simplification ──
        "--geometry.remove",      "true",
        "--roundabouts.guess",    "true",
        "--junctions.join",       "true",
        "--remove-edges.isolated",
        # ── multi-modal completeness ──
        "--keep-edges.by-type",   _KEEP_TYPES,
        "--sidewalks.guess",      "true",
        "--crossings.guess",      "true",
        # ── junction / lane detail ──
        "--no-internal-links",    "false",
        "--osm.turn-lanes",
        # ── output metadata ──
        "--output.original-names",
        "--xml-validation",       "never",   # suppress DTD warnings
    ]

    print(f"[stage2] running netconvert inside {SUMO_IMG} …")
    print(f"[stage2] mount: {data_dir!s} → /data  (Docker: {mount_src})")

    result = subprocess.run(cmd, capture_output=True, text=True)

    # netconvert writes progress to stderr even on success — always show last lines
    nc_log = (result.stdout + result.stderr).strip()
    for line in nc_log.splitlines()[-20:]:
        print(f"  [nc] {line}")

    if result.returncode != 0:
        print("\n[stage2] FULL netconvert stderr:")
        print(result.stderr)
        raise RuntimeError(f"netconvert exited {result.returncode} — see output above")

    if not net_path.exists():
        raise FileNotFoundError(
            f"netconvert returned 0 but {net_path} not found — check the mount path")

    # Clean up intermediate .osm (it's regenerable from the raw JSON)
    osm_path.unlink()
    print(f"[stage2] removed intermediate {osm_path.name}")

    size = net_path.stat().st_size
    print(f"[stage2] OK wrote {net_path.name} ({size:,} bytes)")
    return net_path


# ─── stage 3 — barangay TAZ polygons ─────────────────────────────────────────

def _load_sumolib():
    """Add the venv site-packages to sys.path so sumolib is importable."""
    sp = str(VENV_SP)
    if sp not in sys.path:
        sys.path.insert(0, sp)
    try:
        import sumolib  # type: ignore[import]
        return sumolib
    except ImportError as e:
        raise ImportError(
            f"sumolib not found in {VENV_SP}. "
            f"Ensure app/.venv is synced: cd app/packages/kernel && uv sync"
        ) from e


def _parse_wkt_polygon(wkt: str) -> list[tuple[float, float]]:
    """Extract (lon, lat) pairs from a WKT POLYGON (( lon lat, … )) string."""
    m = re.search(r'\(\((.+?)\)\)', wkt, re.DOTALL)
    if not m:
        return []
    pairs = []
    for part in m.group(1).split(","):
        tokens = part.strip().split()
        if len(tokens) >= 2:
            try:
                pairs.append((float(tokens[0]), float(tokens[1])))
            except ValueError:
                pass
    return pairs


def stage3_taz(net_path: Path, taz_path: Path) -> Path:
    """Generate iloilo.taz.xml from CCHAIN barangay WKT polygons.

    Uses sumolib.net.readNet to get the coordinate projection from the network,
    then converts each barangay WKT POLYGON from geographic lon/lat to SUMO
    XY coordinates.  The resulting TAZ shapes are used by SUMO's OD demand
    generation and by the mode-share calibration in Phase 2.

    input_dataset_ids: CCHAIN (brgy_geography.csv)
    confidence: H (180 Iloilo barangays with complete polygon coverage)
    """
    if not net_path.exists():
        raise FileNotFoundError(f"stage2 output not found: {net_path}  (run stage 2 first)")

    sumolib = _load_sumolib()

    csv_path = DATA_RAW / "hdx" / "brgy_geography.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CCHAIN brgy_geography.csv not found at {csv_path}")

    print(f"[stage3] loading network for coordinate projection …")
    net = sumolib.net.readNet(str(net_path))

    csv.field_size_limit(10 ** 8)  # WKT geometry fields are large
    brgys: list[dict] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("adm4_pcode", "").startswith("PH063022"):
                brgys.append(row)

    print(f"[stage3] projecting {len(brgys)} Iloilo barangay polygons …")
    taz_path.parent.mkdir(parents=True, exist_ok=True)

    written = skipped = 0
    with open(taz_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(f'<!-- MATRIX build_network.py — Phase 1.1 -->\n')
        f.write(f'<!-- input_dataset_ids: {TAZ_PROVENANCE["input_dataset_ids"]} -->\n')
        f.write(f'<!-- confidence: {TAZ_PROVENANCE["confidence"]} -->\n')
        f.write('<additional>\n')

        for row in brgys:
            pcode = row["adm4_pcode"]
            wkt   = row.get("geometry", "").strip()
            pairs = _parse_wkt_polygon(wkt)

            if len(pairs) < 3:
                skipped += 1
                continue

            # Project each (lon, lat) → SUMO (x, y)
            xy_pairs = []
            for lon, lat in pairs:
                try:
                    x, y = net.convertLonLat2XY(lon, lat)
                    xy_pairs.append(f"{x:.2f},{y:.2f}")
                except Exception:
                    pass  # skip any projection failures

            if len(xy_pairs) < 3:
                skipped += 1
                continue

            shape = " ".join(xy_pairs)
            area  = row.get("brgy_total_area", "")
            coastal = row.get("brgy_is_coastal", "")

            f.write(f'  <taz id="{pcode}"')
            if area:
                f.write(f' brgy_total_area_km2="{area}"')
            if coastal:
                f.write(f' brgy_is_coastal="{coastal}"')
            f.write(f' shape="{shape}"/>\n')
            written += 1

        f.write('</additional>\n')

    size = taz_path.stat().st_size
    print(f"[stage3] OK wrote {taz_path.name} ({size:,} bytes)  "
          f"zones={written}  skipped={skipped}")
    return taz_path


# ─── validation helpers ───────────────────────────────────────────────────────

def validate_net(net_path: Path) -> bool:
    """Quick smoke-test the generated net with sumolib.

    Gate 1 done-when: sumolib loads the net; edge count > 0; network is routable
    (has at least one connected component).  Prints key stats.
    """
    sumolib = _load_sumolib()
    print(f"[validate] loading {net_path.name} with sumolib …")
    net = sumolib.net.readNet(str(net_path))
    edges = net.getEdges()
    nodes = net.getNodes()
    print(f"[validate] edges={len(edges):,}  nodes={len(nodes):,}")
    if not edges:
        print("[validate] FAIL: no edges in network")
        return False
    # Check a few edges are connected
    sample = edges[:min(5, len(edges))]
    for e in sample:
        print(f"[validate]   edge {e.getID()!r:20s}  "
              f"from={e.getFromNode().getID()!r}  to={e.getToNode().getID()!r}  "
              f"speed={e.getSpeed():.1f}m/s  lanes={e.getLaneNumber()}")
    print("[validate] OK network routable")
    return True


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build MATRIX SUMO network + TAZ for Iloilo City (Phase 1.1)")
    ap.add_argument(
        "--stage", type=int, choices=[1, 2, 3], default=0,
        help="Run only one stage (0 = all three in sequence)")
    ap.add_argument(
        "--validate", action="store_true",
        help="After building the network, validate it with sumolib")
    args = ap.parse_args()

    osm_path = KERNEL_DATA / "iloilo.osm"
    net_path = KERNEL_DATA / "iloilo.net.xml"
    taz_path = KERNEL_DATA / "iloilo.taz.xml"

    run_all = args.stage == 0
    ok = True

    try:
        if run_all or args.stage == 1:
            stage1_json_to_osm()

        if run_all or args.stage == 2:
            stage2_netconvert(osm_path, net_path)
            if args.validate or run_all:
                ok = validate_net(net_path)

        if run_all or args.stage == 3:
            stage3_taz(net_path, taz_path)

    except (FileNotFoundError, RuntimeError) as e:
        print(f"\n[build_network] ERROR: {e}", file=sys.stderr)
        return 1

    if ok:
        print("\n[build_network] Pipeline complete.")
        print(f"  {net_path}")
        print(f"  {taz_path}")
        print(f"\nGate 1 next: open iloilo.net.xml in sumo-gui and confirm it renders.")
        print(f"  docker run --rm -v {_windows_path_for_docker(KERNEL_DATA)}:/data "
              f"-e DISPLAY -it {SUMO_IMG} sumo-gui --net-file /data/iloilo.net.xml")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
