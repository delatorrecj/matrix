"""Unified simulation kernel -- TraCI delta runner (U7; PRD-F1, SDD §2, RFC RT-03/05).

simulate(scenario) runs SUMO via TraCI, applies the scenario's network edit (lane closure,
full road closure, speed change, capacity change -- dispatched per intervention_type by
matrix_kernel.scenario), and returns ONE per-edge + playback Trajectory computed as a DELTA
against the cached nightly baseline (Redis baseline:iloilo:latest). All five impact modules
score this one dataset -- the architectural reason results never contradict. Never fork
into five simulators.

TraCI applies the edit dynamically; SUMO itself writes edgeData (volumes) + geo FCD
(playback) to files, so the step loop does no per-vehicle Python I/O (keeps it fast). The
trajectory schema (matrix_kernel.trajectory) is FROZEN here -- Phase-3 modules build on it.
The Scenario model + intervention dispatch live in matrix_kernel.scenario (SUMO-free);
`Scenario` is re-exported here so v1 call sites keep importing from the runner.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

from matrix_kernel import sumo_env  # wires SUMO_HOME + tools
from matrix_kernel.baseline import NET, ROU, SIM_END, load_baseline
from matrix_kernel.map_truth import map_truth_fields
from matrix_kernel.personas import ILOILO_MODE_SHARE
from matrix_kernel.scenario import Scenario, apply_intervention  # noqa: F401  (Scenario re-exported)
from matrix_kernel.span import clip_named_span, extract_live_street, keyword_edges, peel_span_fields
from matrix_kernel.trajectory import Frame, Trajectory


@lru_cache(maxsize=1)
def _net():
    """Load the SUMO net once (for edge-name lookup). Cached -- the load is the slow part."""
    import sumolib

    return sumolib.net.readNet(str(NET))


@lru_cache(maxsize=1)
def _edge_ids() -> frozenset[str]:
    """All edge ids in the net, cached -- avoids rescanning ~36k edges per gazetteer check."""
    return frozenset(e.getID() for e in _net().getEdges())


_SNAP_RADIUS_M = {"bridge": 80.0, "market": 100.0, "plaza": 100.0, "district": 120.0}
_SNAP_CAP = {"bridge": 4, "market": 6, "plaza": 6, "district": 8}


def _parse_osm_way_id(osm_id: str) -> str | None:
    """Numeric OSM way id from a gazetteer osm_id, or None for nodes / placeholders."""
    raw = (osm_id or "").strip()
    if not raw:
        return None
    lowered = raw.lower()
    if lowered.startswith("node/"):
        return None
    if lowered.startswith("way/"):
        raw = raw[4:]
    return raw if raw.isdigit() else None


def _lane_orig_id(lane) -> str:
    raw = ""
    for name in ("getParam", "getParameter"):
        fn = getattr(lane, name, None)
        if callable(fn):
            val = fn("origId")
            if val:
                raw = str(val)
                break
    if not raw:
        params = getattr(lane, "getParams", None)
        if callable(params):
            val = (params() or {}).get("origId")
            if val:
                raw = str(val)
    token = raw.split()[0].strip() if raw else ""
    return token if token.isdigit() else ""


@lru_cache(maxsize=1)
def _osm_orig_ids() -> dict[str, tuple[str, ...]]:
    """OSM way origId -> live SUMO edge ids (both directions / split segments)."""
    grouped: dict[str, list[str]] = {}
    for edge in _net().getEdges():
        eid = edge.getID()
        if eid.startswith(":"):
            continue
        oid = ""
        for lane in edge.getLanes():
            oid = _lane_orig_id(lane)
            if oid:
                break
        if not oid:
            continue
        grouped.setdefault(oid, []).append(eid)
    return {oid: tuple(eids) for oid, eids in grouped.items()}


def _gazetteer_edges(entry) -> tuple[list[str], str] | None:
    """Resolve a gazetteer hit against the live net. None = not a geographic match."""
    from matrix_kernel.gazetteer import live_sumo_edges

    live = [eid for eid in live_sumo_edges(entry) if eid in _edge_ids()]
    if live:
        flag = " (PROVISIONAL-id)" if getattr(entry, "provisional", True) else ""
        return live, f"gazetteer-match{flag}"

    oid = _parse_osm_way_id(getattr(entry, "osm_id", "") or "")
    if oid:
        osm_edges = list(_osm_orig_ids().get(oid, ()))
        if osm_edges:
            return osm_edges, "gazetteer-osmid"

    alias = (getattr(entry, "street_name", "") or "").strip()
    if alias:
        kw_alias = _keyword_edges(alias)
        if kw_alias:
            return kw_alias, "gazetteer-alias"

    coords = getattr(entry, "coordinates", None) or []
    ftype = getattr(entry, "feature_type", "") or ""
    radius = getattr(entry, "snap_radius_m", None)
    if radius is None:
        radius = _SNAP_RADIUS_M.get(ftype, 0.0)
    if radius and len(coords) >= 2:
        from matrix_kernel.geometry import nearest_edges

        cap = _SNAP_CAP.get(ftype, 6)
        snapped = nearest_edges(
            _net(), float(coords[0]), float(coords[1]), float(radius), cap
        )
        if snapped:
            return snapped, "gazetteer-snap"
    return None


def _mode_for(vehicle_id: str) -> str:
    """Deterministically assign a persona mode to a SUMO vehicle (slice simplification: the
    demand is vehicle-routed, modes label it for BEH-2 mode-share accounting -- Behavioral
    *behavior* confidence stays M)."""
    modes, weights = list(ILOILO_MODE_SHARE), list(ILOILO_MODE_SHARE.values())
    h = (hash(vehicle_id) & 0xFFFFFFFF) / 0xFFFFFFFF
    cum = 0.0
    for m, w in zip(modes, weights):
        cum += w
        if h <= cum:
            return m
    return modes[-1]


def _keyword_edges(corridor: str) -> list[str]:
    """SUMO edge ids whose street name matches `corridor` (normalized), else [].

    A stuffed span phrase is not a match — tokenize/normalize first, then look up
    the live street index. If that misses, the longest live street name contained
    in the string is tried. Empty is an honest miss, not a guess (PRD-F14).
    """
    net = _net()
    hits = keyword_edges(net, corridor)
    if hits:
        return hits
    extracted = extract_live_street(net, corridor)
    return keyword_edges(net, extracted) if extracted else []


def _busiest_baseline_edges(top_n: int = 1) -> list[str]:
    """The top_n busiest edges in the cached baseline -- the honest last resort so a
    scenario always has SOMETHING to measure when it names no resolvable location. The
    caller labels this as a fallback; it is never presented as a location match."""
    base = load_baseline().edge_counts
    return [eid for eid, _ in sorted(base.items(), key=lambda kv: kv[1], reverse=True)[:top_n]]


def target_edges(corridor: str, top_n: int = 1) -> list[str]:
    """Edges the scenario affects: street-name match on `corridor`, else the busiest
    baseline edge. Back-compat wrapper over the two resolvers above (callers that need to
    know WHICH path was taken use _resolve_edges, which labels it)."""
    return _keyword_edges(corridor) or _busiest_baseline_edges(top_n)


def _span_fields(scenario: Scenario) -> tuple[str, str, str]:
    """Corridor-only location + bounding crosses. Kernel re-peels sloppy LLM strings."""
    params = scenario.parameters or {}
    return peel_span_fields(
        scenario.effective_location,
        str(params.get("from_cross") or ""),
        str(params.get("to_cross") or ""),
    )


def _clip_corridor(
    edges: list[str], method: str, from_cross: str, to_cross: str
) -> tuple[list[str], str, list[str], str]:
    """Clip a live named-street set. Empty walk keeps the corridor (never hash)."""
    if not from_cross and not to_cross:
        return edges, method, [], ""
    clip = clip_named_span(_net(), edges, from_cross, to_cross)
    if clip.method == "miss" or not clip.edges:
        return edges, method, list(clip.span_nodes), clip.assumption
    out_method = clip.method
    if method.endswith("(geometry off-network)") and out_method.startswith("keyword-"):
        out_method = f"{out_method} (geometry off-network)"
    return clip.edges, out_method, list(clip.span_nodes), clip.assumption


def _resolve_site(scenario: Scenario, top_n: int = 1) -> dict:
    """WHERE a scenario applies, plus span provenance for Trajectory.meta."""
    loc, from_cross, to_cross = _span_fields(scenario)
    empty = {
        "from_cross": from_cross,
        "to_cross": to_cross,
        "span_nodes": [],
        "span_assumption": "",
        "corridor": loc,
    }

    geom = scenario.geometry is not None
    if geom:
        from matrix_kernel.geometry import resolve_geometry

        edges = resolve_geometry(_net(), scenario.geometry)
        if edges:
            return {"edges": edges, "method": "geometry", **empty}

    from matrix_kernel.gazetteer import resolve_colloquial_term

    entry = resolve_colloquial_term(loc) if loc else None
    raw_loc = scenario.effective_location
    if entry is None and raw_loc and raw_loc != loc:
        entry = resolve_colloquial_term(raw_loc)
    if entry is None and scenario.description:
        entry = resolve_colloquial_term(scenario.description)
    if entry:
        hit = _gazetteer_edges(entry)
        if hit:
            edges, method = hit
            return {"edges": edges, "method": method, **empty}

    kw = _keyword_edges(loc)
    if not kw and raw_loc and raw_loc != loc:
        kw = _keyword_edges(raw_loc)
    if not kw and " " in (scenario.description or ""):
        extracted = extract_live_street(_net(), scenario.description)
        if extracted:
            kw = _keyword_edges(extracted)
    if kw:
        method = "keyword-match (geometry off-network)" if geom else "keyword-match"
        edges, method, span_nodes, assumption = _clip_corridor(
            kw, method, from_cross, to_cross
        )
        return {
            "edges": edges,
            "method": method,
            "from_cross": from_cross,
            "to_cross": to_cross,
            "span_nodes": span_nodes,
            "span_assumption": assumption,
            "corridor": loc,
        }

    detail_src = raw_loc or loc
    detail = f"no edge named like {detail_src!r}" if detail_src.strip() else "no location given"
    if geom:
        detail = f"geometry off-network; {detail}"

    busiest_50 = _busiest_baseline_edges(50)
    if busiest_50 and detail_src.strip():
        import hashlib

        h = int(hashlib.md5(detail_src.strip().encode("utf-8")).hexdigest(), 16)
        fallback_edge = busiest_50[h % len(busiest_50)]
        return {
            "edges": [fallback_edge],
            "method": f"busiest-baseline-fallback (deterministic-hash; {detail})",
            **empty,
        }

    return {
        "edges": _busiest_baseline_edges(top_n),
        "method": f"busiest-baseline-fallback ({detail})",
        **empty,
    }


def _resolve_edges(scenario: Scenario, top_n: int = 1) -> tuple[list[str], str]:
    """Resolve WHERE a scenario applies -> (SUMO edge ids, resolution method).

    Order: map-drop geometry; gazetteer (live ids / origId / alias / snap);
    live-net street index on the corridor name; optional span clip when
    from_cross/to_cross resolve on that corridor; longest live street name
    contained in a leftover stuffed phrase; then busiest-baseline-fallback.
    The method string is recorded verbatim in Trajectory.meta (PRD-F14).
    """
    site = _resolve_site(scenario, top_n)
    return site["edges"], site["method"]


def resolve_edges(scenario: Scenario, top_n: int = 1) -> list[str]:
    """Edge ids a scenario affects (back-compat wrapper over _resolve_edges)."""
    return resolve_intervention_site(scenario, top_n)[0]


def resolve_intervention_site(scenario: Scenario, top_n: int = 1) -> tuple[list[str], str]:
    """Where the intervention applies: demand-only facilities touch no corridor edges."""
    site = _intervention_site(scenario, top_n)
    return site["edges"], site["method"]


def _intervention_site(scenario: Scenario, top_n: int = 1) -> dict:
    if scenario.intervention_type == "new_facility":
        loc, frm, to = _span_fields(scenario)
        edges = _facility_adjacent_edges(scenario)
        return {
            "edges": edges,
            "method": "facility-adjacent" if edges else "facility-demand",
            "from_cross": frm,
            "to_cross": to,
            "span_nodes": [],
            "span_assumption": "",
            "corridor": loc,
        }
    return _resolve_site(scenario, top_n)


_FACILITY_ADJACENT_RADIUS_M = 250.0
_FACILITY_ADJACENT_CAP = 8


def _facility_adjacent_edges(scenario: Scenario) -> list[str]:
    """Nearest live-net edges to the facility centroid — scoring/overlay only, no TraCI edit."""
    try:
        from matrix_kernel.demand_delta import prepare_facility_demand
        from matrix_kernel.geometry import nearest_edges

        delta = prepare_facility_demand(
            scenario.geometry,
            scenario.effective_location,
            scenario.effective_parameters(),
        )
        lon, lat = delta.facility_lonlat
        return nearest_edges(
            _net(), lon, lat,
            radius_m=_FACILITY_ADJACENT_RADIUS_M,
            cap=_FACILITY_ADJACENT_CAP,
        )
    except Exception:
        return []


def facility_demand_meta(scenario: Scenario) -> dict | None:
    """BEH-4 summary for Trajectory.meta, or None when the scenario is not a facility."""
    delta = _facility_demand_delta(scenario)
    if delta is None:
        return None
    from matrix_kernel.demand_delta import demand_delta_summary

    return demand_delta_summary(delta)


def _facility_demand_delta(scenario: Scenario):
    """Full DemandDelta for injection, or None."""
    if scenario.intervention_type != "new_facility":
        return None
    from matrix_kernel.demand_delta import prepare_facility_demand

    return prepare_facility_demand(
        scenario.geometry,
        scenario.effective_location,
        scenario.effective_parameters(),
    )


def _location_of_interest(affected: list[str], edge_resolution: str) -> list[float] | None:
    """[lon, lat] of the first affected edge's midpoint, ground truth for the results-
    view map marker/pan (CR-013) -- or None for a fallback resolution. Never a centroid
    across all affected edges: a street name can match segments in unrelated
    neighborhoods, and averaging those would land the marker in a meaningless spot
    between them. Only a real resolution (geometry/gazetteer/keyword) earns a marker --
    showing one for busiest-baseline-fallback would be a glass-box lie (PRD-F14).
    The results-map camera uses the corridor box, not this point.
    new_facility with facility-adjacent edges earns a marker; facility-demand (no
    resolved centroid) does not."""
    if (
        not affected
        or edge_resolution.startswith("busiest-baseline-fallback")
        or edge_resolution == "facility-demand"
    ):
        return None
    from matrix_kernel.geometry import edge_midpoint_lonlat

    lon, lat = edge_midpoint_lonlat(_net(), affected[0])
    return [round(lon, 5), round(lat, 5)]


def simulate(scenario: Scenario, end: float = SIM_END, sample_period: int | None = None,
             max_frames: int | None = None) -> Trajectory:
    """Run the scenario via TraCI as a delta vs the cached baseline -> one Trajectory."""
    if sample_period is None:
        sample_period = int(os.environ.get("MATRIX_SIM_SAMPLE_PERIOD", "30"))
    if max_frames is None:
        max_frames = int(os.environ.get("MATRIX_SIM_MAX_FRAMES", "30"))
    if not NET.exists() or not ROU.exists():
        raise FileNotFoundError("network/demand missing -- run build_network.py + build_demand.py")
    import traci

    site = _intervention_site(scenario)
    affected, edge_resolution = site["edges"], site["method"]
    location_of_interest = _location_of_interest(affected, edge_resolution)
    demand_meta = facility_demand_meta(scenario)
    demand_delta = _facility_demand_delta(scenario)
    truth = map_truth_fields(affected, edge_resolution, location_of_interest)
    from matrix_kernel.geometry import affected_edge_features

    geoms = affected_edge_features(_net(), affected) if truth["overlay_honest"] else []

    with tempfile.TemporaryDirectory() as td:
        add = Path(td) / "ed.add.xml"
        edge_out = Path(td) / "edgeout.xml"
        fcd_out = Path(td) / "fcd.xml"
        add.write_text(f'<additional>\n  <edgeData id="ed" file="{edge_out.as_posix()}" freq="1000000"/>\n</additional>\n')

        cmd = [
            sumo_env.bin_path("sumo"),
            "-n", str(NET), "-r", str(ROU),
            "--additional-files", str(add),
            "--fcd-output", str(fcd_out), "--fcd-output.geo", "--device.fcd.period", str(sample_period),
            "--device.rerouting.probability", "1", "--device.rerouting.period", "120",
            "--end", str(end), "--no-step-log", "true", "--xml-validation", "never",
            "--ignore-route-errors", "true",  # an edit may strand a route -> drop it, don't abort
        ]
        os.environ["SUMO_HOME"] = sumo_env.sumo_home()
        # A unique label per call (not the implicit "default") -- traci's module-level
        # _connections dict is process-global, so two concurrent simulate() calls (the
        # /simulate concurrency gate admits MATRIX_MAX_CONCURRENT_SIMS, default 2) both
        # starting under "default" collide with "Connection 'default' is already
        # active." getConnection() returns a connection object whose .edge/.lane/
        # .simulation domains are bound to THIS socket specifically (traci's
        # domain._register binds a per-connection copy, independent of whichever
        # connection is globally "switched" current) -- genuinely thread-safe.
        label = f"matrix-{uuid.uuid4().hex}"
        traci.start(cmd, label=label)
        conn = traci.getConnection(label)
        conn.TraCIException = traci.TraCIException  # scenario.py handlers read this off traci_mod
        try:
            # Apply the scenario's network edit via the per-intervention dispatcher.
            applied = apply_intervention(conn, scenario, affected)
            injection_record = None
            if demand_delta is not None:
                from matrix_kernel.facility_injection import inject_facility_demand

                injection_record = inject_facility_demand(conn, _net(), demand_delta)
                applied = {**applied, "facility_injection": injection_record}
            while conn.simulation.getMinExpectedNumber() > 0 and conn.simulation.getTime() < end:
                conn.simulationStep()
        finally:
            conn.close()

        edge_counts = _parse_edgecounts(edge_out)
        frames = _parse_frames(fcd_out, max_frames)

    from matrix_kernel.baseline import load_baseline as _load_baseline
    try:
        base_counts = _load_baseline().edge_counts
    except Exception:
        base_counts = {}
    impacted = [
        e for e in (set(edge_counts) | set(base_counts))
        if edge_counts.get(e, 0) != base_counts.get(e, 0)
    ]
    lengths: dict[str, float] = {}
    try:
        net = _net()
        for eid in set(affected) | set(impacted):
            try:
                lengths[eid] = net.getEdge(eid).getLength() / 1000.0
            except Exception:
                continue
    except Exception:
        lengths = {}

    return Trajectory(
        edge_counts=edge_counts,
        frames=frames,
        meta={
            "kind": "scenario",
            "scenario_id": scenario.scenario_id,
            "description": scenario.description,
            # -- Scenario v2 provenance (PRD-F14): the exact edit that was applied --
            "intervention_type": scenario.intervention_type,
            "affected_edges": affected,
            "impacted_edges": impacted,
            "edge_lengths_km": lengths,
            "flood_hazard": bool(getattr(scenario, "flood_hazard", False)),
            "applied": applied,  # dispatch record: edges touched, parameters, TraCI calls, assumptions
            "edge_resolution": edge_resolution,  # "geometry" (map-drop) or "keyword-match" / "keyword-span"
            "overlay_honest": truth["overlay_honest"],
            # [lon, lat] of the first affected edge's midpoint, or None for a fallback
            # resolution (CR-013: location marker only; camera uses corridor box).
            "location_of_interest": truth["location_of_interest"],
            "from_cross": site.get("from_cross") or "",
            "to_cross": site.get("to_cross") or "",
            "span_nodes": site.get("span_nodes") or [],
            "corridor": site.get("corridor") or scenario.effective_location,
            "affected_edge_geoms": geoms,
            # -- legacy keys: the five modules read these as "the affected corridor" -- keep. --
            "closed_edges": affected,
            "edge_lanes": applied["edge_lanes"],
            "lanes_closed": applied["lanes_closed_legacy"],
            "sim_end_s": end,
            "edges_with_traffic": len(edge_counts),
            # BEH-4 summary only; per-trip samples stay off the WebSocket (PRD-F14 + 90s budget).
            "demand_delta": demand_meta,
        },
    )


def _parse_edgecounts(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    counts: dict[str, int] = {}
    for edge in ET.parse(path).getroot().iter("edge"):
        entered = edge.get("entered")
        if entered is not None and int(float(entered)) > 0:
            counts[edge.get("id")] = int(float(entered))
    return counts


def _parse_frames(path: Path, max_frames: int) -> list[Frame]:
    if not path.exists():
        return []
    frames: list[Frame] = []
    for ts in ET.parse(path).getroot().iter("timestep"):
        agents = [
            {"id": v.get("id"), "lon": float(v.get("x")), "lat": float(v.get("y")),
             "mode": _mode_for(v.get("id"))}
            for v in ts.iter("vehicle")
        ]
        if agents:
            frames.append(Frame(tick=float(ts.get("time")), agents=agents))
    # Down-sample to at most max_frames evenly spaced ticks (keeps the WS payload small).
    if len(frames) > max_frames:
        step = len(frames) / max_frames
        frames = [frames[int(i * step)] for i in range(max_frames)]
    return frames
