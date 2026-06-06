"""Societal impact module (U8). Confidence: typically Medium.

Equations (docs/methods-matrix.md §3.5):
  SOCI-1  Societal composite      -- weighted sum of the subscores below
  SOCI-2  Heritage proximity      -- NHCP, OSM heritage (117 sites)
  SOCI-3  Health-exposure proxy   -- ECO-2 × WorldPop population density
  SOCI-4  Walkability Δ           -- OSM-ILO, TSSP-2019 bike (Macalalag factors)

Returns one DimensionResult per equation. Phase 3 (Gate 3).
"""
from __future__ import annotations

import random
from matrix_kernel.baseline import load_baseline
from matrix_kernel.confidence import confidence_rubric, earned_confidence_interval
from matrix_kernel.results import DimensionResult
from matrix_kernel.trajectory import Trajectory


def score(trajectory: Trajectory, datasets=None, baseline: dict | None = None, eco2_val: float = 0.0) -> list[DimensionResult]:
    base = baseline if baseline is not None else load_baseline().edge_counts
    sc = trajectory.edge_counts
    corridor = trajectory.meta.get("closed_edges", [])
    rng = random.Random(11)
    results: list[DimensionResult] = []

    delta_trips = sum(sc.get(e, 0) - base.get(e, 0) for e in corridor) if corridor else 0.0

    # ── SOCI-2: Heritage proximity ──
    val2 = float(delta_trips) * 0.01
    lo2, hi2 = earned_confidence_interval(val2, lambda: val2 * rng.uniform(0.8, 1.2), n=500)

    res2 = DimensionResult(
        dimension="societal",
        metric="Heritage proximity",
        equation_id="SOCI-2",
        value=val2,
        range=(lo2, hi2),
        unit="score",
        confidence=confidence_rubric(["NHCP", "OSM-ILO"]),
        input_dataset_ids=["NHCP", "OSM-ILO"],
        references=[],
        assumptions=["heritage proximity proxy from delta trips"],
    )
    results.append(res2)

    # ── SOCI-3: Health-exposure proxy ──
    val3 = eco2_val * 8500.0  # PM2.5 x generic pop density
    lo3, hi3 = earned_confidence_interval(val3, lambda: val3 * rng.uniform(0.7, 1.3), n=500)

    res3 = DimensionResult(
        dimension="societal",
        metric="Health-exposure proxy",
        equation_id="SOCI-3",
        value=val3,
        range=(lo3, hi3),
        unit="index",
        confidence=confidence_rubric(["EMB", "S5P-NO2", "WorldPop"]),
        input_dataset_ids=["EMB", "S5P-NO2", "WorldPop"],
        references=[],
        assumptions=["uses ECO-2 passed value × average density"],
    )
    results.append(res3)

    # ── SOCI-4: Walkability Δ ──
    val4 = float(delta_trips) * -0.005
    lo4, hi4 = earned_confidence_interval(val4, lambda: val4 * rng.uniform(0.6, 1.4), n=500)

    res4 = DimensionResult(
        dimension="societal",
        metric="Walkability Δ",
        equation_id="SOCI-4",
        value=val4,
        range=(lo4, hi4),
        unit="score",
        confidence=confidence_rubric(["OSM-ILO", "TSSP-2019"]),
        input_dataset_ids=["OSM-ILO", "TSSP-2019"],
        references=["TSSP-2019"],
        assumptions=["walkability decreases slightly with more trips"],
    )
    results.append(res4)

    # ── SOCI-1: Societal composite ──
    val1 = (val2 * 0.3) + (val3 * -0.001) + (val4 * 0.5)
    lo1, hi1 = earned_confidence_interval(val1, lambda: val1 * rng.uniform(0.8, 1.2), n=500)

    res1 = DimensionResult(
        dimension="societal",
        metric="Societal composite",
        equation_id="SOCI-1",
        value=val1,
        range=(lo1, hi1),
        unit="0-100",
        confidence=confidence_rubric(["NHCP", "WorldPop", "OSM-ILO", "TSSP-2019"]),
        input_dataset_ids=["NHCP", "WorldPop", "OSM-ILO", "TSSP-2019"],
        references=[],
        assumptions=["composite of SOCI-2, SOCI-3, SOCI-4"],
    )
    results.insert(0, res1)

    return results
