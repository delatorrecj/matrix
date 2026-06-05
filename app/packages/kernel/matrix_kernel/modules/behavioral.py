"""Behavioral impact module (U8). Confidence: High (network physics) / Medium (mode behavior).

Scores the ONE scenario trajectory (vs the cached baseline) into three glass-box results --
exactly the equations in docs/methods-matrix.md §3.1:

  BEH-1  Δ trips on the affected corridor (scenario − baseline)  OSM-ILO, OVERTURE, PERSONA-POOL  -> H
  BEH-2  Mode-share shift (±3% anchor)                           PERSONA-POOL, Calderon2014, CCHAIN -> M
  BEH-3  Peak saturation V/C on the corridor                     SUMO-NET, OSM-ILO                  -> H

Confidence is COMPUTED (confidence_rubric, methods §2); the range is EARNED
(earned_confidence_interval, PRD-F15). Numbers come from the trajectory + these equations,
never an LLM (glass box, PRD-F14). DimensionResult's invariants reject any black-box result.
"""
from __future__ import annotations

import random

from matrix_kernel.baseline import SIM_END, load_baseline
from matrix_kernel.confidence import confidence_rubric, earned_confidence_interval
from matrix_kernel.personas import ILOILO_MODE_SHARE
from matrix_kernel.results import DimensionResult
from matrix_kernel.trajectory import Trajectory

_LANE_CAP_VPH = 1800.0  # HCM nominal per-lane capacity (veh/h)


def score(trajectory: Trajectory, datasets=None, baseline: dict | None = None) -> list[DimensionResult]:
    """Three Behavioral DimensionResults from the scenario trajectory vs the baseline.

    `baseline` (edge_id -> count) defaults to the cached nightly baseline from Redis; pass it
    explicitly to score without a live Redis (unit tests)."""
    base = baseline if baseline is not None else load_baseline().edge_counts
    sc = trajectory.edge_counts
    corridor: list[str] = trajectory.meta.get("closed_edges", [])
    edge_lanes: dict = trajectory.meta.get("edge_lanes", {})
    lanes_closed = int(trajectory.meta.get("lanes_closed", 1))
    rng = random.Random(7)
    results: list[DimensionResult] = []

    # ── BEH-1: Δ trips on the affected corridor over the sim window (the headline number) ──
    window_delta = float(sum(sc.get(e, 0) - base.get(e, 0) for e in corridor))
    lo1, hi1 = earned_confidence_interval(
        window_delta, lambda: window_delta * rng.uniform(0.7, 1.3), n=500)
    results.append(DimensionResult(
        dimension="behavioral",
        metric="Δ trips on affected corridor (AM-peak window)",
        equation_id="BEH-1",
        value=window_delta,
        range=(lo1, hi1),
        unit="Δ trips/window",
        confidence=confidence_rubric(["OSM-ILO", "OVERTURE", "PERSONA-POOL"]),
        input_dataset_ids=["OSM-ILO", "OVERTURE", "PERSONA-POOL"],
        references=["Calderon2014"],
        assumptions=[
            f"sim window = {SIM_END:.0f}s AM-peak slice",
            "demand = uncalibrated random baseline (Milestone A; daily expansion deferred)",
            f"corridor = {len(corridor)} edge(s): {corridor[:3]}",
        ],
    ))

    # ── BEH-2: mode-share shift vs the ±3% Iloilo anchor ──
    # Milestone A does not yet model mode choice (no congestion elasticity) -> Δ ≈ 0, stated honestly.
    results.append(DimensionResult(
        dimension="behavioral",
        metric="mode-share shift (jeepney)",
        equation_id="BEH-2",
        value=0.0,
        range=(0.0, 0.0),
        unit="%-points",
        confidence=confidence_rubric(["PERSONA-POOL", "Calderon2014", "CCHAIN"]),
        input_dataset_ids=["PERSONA-POOL", "Calderon2014", "CCHAIN"],
        references=["Calderon2014"],
        assumptions=[
            f"baseline jeepney share = {ILOILO_MODE_SHARE['jeepney']:.0%} (anchor, methods §3.1)",
            "no mode-choice response modeled (Milestone A); needs congestion-elasticity calibration",
        ],
    ))

    # ── BEH-3: peak saturation V/C on the busiest corridor edge ──
    def vc_for(e: str) -> float:
        vol_vph = sc.get(e, 0) * 3600.0 / SIM_END
        lanes_eff = max(1, edge_lanes.get(e, 1) - lanes_closed)
        return vol_vph / (lanes_eff * _LANE_CAP_VPH)

    busiest = max(corridor, key=lambda e: sc.get(e, 0), default=None)
    vc = vc_for(busiest) if busiest else 0.0
    vol_vph = (sc.get(busiest, 0) * 3600.0 / SIM_END) if busiest else 0.0
    lanes_eff = max(1, edge_lanes.get(busiest, 1) - lanes_closed) if busiest else 1
    lo3, hi3 = earned_confidence_interval(
        vc, lambda: vol_vph / (lanes_eff * rng.uniform(1600, 2000)), n=500)
    results.append(DimensionResult(
        dimension="behavioral",
        metric="peak saturation V/C on affected corridor",
        equation_id="BEH-3",
        value=vc,
        range=(lo3, hi3),
        unit="ratio",
        confidence=confidence_rubric(["SUMO-NET", "OSM-ILO"]),
        input_dataset_ids=["SUMO-NET", "OSM-ILO"],
        references=[],
        assumptions=[
            f"capacity = {_LANE_CAP_VPH:.0f} veh/h/lane (HCM nominal)",
            f"{lanes_closed} lane(s) closed on the corridor",
        ],
    ))
    return results
