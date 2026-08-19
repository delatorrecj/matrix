"""Behavioral impact module (U8). Mode-share: Medium. Corridor volumes: Low / directional.

Scores the ONE scenario trajectory (vs the cached baseline) into glass-box results --
exactly the equations in docs/methods-matrix.md §3.1:

  BEH-1  Δ trips on the affected corridor (scenario − baseline)  OSM-ILO, OVERTURE, PERSONA-POOL
         -> L while VAL-01 is a published FAIL (uncalibrated demand; methods §2 validation factor)
  BEH-2  Mode-share shift (±3% anchor)                           PERSONA-POOL, Calderon2014, CCHAIN -> M
  BEH-3  Peak saturation V/C on the corridor                     SUMO-NET, OSM-ILO
         -> L while VAL-01 FAIL (same volume-calibration cap as BEH-1)
  BEH-4  Facility demand redistribution — only when Trajectory.meta carries a demand_delta
         summary (new_facility). Value is the BEH-4 n_total already computed; the module
         does not invent a second number.

Network-physics inputs are High; the VAL-01 validation factor caps *magnitudes*
at L while the gate is FAIL/NOT_RUN, and lifts only on PASS (methods §2: worst
factor includes validation). Confidence is COMPUTED from that factor, never
hardcoded; the range is EARNED (earned_confidence_interval, PRD-F15). Numbers
come from the trajectory + these equations, never an LLM (glass box, PRD-F14).
"""
from __future__ import annotations

import random

from matrix_kernel.baseline import SIM_END, load_baseline
from matrix_kernel.confidence import (
    confidence_rubric,
    earned_confidence_interval,
    validation_capped_confidence,
)
from matrix_kernel.personas import ILOILO_MODE_SHARE
from matrix_kernel.results import Confidence, DimensionResult
from matrix_kernel.trajectory import Trajectory


def _resolve_val01_status(meta: dict) -> str:
    """Prefer an injected gate status (tests); else the published validation report."""
    injected = meta.get("val01_status")
    if injected:
        return str(injected).strip().upper()
    try:
        from matrix_kernel.validation import published_val01_status
        return published_val01_status()
    except Exception:
        return "NOT_RUN"


def _val01_volume_note(status: str) -> str:
    if status == "PASS":
        return (
            "VAL-01 PASS against Calderon 2014 (NRMSE vs threshold in GET /validation) "
            "— corridor volume magnitudes are city-back-tested (demand not fitted to "
            "passenger_flow_max; CR-012 §4)"
        )
    if status == "FAIL":
        return (
            "confidence capped at L: VAL-01 published FAIL against Calderon 2014 "
            "(NRMSE vs threshold in GET /validation) — Iloilo corridor volumes are "
            "directional, not city-calibrated (uncalibrated demand)"
        )
    return (
        "confidence capped at L: VAL-01 not computed (NOT_RUN) — Iloilo corridor "
        "volumes are directional, not city-calibrated"
    )

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
    val01 = _resolve_val01_status(trajectory.meta)
    vol_note = _val01_volume_note(val01)
    beh1_conf: Confidence = validation_capped_confidence(
        ["OSM-ILO", "OVERTURE", "PERSONA-POOL"], val01)
    beh3_conf: Confidence = validation_capped_confidence(["SUMO-NET", "OSM-ILO"], val01)

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
        confidence=beh1_conf,
        input_dataset_ids=["OSM-ILO", "OVERTURE", "PERSONA-POOL"],
        references=["Calderon2014"],
        assumptions=[
            f"sim window = {SIM_END:.0f}s AM-peak slice",
            "demand = uncalibrated random baseline (Milestone A; daily expansion deferred)",
            f"corridor = {len(corridor)} edge(s): {corridor[:3]}",
            vol_note,
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
        confidence=beh3_conf,
        input_dataset_ids=["SUMO-NET", "OSM-ILO"],
        references=[],
        assumptions=[
            f"capacity = {_LANE_CAP_VPH:.0f} veh/h/lane (HCM nominal)",
            f"{lanes_closed} lane(s) closed on the corridor",
            vol_note,
        ],
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
            assumptions=list(demand.get("assumptions") or []),
        ))
    return results
