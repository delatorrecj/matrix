#!/usr/bin/env python3
"""Report how gazetteer_iloilo.json aliases resolve against a live SUMO net.

Read-only by default. Does not run in CI --strict: the City Proper fixture omits
Arevalo/Molo. Point --net at the full Iloilo net (kernel data/ or deploy/hf-space/).

Usage (from app/packages/kernel so uv has sumolib):
    uv run python ../data/verify_gazetteer.py
    uv run python ../data/verify_gazetteer.py --net ../../deploy/hf-space/iloilo.net.xml
    uv run python ../data/verify_gazetteer.py --write   # fill live ids after review
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_KERNEL = _HERE.parents[1] / "kernel"
_HF_NET = _HERE.parents[3] / "deploy" / "hf-space" / "iloilo.net.xml"

if str(_KERNEL) not in sys.path:
    sys.path.insert(0, str(_KERNEL))

from matrix_kernel.gazetteer import (  # noqa: E402
    GAZETTEER_FILE,
    GazetteerEntry,
    live_sumo_edges,
    load_gazetteer,
)
from matrix_kernel.geometry import load_net, nearest_edges  # noqa: E402
from matrix_kernel.runner import (  # noqa: E402
    _SNAP_CAP,
    _SNAP_RADIUS_M,
    _lane_orig_id,
    _parse_osm_way_id,
)


def resolve_net_path(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    env = os.environ.get("MATRIX_NET_PATH")
    if env and Path(env).is_file():
        return Path(env)
    from matrix_kernel.geometry import NET

    if NET.is_file():
        return NET
    if _HF_NET.is_file():
        return _HF_NET
    return None


def _orig_id(edge) -> str:
    for lane in edge.getLanes():
        oid = _lane_orig_id(lane)
        if oid:
            return oid
    return ""


def _keyword_edges(net, key: str) -> list[str]:
    needle = key.strip().lower()
    if not needle:
        return []
    return [
        e.getID()
        for e in net.getEdges()
        if not e.getID().startswith(":")
        and e.getName()
        and needle in e.getName().lower()
    ]


def inspect_entry(net, alias: str, entry: GazetteerEntry) -> dict:
    ids = set(e.getID() for e in net.getEdges())
    live = [eid for eid in live_sumo_edges(entry) if eid in ids]
    oid = _parse_osm_way_id(entry.osm_id)
    orig_hits: list[str] = []
    if oid:
        orig_hits = [
            e.getID()
            for e in net.getEdges()
            if not e.getID().startswith(":") and _orig_id(e) == oid
        ]
    alias_hits = _keyword_edges(net, entry.street_name)
    ftype = entry.feature_type
    radius = entry.snap_radius_m
    if radius is None:
        radius = _SNAP_RADIUS_M.get(ftype, 0.0)
    cap = _SNAP_CAP.get(ftype, 6)
    snapped: list[tuple[str, str, str]] = []
    if radius and len(entry.coordinates) >= 2:
        for eid in nearest_edges(
            net, entry.coordinates[0], entry.coordinates[1], float(radius), cap
        ):
            edge = net.getEdge(eid)
            snapped.append((eid, edge.getName() or "", _orig_id(edge)))
    named_suggestions: list[str] = []
    seen: set[str] = set()
    for _eid, name, _oid in snapped:
        if name and name not in seen:
            seen.add(name)
            named_suggestions.append(name)

    method = "unresolved"
    if live:
        method = "gazetteer-match"
    elif orig_hits:
        method = "gazetteer-osmid"
    elif alias_hits:
        method = "gazetteer-alias"
    elif snapped:
        method = "gazetteer-snap"

    return {
        "alias": alias,
        "canonical_name": entry.canonical_name,
        "feature_type": ftype,
        "method": method,
        "live_sumo_edges": live,
        "orig_hits": orig_hits[:12],
        "alias_hits": len(alias_hits),
        "snapped": snapped,
        "named_suggestions": named_suggestions,
        "provisional": entry.provisional,
    }


def _write_updates(raw: dict, reports: list[dict], net) -> dict:
    """Fill live ids for entries that snapped or matched origId. Does not invent street_name."""
    by_alias = {r["alias"]: r for r in reports}
    out = json.loads(json.dumps(raw))
    for alias, val in out.items():
        report = by_alias.get(alias.lower())
        if not report:
            continue
        snapped = report["snapped"]
        orig_hits = report["orig_hits"]
        live = report["live_sumo_edges"]
        # Street alias is the geographic truth for corridors/districts — do not
        # pin a handful of snap fragments and demote the alias.
        if report["alias_hits"] > 0:
            val["provisional"] = False
            if snapped and snapped[0][2]:
                val["osm_id"] = f"way/{snapped[0][2]}"
            continue
        edges = live or orig_hits or [row[0] for row in snapped]
        if not edges:
            continue
        val["sumo_edges"] = list(edges)
        val["sumo_edge"] = edges[0]
        oid = snapped[0][2] if snapped and snapped[0][2] else ""
        if oid:
            val["osm_id"] = f"way/{oid}"
        val["provisional"] = False
        if snapped:
            edge = net.getEdge(snapped[0][0])
            shape = edge.getShape()
            mx, my = shape[len(shape) // 2]
            lon, lat = net.convertXY2LonLat(mx, my)
            val["coordinates"] = [round(lon, 6), round(lat, 6)]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--net", default=None, help="Path to iloilo.net.xml")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Rewrite gazetteer JSON with live sumo_edges / osm_id / coordinates",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any non-provisional entry is unresolved (not for CI)",
    )
    args = parser.parse_args(argv)

    net_path = resolve_net_path(args.net)
    if net_path is None:
        print("missing SUMO net — pass --net, set MATRIX_NET_PATH, or run build_network.py", flush=True)
        return 1

    print(f"net: {net_path}", flush=True)
    net = load_net(net_path)
    gaz = load_gazetteer()
    reports = [inspect_entry(net, alias, entry) for alias, entry in gaz.items()]

    unresolved = 0
    for r in reports:
        snap_s = ", ".join(
            f"{eid} ({name or 'unnamed'})" for eid, name, _oid in r["snapped"][:4]
        )
        suggest = "; ".join(r["named_suggestions"][:3])
        print(
            f"{r['alias']!r:22} {r['method']:18} "
            f"live={len(r['live_sumo_edges'])} orig={len(r['orig_hits'])} "
            f"alias={r['alias_hits']} snap=[{snap_s}] "
            f"suggest={suggest!r} provisional={r['provisional']}",
            flush=True,
        )
        if r["method"] == "unresolved":
            unresolved += 1
        elif r["provisional"] is False and r["method"] == "unresolved":
            unresolved += 1

    if args.write:
        with open(GAZETTEER_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        updated = _write_updates(raw, reports, net)
        Path(GAZETTEER_FILE).write_text(
            json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {GAZETTEER_FILE}", flush=True)

    if args.strict:
        bad = [r for r in reports if not r["provisional"] and r["method"] == "unresolved"]
        if bad:
            print("strict: unresolved non-provisional:", [r["alias"] for r in bad], flush=True)
            return 1
    print(f"aliases={len(reports)} unresolved={unresolved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
