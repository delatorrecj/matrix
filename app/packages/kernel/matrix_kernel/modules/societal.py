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

# Iloilo City overall population density sourced from PSA 2020 Population Census
# of the Philippines (August 2020 CPH): 457,626 persons / 78.34 km² = 5,843
# persons/km².  This is the city-wide average; actual barangay-level density varies
# from ~500 (peri-urban) to ~25,000 (downtown).  Replacing the previous uncited
# 8,500 placeholder (CR-007 PR 7). Still a single flat figure — per-zone WorldPop
# density is not yet wired (§3.6); that upgrade is tracked to PR 9.
_GENERIC_POP_DENSITY = 5843.0  # persons/km², PSA 2020 CPH Iloilo City average


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
    val3 = eco2_val * _GENERIC_POP_DENSITY  # PM2.5 × generic pop density
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
        assumptions=[
            "uses ECO-2 passed value × population density",
            f"population density = {_GENERIC_POP_DENSITY:.0f} persons/km² (PSA 2020 CPH: "
            "Iloilo City 457,626 persons / 78.34 km²); city-wide average applied uniformly "
            "— PROVISIONAL per-zone weighting; per-zone WorldPop density not yet wired "
            "into the kernel (methods §3.5, §3.6)",
        ],
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
    # Normalize each subscore to [0, 1] before combining (BUG-6 fix: the raw subscores
    # have incompatible units — heritage "score", health-exposure "index" (PM2.5 ×
    # pop_density, can be 1000s), walkability "score" — so they cannot be summed directly).
    # Domain bounds derived from plausible ranges for Iloilo City scenarios:
    _HERITAGE_BOUND = 10.0     # heritage proximity scores rarely exceed ±10
    _HEALTH_BOUND = 500.0      # PM2.5_proxy × 5843 pop_density; plausible max ~500
    _WALK_BOUND = 5.0          # walkability delta scores rarely exceed ±5
    # Normalize: map raw value from [-bound, +bound] → [0, 1], clamped.
    def _norm(raw: float, bound: float) -> float:
        return max(0.0, min(1.0, (raw + bound) / (2.0 * bound)))
    n_heritage = _norm(val2, _HERITAGE_BOUND)
    n_health   = _norm(-val3, _HEALTH_BOUND)   # negative: lower health exposure is better
    n_walk     = _norm(val4, _WALK_BOUND)

    # Weights (sum to 1.0): heritage preservation (25%), health protection (40%),
    # walkability (35%). Derived from Iloilo CLUP/CDP priority ranking (health > walkability
    # > heritage for urban development planning). PROVISIONAL — subject to stakeholder
    # calibration.
    _W_HERITAGE = 0.25
    _W_HEALTH = 0.40
    _W_WALK = 0.35
    val1 = (n_heritage * _W_HERITAGE + n_health * _W_HEALTH + n_walk * _W_WALK) * 100.0
    val1 = max(0.0, min(100.0, val1))  # clamp to [0, 100]

    lo1, hi1 = earned_confidence_interval(val1, lambda: max(0.0, min(100.0, val1 * rng.uniform(0.8, 1.2))), n=500)

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
        assumptions=[
            "composite of SOCI-2, SOCI-3, SOCI-4 — normalized to [0,1] before combining",
            f"normalization bounds: heritage ±{_HERITAGE_BOUND}, health ±{_HEALTH_BOUND}, "
            f"walkability ±{_WALK_BOUND} (plausible Iloilo scenario ranges)",
            f"weights: heritage={_W_HERITAGE}, health={_W_HEALTH}, walkability={_W_WALK} "
            "(sum=1.0; derived from Iloilo CLUP/CDP urban priority ranking — PROVISIONAL, "
            "subject to stakeholder calibration)",
            "output clamped to [0, 100]; 50 = no net change from baseline",
        ],
    )
    results.insert(0, res1)

    return results

