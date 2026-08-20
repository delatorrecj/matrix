"""Behavioral impact module (U8). Mode-share: not modeled. Corridor volumes: Low / directional.

Scores the ONE scenario trajectory (vs the cached baseline) into glass-box results --
exactly the equations in docs/methods-matrix.md §3.1:

  BEH-1  Δ trips on the affected site (scenario − baseline)
         -> L while VAL-01 is a published FAIL (uncalibrated demand; methods §2 validation factor)
  BEH-2  Mode-share shift — not_modeled (no congestion elasticity)
  BEH-3  Peak saturation V/C on the site — type-aware denominator
         -> L while VAL-01 FAIL
  BEH-4  Facility demand — computed for new_facility; not_applicable otherwise

Network-physics inputs are High; the VAL-01 validation factor caps *magnitudes*
at L while the gate is FAIL/NOT_RUN. Confidence is COMPUTED, never hardcoded.
"""
from __future__ import annotations

import math
import random

from matrix_kernel.baseline import SIM_END, load_baseline
from matrix_kernel.confidence import confidence_rubric, earned_confidence_interval
from matrix_kernel.personas import ILOILO_MODE_SHARE
from matrix_kernel.results import Confidence, DimensionResult
from matrix_kernel.scoring_aperture import (
    REROUTING_ASSUMPTION,
    affected_edges,
    applied_parameters,
    intervention_type,
    na_result,
    resolve_val01_status,
    site_delta,
    val01_volume_note,
    volume_confidence,
)
from matrix_kernel.trajectory import Trajectory

_LANE_CAP_VPH = 1800.0  # HCM nominal per-lane capacity (veh/h)


def _capacity_vph(nlanes: int, itype: str, lanes_closed: int, params: dict) -> float:
    """Type-aware remaining capacity (veh/h). No phantom lane on a full closure."""
    nlanes = max(0, int(nlanes))
    if itype == "full_closure":
        return 0.0
    if itype == "capacity_change":
        factor = float(params.get("capacity_factor") or 1.0)
        return nlanes * _LANE_CAP_VPH * factor
    if itype == "lane_closure":
        remaining = max(0, nlanes - int(lanes_closed))
        return remaining * _LANE_CAP_VPH
    # speed_change / new_facility / unknown: geometric lanes; do not pretend capacity changed
    return nlanes * _LANE_CAP_VPH


def score(trajectory: Trajectory, datasets=None, baseline: dict | None = None) -> list[DimensionResult]:
    """Behavioral DimensionResults from the scenario trajectory vs the baseline."""
    base = baseline if baseline is not None else load_baseline().edge_counts
    sc = trajectory.edge_counts
    corridor = affected_edges(trajectory.meta)
    edge_lanes: dict = trajectory.meta.get("edge_lanes") or {}
    lanes_closed = int(trajectory.meta.get("lanes_closed", 0) or 0)
    itype = intervention_type(trajectory)
    params = applied_parameters(trajectory)
    rng = random.Random(7)
    results: list[DimensionResult] = []
    val01 = resolve_val01_status(trajectory.meta)
    vol_note = val01_volume_note(val01)
    beh1_conf: Confidence = volume_confidence(
        ["OSM-ILO", "OVERTURE", "PERSONA-POOL"], val01, pass_method="H"
    )
    beh3_conf: Confidence = volume_confidence(["SUMO-NET", "OSM-ILO"], val01, pass_method="H")

    window_delta = site_delta(trajectory, base)
    lo1, hi1 = earned_confidence_interval(
        window_delta, lambda: window_delta * rng.uniform(0.7, 1.3), n=500)
    results.append(DimensionResult(
        dimension="behavioral",
        metric="Δ trips on affected corridor (AM-peak window)",
        equation_id="BEH-1",
        value=window_delta,
        range=(lo1, hi1),
        unit="Δ trips/window",
        confidence=beh1_conf,
        input_dataset_ids=["OSM-ILO", "OVERTURE", "PERSONA-POOL"],
        references=["Calderon2014"],
        assumptions=[
            f"sim window = {SIM_END:.0f}s AM-peak slice",
            "demand = uncalibrated random baseline (Milestone A; daily expansion deferred)",
            f"site = {len(corridor)} edge(s): {corridor[:3]}",
            "BEH-1 is Δ vehicles entering the intervention site, not citywide trip count",
            vol_note,
            REROUTING_ASSUMPTION,
        ],
    ))

    results.append(na_result(
        dimension="behavioral",
        metric="mode-share shift (jeepney)",
        equation_id="BEH-2",
        unit="%-points",
        input_dataset_ids=["PERSONA-POOL", "Calderon2014", "CCHAIN"],
        applicability="not_modeled",
        confidence=confidence_rubric(["PERSONA-POOL", "Calderon2014", "CCHAIN"]),
        references=["Calderon2014"],
        assumptions=[
            f"baseline jeepney share = {ILOILO_MODE_SHARE['jeepney']:.0%} (anchor, methods §3.1)",
            "not modeled: no congestion-elasticity / mode-choice response in the kernel",
        ],
    ))

    def vc_for(e: str) -> float:
        vol_vph = sc.get(e, 0) * 3600.0 / SIM_END
        cap = _capacity_vph(edge_lanes.get(e, 1), itype, lanes_closed, params)
        if cap <= 0:
            return 0.0 if vol_vph == 0 else math.inf
        return vol_vph / cap

    busiest = max(corridor, key=lambda e: sc.get(e, 0), default=None)
    raw_vc = vc_for(busiest) if busiest else 0.0
    # Bound a theoretically infinite V/C so DimensionResult.range stays finite.
    vc = 99.0 if not math.isfinite(raw_vc) else raw_vc
    vol_vph = (sc.get(busiest, 0) * 3600.0 / SIM_END) if busiest else 0.0
    cap = _capacity_vph(edge_lanes.get(busiest, 1), itype, lanes_closed, params) if busiest else 0.0
    lo3, hi3 = earned_confidence_interval(
        vc,
        lambda: (vol_vph / cap) if cap > 0 else vc,
        n=500,
    )
    beh3_assumptions = [
        f"capacity = {_LANE_CAP_VPH:.0f} veh/h/lane (HCM nominal)",
        f"intervention_type = {itype}",
        vol_note,
        REROUTING_ASSUMPTION,
    ]
    if itype == "full_closure":
        beh3_assumptions.append(
            "full_closure remaining lanes = 0 (no phantom open lane); V/C is 0 when the edge is empty"
        )
    elif itype == "capacity_change":
        factor = float(params.get("capacity_factor") or 1.0)
        beh3_assumptions.append(
            f"denominator = lanes × {_LANE_CAP_VPH:.0f} × capacity_factor {factor:g} "
            "(TraCI still uses a speed proxy; this is the scored capacity)"
        )
    elif itype == "speed_change":
        beh3_assumptions.append(
            "V/C uses geometric lanes — not a speed-adjusted capacity"
        )
    elif itype == "lane_closure":
        beh3_assumptions.append(f"{lanes_closed} lane(s) closed on the corridor")
    else:
        beh3_assumptions.append("lanes_closed does not apply; geometric lane count used")

    results.append(DimensionResult(
        dimension="behavioral",
        metric="peak saturation V/C on affected corridor",
        equation_id="BEH-3",
        value=vc,
        range=(lo3, hi3),
        unit="ratio",
        confidence=beh3_conf,
        input_dataset_ids=["SUMO-NET", "OSM-ILO"],
        references=[],
        assumptions=beh3_assumptions,
    ))

    demand = trajectory.meta.get("demand_delta")
    if isinstance(demand, dict) and demand.get("equation_id") == "BEH-4":
        datasets = list(demand.get("input_dataset_ids") or [])
        if not datasets:
            raise ValueError("BEH-4: demand_delta missing input_dataset_ids (glass-box, PRD-F14)")
        conf = demand.get("confidence")
        if conf not in ("H", "M", "L"):
            raise ValueError("BEH-4: demand_delta missing computed confidence (glass-box, PRD-F14)")
        value = float(demand["demand_trips_total"])
        assumptions = list(demand.get("assumptions") or [])
        assumptions.append(
            "BEH-4 value is the gravity-model total; TraCI injection is capped at 80 vehicles "
            "(physics deferred — the simulated network is a sample of this demand)"
        )
        results.append(DimensionResult(
            dimension="behavioral",
            metric="facility demand redistribution (AM-peak window)",
            equation_id="BEH-4",
            value=value,
            range=(value, value),
            unit=str(demand.get("unit") or "trips/window"),
            confidence=conf,
            input_dataset_ids=datasets,
            references=list(demand.get("references") or []),
            assumptions=assumptions,
        ))
    else:
        results.append(na_result(
            dimension="behavioral",
            metric="facility demand redistribution (AM-peak window)",
            equation_id="BEH-4",
            unit="trips/window",
            input_dataset_ids=["Calderon2014"],
            applicability="not_applicable",
            confidence="L",
            references=["Calderon2014"],
            assumptions=["not applicable: BEH-4 only runs for new_facility interventions"],
        ))
    return results
