"""Scenario v2 -- typed intervention model + per-intervention TraCI dispatch (PRD-F2, SDD §2).

Generalizes the kernel beyond "close a lane": a Scenario is now
`{scenario_id, description, intervention_type, location, geometry, parameters}` and the
runner dispatches to one handler per intervention type. v1 fields (`corridor`,
`lanes_closed`) stay in place -- a v1 construction is exactly a `lane_closure`.

This module is deliberately **SUMO-free**: handlers receive the live ``traci`` module as
an argument (the runner passes the real one; tests pass a fake), so dispatch logic is
unit-testable without eclipse-sumo installed. TraCI call shapes verified against the
pinned eclipse-sumo 1.27.0 wheel (traci/_lane.py, traci/_edge.py):

  lane.setDisallowed(laneID, classes)   close a lane to the given vehicle classes
  lane.getMaxSpeed / lane.setMaxSpeed   per-lane speed limit, m/s
  edge.setMaxSpeed(edgeID, speed)       all lanes of the edge, m/s
  edge.getLaneNumber(edgeID)            lane count

NOTE: ``lane.setAllowed(laneID, [])`` means *all vehicles allowed* in TraCI -- it cannot
express a closure; closures must go through ``setDisallowed``.

Glass box (PRD-F14): every handler returns the exact edit it applied (edges touched,
parameters, TraCI calls, assumptions) and the runner records it verbatim in
``Trajectory.meta`` so the edit is inspectable, not implied.
"""
from __future__ import annotations

from dataclasses import dataclass, field

KPH_TO_MS = 1.0 / 3.6

INTERVENTION_TYPES = ("lane_closure", "full_closure", "speed_change", "capacity_change")

# Defaults applied ONLY when the orchestrator/caller omits a parameter. Never silent:
# the exact applied values are always recorded in the dispatch record -> Trajectory.meta.
_PARAMETER_DEFAULTS: dict[str, dict] = {
    "lane_closure": {"lanes_closed": 1},
    "full_closure": {},
    "speed_change": {"max_speed_kph": 30.0},   # traffic-calming fallback; orchestrator should supply
    "capacity_change": {"capacity_factor": 1.2},  # mild widening fallback; orchestrator should supply
}

# The demand model routes the "passenger" vehicle class (build_demand.py), so disallowing
# "passenger" removes all simulated traffic from a lane. Kept as a named constant so a
# later multi-class demand upgrade has one place to change.
_DEMAND_CLASSES = ["passenger"]


@dataclass(frozen=True)
class Scenario:
    """A proposed infrastructure intervention.

    v1 (Milestone A) carried only `corridor` + `lanes_closed` -- every query was a lane
    closure. v2 adds `intervention_type`, `location`, `geometry`, `parameters` so the
    Gemini orchestrator (PRD-F2) can express closures, speed changes, and capacity
    changes. Back-compat: `corridor`/`lanes_closed` keep their positions and defaults,
    and a v1 construction (`Scenario(id, desc, corridor=..., lanes_closed=...)`) behaves
    exactly as before (it *is* a lane_closure).

    `geometry` is an optional GeoJSON dict (map-drop input). Edge resolution from
    geometry is owned by ``matrix_kernel.geometry`` (separate unit); until it lands the
    runner resolves edges from `location`/`corridor` keywords only.
    """

    scenario_id: str
    description: str
    # -- v1 fields. Keep names, positions, and defaults: callers construct positionally. --
    corridor: str = ""        # street-name keyword for the affected corridor (legacy channel)
    lanes_closed: int = 1     # lane_closure parameter, legacy channel
    # -- v2 fields --
    intervention_type: str = "lane_closure"
    location: str = ""        # street / corridor / barangay / landmark keyword
    geometry: dict | None = None   # GeoJSON; resolved by matrix_kernel.geometry (later unit)
    parameters: dict = field(default_factory=dict)  # per-type knobs, see _PARAMETER_DEFAULTS

    def __post_init__(self) -> None:
        if self.intervention_type not in INTERVENTION_TYPES:
            raise ValueError(
                f"unknown intervention_type {self.intervention_type!r}; "
                f"expected one of {INTERVENTION_TYPES}"
            )

    @property
    def effective_location(self) -> str:
        """The location keyword to resolve edges from -- v2 `location` wins, v1 `corridor`
        is the fallback channel."""
        return self.location or self.corridor

    def effective_parameters(self) -> dict:
        """Per-type defaults <- legacy v1 fields <- explicit `parameters` (later wins).
        None values in `parameters` are ignored so an unset orchestrator field never
        clobbers a default."""
        params = dict(_PARAMETER_DEFAULTS[self.intervention_type])
        if self.intervention_type == "lane_closure":
            params["lanes_closed"] = self.lanes_closed  # the v1 channel
        params.update({k: v for k, v in self.parameters.items() if v is not None})
        return params


def _close_lanes(traci_mod, edges: list[str], n_close) -> tuple[list[str], dict[str, int], list[str]]:
    """Disallow the demand class on the first min(n_close(nlanes), nlanes) lanes of each
    edge. `n_close` is a callable nlanes -> how many to close (lets lane_closure and
    full_closure share the loop). Per-edge TraCI errors skip that edge (unknown id etc.),
    matching the v1 runner's behavior."""
    exc = getattr(traci_mod, "TraCIException", Exception)
    touched: list[str] = []
    edge_lanes: dict[str, int] = {}
    closed_lanes: list[str] = []
    for eid in edges:
        try:
            nlanes = traci_mod.edge.getLaneNumber(eid)
            edge_lanes[eid] = nlanes
            for i in range(min(n_close(nlanes), nlanes)):
                traci_mod.lane.setDisallowed(f"{eid}_{i}", _DEMAND_CLASSES)
                closed_lanes.append(f"{eid}_{i}")
            touched.append(eid)
        except exc:
            continue
    return touched, edge_lanes, closed_lanes


def _apply_lane_closure(traci_mod, scenario: Scenario, edges: list[str]) -> dict:
    """Close `lanes_closed` lanes per affected edge (capacity cut; v1 behavior preserved)."""
    n = int(scenario.effective_parameters()["lanes_closed"])
    touched, edge_lanes, closed_lanes = _close_lanes(traci_mod, edges, lambda nlanes: n)
    return {
        "intervention_type": "lane_closure",
        "edges": touched,
        "edge_lanes": edge_lanes,
        "parameters": {"lanes_closed": n},
        "closed_lanes": closed_lanes,
        "traci_calls": ["lane.setDisallowed(<edge>_<i>, ['passenger'])"],
        "assumptions": [
            "demand is passenger-class routed, so disallowing 'passenger' removes all simulated traffic from the lane",
        ],
        "lanes_closed_legacy": n,
    }


def _apply_full_closure(traci_mod, scenario: Scenario, edges: list[str]) -> dict:
    """Close EVERY lane of each affected edge -- a road made impassable (flood, event,
    total reconstruction). Rerouting devices send demand around it."""
    touched, edge_lanes, closed_lanes = _close_lanes(traci_mod, edges, lambda nlanes: nlanes)
    return {
        "intervention_type": "full_closure",
        "edges": touched,
        "edge_lanes": edge_lanes,
        "parameters": dict(scenario.effective_parameters()),
        "closed_lanes": closed_lanes,
        "traci_calls": ["lane.setDisallowed(<edge>_<i>, ['passenger']) on every lane"],
        "assumptions": [
            "full closure disallows the 'passenger' class on every lane; the demand model is passenger-class routed, so the edge is impassable to all simulated traffic",
        ],
        "lanes_closed_legacy": max(edge_lanes.values(), default=0),
    }


def _apply_speed_change(traci_mod, scenario: Scenario, edges: list[str]) -> dict:
    """Set a new speed limit on each affected edge (traffic calming / school zone)."""
    kph = float(scenario.effective_parameters()["max_speed_kph"])
    speed_ms = round(kph * KPH_TO_MS, 3)
    exc = getattr(traci_mod, "TraCIException", Exception)
    touched: list[str] = []
    edge_lanes: dict[str, int] = {}
    for eid in edges:
        try:
            edge_lanes[eid] = traci_mod.edge.getLaneNumber(eid)
            traci_mod.edge.setMaxSpeed(eid, speed_ms)
            touched.append(eid)
        except exc:
            continue
    return {
        "intervention_type": "speed_change",
        "edges": touched,
        "edge_lanes": edge_lanes,
        "parameters": {"max_speed_kph": kph, "max_speed_ms": speed_ms},
        "traci_calls": ["edge.setMaxSpeed(<edge>, m/s)"],
        "assumptions": [
            "speed limit applied to all lanes of each affected edge for the whole simulation window",
        ],
        "lanes_closed_legacy": 0,
    }


def _apply_capacity_change(traci_mod, scenario: Scenario, edges: list[str]) -> dict:
    """Scale per-lane max speeds by `capacity_factor` as a CAPACITY PROXY (>1 widening,
    <1 road diet). SUMO cannot add or remove physical lanes at runtime, so the proxy is
    declared honestly in the assumptions and the per-lane before/after speeds are
    recorded for inspection."""
    factor = float(scenario.effective_parameters()["capacity_factor"])
    exc = getattr(traci_mod, "TraCIException", Exception)
    touched: list[str] = []
    edge_lanes: dict[str, int] = {}
    lane_speeds_ms: dict[str, list[float]] = {}  # lane id -> [before, after]
    for eid in edges:
        try:
            nlanes = traci_mod.edge.getLaneNumber(eid)
            edge_lanes[eid] = nlanes
            for i in range(nlanes):
                lid = f"{eid}_{i}"
                before = traci_mod.lane.getMaxSpeed(lid)
                after = round(before * factor, 3)
                traci_mod.lane.setMaxSpeed(lid, after)
                lane_speeds_ms[lid] = [round(before, 3), after]
            touched.append(eid)
        except exc:
            continue
    return {
        "intervention_type": "capacity_change",
        "edges": touched,
        "edge_lanes": edge_lanes,
        "parameters": {"capacity_factor": factor},
        "lane_speeds_ms": lane_speeds_ms,
        "traci_calls": ["lane.getMaxSpeed(<lane>)", "lane.setMaxSpeed(<lane>, m/s)"],
        "assumptions": [
            "PROXY: SUMO cannot add/remove physical lanes at runtime; capacity change is approximated by scaling each lane's max speed by capacity_factor",
            "throughput response to a speed-scaled proxy understates queue-discharge effects of a real added lane; treat capacity_change deltas as directional",
        ],
        "lanes_closed_legacy": 0,
    }


_HANDLERS = {
    "lane_closure": _apply_lane_closure,
    "full_closure": _apply_full_closure,
    "speed_change": _apply_speed_change,
    "capacity_change": _apply_capacity_change,
}


def apply_intervention(traci_mod, scenario: Scenario, edges: list[str]) -> dict:
    """Dispatch the scenario's intervention to its TraCI handler against the already-
    resolved `edges`. Returns the dispatch record (exact parameters applied, edges
    touched, TraCI calls, assumptions) which the runner stores verbatim in
    ``Trajectory.meta["applied"]`` -- the glass-box provenance of the network edit."""
    handler = _HANDLERS.get(scenario.intervention_type)
    if handler is None:  # defensive: Scenario.__post_init__ already validates
        raise ValueError(
            f"unknown intervention_type {scenario.intervention_type!r}; "
            f"expected one of {INTERVENTION_TYPES}"
        )
    return handler(traci_mod, scenario, edges)
