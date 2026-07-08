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

# ECON-1 land-value proxy: PHP of land-value change per unit trip delta. PROVISIONAL —
# an uncalibrated Milestone-A round number, NOT a BIR-ZV-derived uplift. Methods §3.4 wants
# `ΔLV = LV_base · uplift(Δaccessibility)` off the BIR zonal schedule; this stand-in stays
# until that uplift curve is wired. No source backs the literal ₱/trip figure.
_PHP_PER_TRIP_PROXY = 50.0

# ECON-2 footfall proxy: visits generated per unit trip delta. PROVISIONAL —
# an uncalibrated Milestone-A estimate assuming each trip delta translates to ~1.2
# commercial visits (a trip may pass multiple establishments). Methods §3.4 wants
# `Δfootfall = persona_pool × Overture_POI_density`; this stand-in stays until the
# POI-density model is wired. No published source backs the literal 1.2 factor.
_VISITS_PER_TRIP_DELTA = 1.2

# ECON-3 employment proxy: jobs affected per unit trip delta. PROVISIONAL —
# an uncalibrated Milestone-A estimate derived from the ADB/NEDA indirect-employment
# multiplier concept (methods §3.4): each ~20 trips supports ~1 local job, giving
# 1/20 = 0.05. This is a heuristic, NOT a calibrated PSA-ASPBI employment elasticity.
# The real model wants `ΔE = Σ(sector_employment × accessibility_elasticity)`; this
# stand-in stays until the PSA-ASPBI/OpenStat employment data is wired.
_JOBS_PER_TRIP_DELTA = 0.05


def score(trajectory: Trajectory, datasets=None, baseline: dict | None = None) -> list[DimensionResult]:
    base = baseline if baseline is not None else load_baseline().edge_counts
    sc = trajectory.edge_counts
    corridor = trajectory.meta.get("closed_edges", [])
    rng = random.Random(10)
    results: list[DimensionResult] = []

    delta_trips = sum(sc.get(e, 0) - base.get(e, 0) for e in corridor) if corridor else 0.0

    # ── ECON-1: Land-value Δ (≤1 km) ──
    # Approximated based on corridor trips (PROVISIONAL proxy; see _PHP_PER_TRIP_PROXY).
    val1 = float(delta_trips) * _PHP_PER_TRIP_PROXY
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
        assumptions=[
            "land value proxy from trip delta (Milestone A)",
            f"land-value proxy = ₱{_PHP_PER_TRIP_PROXY:g} per unit trip delta — PROVISIONAL, "
            "uncalibrated Milestone-A round number, NOT a BIR-ZV-derived uplift (methods §3.4 "
            "wants ΔLV = LV_base · uplift(Δaccessibility)); no source backs this ₱/trip figure",
        ],
    ))

    # ── ECON-2: Footfall Δ per zone ──
    # Approximated from corridor trip delta (PROVISIONAL proxy; see _VISITS_PER_TRIP_DELTA).
    val2 = float(delta_trips) * _VISITS_PER_TRIP_DELTA
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
        assumptions=[
            f"footfall proxy = {_VISITS_PER_TRIP_DELTA:g} visits per unit trip delta — "
            "PROVISIONAL, uncalibrated Milestone-A estimate; methods §3.4 wants "
            "Δfootfall from persona-pool × Overture POI density; no published source "
            "backs this literal factor",
        ],
    ))

    # ── ECON-3: Employment Δ ──
    # Approximated from corridor trip delta (PROVISIONAL proxy; see _JOBS_PER_TRIP_DELTA).
    val3 = float(delta_trips) * _JOBS_PER_TRIP_DELTA
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
        assumptions=[
            f"employment proxy = {_JOBS_PER_TRIP_DELTA:g} jobs per unit trip delta — "
            "PROVISIONAL, uncalibrated heuristic from ADB/NEDA indirect-employment "
            "multiplier concept (~1 job per 20 trips); methods §3.4 wants "
            "ΔE = Σ(sector_employment × accessibility_elasticity) from PSA-ASPBI; "
            "no published source backs this literal factor",
        ],
    ))

    return results
