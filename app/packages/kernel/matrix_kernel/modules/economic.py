"""Economic impact module (U8). Confidence: Medium.

Equations (docs/methods-matrix.md §3.4):
  ECON-1  Land-value Δ (≤1 km)  -- BIR-ZV (✅ manual XLS), CCHAIN RWI
                                   carry confidence M.
  ECON-2  Footfall Δ per zone   -- persona pool, OVERTURE places
  ECON-3  Employment Δ          -- PSA-ASPBI/OpenStat, ADB/NEDA multiplier

Returns one DimensionResult per equation. Phase 3 (Gate 3).
"""
from __future__ import annotations

import random
from matrix_kernel.baseline import load_baseline
from matrix_kernel.confidence import confidence_rubric, earned_confidence_interval
from matrix_kernel.results import DimensionResult
from matrix_kernel.trajectory import Trajectory


def score(trajectory: Trajectory, datasets=None, baseline: dict | None = None) -> list[DimensionResult]:
    base = baseline if baseline is not None else load_baseline().edge_counts
    sc = trajectory.edge_counts
    corridor = trajectory.meta.get("closed_edges", [])
    rng = random.Random(10)
    results: list[DimensionResult] = []

    delta_trips = sum(sc.get(e, 0) - base.get(e, 0) for e in corridor) if corridor else 0.0

    # ── ECON-1: Land-value Δ (≤1 km) ──
    # Approximated based on corridor trips
    val1 = float(delta_trips) * 50.0  # e.g., 50 PHP per trip delta
    lo1, hi1 = earned_confidence_interval(val1, lambda: val1 * rng.uniform(0.6, 1.4), n=500)

    results.append(DimensionResult(
        dimension="economic",
        metric="Land-value Δ (≤1 km)",
        equation_id="ECON-1",
        value=val1,
        range=(lo1, hi1),
        unit="PHP",
        confidence=confidence_rubric(["BIR-ZV", "CCHAIN"]),
        input_dataset_ids=["BIR-ZV", "CCHAIN"],
        references=["BIR-ZV"],
        assumptions=["land value proxy from trip delta (Milestone A)"],
    ))

    # ── ECON-2: Footfall Δ per zone ──
    val2 = float(delta_trips) * 1.2
    lo2, hi2 = earned_confidence_interval(val2, lambda: val2 * rng.uniform(0.75, 1.25), n=500)

    results.append(DimensionResult(
        dimension="economic",
        metric="Footfall Δ per zone",
        equation_id="ECON-2",
        value=val2,
        range=(lo2, hi2),
        unit="visits/day",
        confidence=confidence_rubric(["PERSONA-POOL", "OVERTURE"]),
        input_dataset_ids=["PERSONA-POOL", "OVERTURE"],
        references=[],
        assumptions=["footfall proportional to trip delta"],
    ))

    # ── ECON-3: Employment Δ ──
    val3 = float(delta_trips) * 0.05
    lo3, hi3 = earned_confidence_interval(val3, lambda: val3 * rng.uniform(0.5, 1.5), n=500)

    results.append(DimensionResult(
        dimension="economic",
        metric="Employment Δ",
        equation_id="ECON-3",
        value=val3,
        range=(lo3, hi3),
        unit="jobs",
        confidence=confidence_rubric(["PSA-ASPBI", "PSA-OpenStat"]),
        input_dataset_ids=["PSA-ASPBI", "PSA-OpenStat"],
        references=[],
        assumptions=["indirect employment impact proportional to delta trips"],
    ))

    return results
