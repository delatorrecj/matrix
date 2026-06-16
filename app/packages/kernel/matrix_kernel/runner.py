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
    matrix_kernel.geometry) wins; else the location keyword is matched against edge street
    names; else the busiest baseline edge is the honest last resort. The method string is
    recorded verbatim in Trajectory.meta (PRD-F14) and names the busiest-edge FALLBACK
    explicitly -- a run must never claim a named-corridor ("keyword-match") it did not make
    (it previously did, because the net carried no street names so every keyword silently
    fell back to the busiest edge)."""
    geom = scenario.geometry is not None
    if geom:
        from matrix_kernel.geometry import resolve_geometry

        edges = resolve_geometry(_net(), scenario.geometry)
        if edges:
            return edges, "geometry"

    loc = scenario.effective_location
    kw = _keyword_edges(loc)
    if kw:
        return kw, "keyword-match (geometry off-network)" if geom else "keyword-match"

    detail = f"no edge named like {loc!r}" if loc.strip() else "no location given"
    if geom:
        detail = f"geometry off-network; {detail}"
    return _busiest_baseline_edges(top_n), f"busiest-baseline-fallback ({detail})"


def resolve_edges(scenario: Scenario, top_n: int = 1) -> list[str]:
    """Edge ids a scenario affects (back-compat wrapper over _resolve_edges)."""
    return _resolve_edges(scenario, top_n)[0]


def simulate(scenario: Scenario, end: float = SIM_END, sample_period: int = 30,
             max_frames: int = 40) -> Trajectory:
    """Run the scenario via TraCI as a delta vs the cached baseline -> one Trajectory."""
    if not NET.exists() or not ROU.exists():
        raise FileNotFoundError("network/demand missing -- run build_network.py + build_demand.py")
    import traci

    affected, edge_resolution = _resolve_edges(scenario)
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
            "--device.rerouting.probability", "1", "--device.rerouting.period", "60",
            "--end", str(end), "--no-step-log", "true", "--xml-validation", "never",
            "--ignore-route-errors", "true",  # an edit may strand a route -> drop it, don't abort
        ]
        os.environ["SUMO_HOME"] = sumo_env.sumo_home()
        traci.start(cmd)
        try:
            # Apply the scenario's network edit via the per-intervention dispatcher.
            applied = apply_intervention(traci, scenario, affected)
            while traci.simulation.getMinExpectedNumber() > 0 and traci.simulation.getTime() < end:
                traci.simulationStep()
        finally:
            traci.close()

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
            # -- legacy keys: the five modules read these as "the affected corridor" -- keep. --
            "closed_edges": affected,
            "edge_lanes": applied["edge_lanes"],
            "lanes_closed": applied["lanes_closed_legacy"],
            "sim_end_s": end,
            "edges_with_traffic": len(edge_counts),
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
