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
from matrix_kernel.personas import ILOILO_MODE_SHARE
from matrix_kernel.scenario import Scenario, apply_intervention  # noqa: F401  (Scenario re-exported)
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
    """SUMO edge ids whose street name contains `corridor` (case-insensitive), else [].

    Kept separate from the busiest-edge fallback so the resolution METHOD can be reported
    honestly (a real name match vs a fallback). Requires the net to carry street names
    (build_network.py `--output.street-names`); an empty result is an honest miss, not a
    guess (PRD-F14)."""
    key = corridor.strip().lower()
    if not key:
        return []
    return [e.getID() for e in _net().getEdges() if e.getName() and key in e.getName().lower()]


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


def _resolve_edges(scenario: Scenario, top_n: int = 1) -> tuple[list[str], str]:
    """Resolve WHERE a scenario applies -> (SUMO edge ids, resolution method).

    Order: a map-drop `geometry` (resolved against the cached net via
    matrix_kernel.geometry) wins; else the location keyword is mapped via gazetteer;
    else it is matched against edge street names; else a deterministic hash of the
    location selects from the top 50 busiest edges. The method string is
    recorded verbatim in Trajectory.meta (PRD-F14) and names the fallback explicitly.
    This ensures that different unknown locations hit different distinct edges,
    producing varied module outputs rather than identically falling back to the single
    busiest edge every time."""
    geom = scenario.geometry is not None
    if geom:
        from matrix_kernel.geometry import resolve_geometry

        edges = resolve_geometry(_net(), scenario.geometry)
        if edges:
            return edges, "geometry"

    loc = scenario.effective_location

    if loc:
        from matrix_kernel.gazetteer import resolve_colloquial_term
        entry = resolve_colloquial_term(loc)
        # A gazetteer hit is only a real match if its sumo_edge actually exists in the
        # deployed net (PRD-F14): a curated entry can carry a stale/placeholder id, and
        # claiming "gazetteer-match" while touching zero edges would be a glass-box lie.
        if entry and entry.sumo_edge and entry.sumo_edge in _edge_ids():
            flag = " (PROVISIONAL-id)" if entry.provisional else ""
            return [entry.sumo_edge], f"gazetteer-match{flag}"

    kw = _keyword_edges(loc)
    if kw:
        return kw, "keyword-match (geometry off-network)" if geom else "keyword-match"

    detail = f"no edge named like {loc!r}" if loc.strip() else "no location given"
    if geom:
        detail = f"geometry off-network; {detail}"
        
    busiest_50 = _busiest_baseline_edges(50)
    if busiest_50 and loc.strip():
        import hashlib
        h = int(hashlib.md5(loc.strip().encode('utf-8')).hexdigest(), 16)
        fallback_edge = busiest_50[h % len(busiest_50)]
        return [fallback_edge], f"busiest-baseline-fallback (deterministic-hash; {detail})"
        
    return _busiest_baseline_edges(top_n), f"busiest-baseline-fallback ({detail})"


def resolve_edges(scenario: Scenario, top_n: int = 1) -> list[str]:
    """Edge ids a scenario affects (back-compat wrapper over _resolve_edges)."""
    return resolve_intervention_site(scenario, top_n)[0]


def resolve_intervention_site(scenario: Scenario, top_n: int = 1) -> tuple[list[str], str]:
    """Where the intervention applies: demand-only facilities touch no corridor edges."""
    if scenario.intervention_type == "new_facility":
        return [], "facility-demand"
    return _resolve_edges(scenario, top_n)


def facility_demand_meta(scenario: Scenario) -> dict | None:
    """BEH-4 summary for Trajectory.meta, or None when the scenario is not a facility."""
    if scenario.intervention_type != "new_facility":
        return None
    from matrix_kernel.demand_delta import demand_delta_summary, prepare_facility_demand

    delta = prepare_facility_demand(
        scenario.geometry,
        scenario.effective_location,
        scenario.effective_parameters(),
    )
    return demand_delta_summary(delta)


def _location_of_interest(affected: list[str], edge_resolution: str) -> list[float] | None:
    """[lon, lat] of the first affected edge's midpoint, ground truth for the results-
    view map marker/pan (CR-013) -- or None for a fallback resolution. Never a centroid
    across all affected edges: a street name can match segments in unrelated
    neighborhoods, and averaging those would land the marker in a meaningless spot
    between them. Only a real resolution (geometry/gazetteer/keyword) earns a marker --
    showing one for busiest-baseline-fallback would be a glass-box lie (PRD-F14).
    new_facility (facility-demand) has no closed corridor, so no marker."""
    if (
        not affected
        or edge_resolution.startswith("busiest-baseline-fallback")
        or edge_resolution == "facility-demand"
    ):
        return None
    from matrix_kernel.geometry import edge_midpoint_lonlat

    lon, lat = edge_midpoint_lonlat(_net(), affected[0])
    return [round(lon, 5), round(lat, 5)]


def simulate(scenario: Scenario, end: float = SIM_END, sample_period: int = 30,
             max_frames: int = 40) -> Trajectory:
    """Run the scenario via TraCI as a delta vs the cached baseline -> one Trajectory."""
    if not NET.exists() or not ROU.exists():
        raise FileNotFoundError("network/demand missing -- run build_network.py + build_demand.py")
    import traci

    affected, edge_resolution = resolve_intervention_site(scenario)
    location_of_interest = _location_of_interest(affected, edge_resolution)
    demand_meta = facility_demand_meta(scenario)

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
            while conn.simulation.getMinExpectedNumber() > 0 and conn.simulation.getTime() < end:
                conn.simulationStep()
        finally:
            conn.close()

        edge_counts = _parse_edgecounts(edge_out)
        frames = _parse_frames(fcd_out, max_frames)

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
            "applied": applied,  # dispatch record: edges touched, parameters, TraCI calls, assumptions
            "edge_resolution": edge_resolution,  # "geometry" (map-drop) or "keyword-match"
            # [lon, lat] of the first affected edge's midpoint, or None for a fallback
            # resolution (CR-013: the results-view map marker/pan; ground truth, not a guess).
            "location_of_interest": location_of_interest,
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
