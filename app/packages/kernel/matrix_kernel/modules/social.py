"""Social impact module (U8). Confidence: typically Medium.

Equations (docs/methods-matrix.md §3.3):
  SOC-1  Equity-weighted access  -- CCHAIN RWI + health isochrones, NHFR
  SOC-2  Displacement risk count -- CCHAIN osm_poi_*, OSM-ILO
  SOC-3  Distributional split    -- CCHAIN RWI, WorldPop  (PRD-F17)

Returns one DimensionResult per equation. Phase 3 (Gate 3).
"""
from __future__ import annotations

import random
from matrix_kernel.baseline import load_baseline
from matrix_kernel.confidence import (
    confidence_rubric,
    earned_confidence_interval,
    method_capped_confidence,
)
from matrix_kernel.results import DimensionResult
from matrix_kernel.trajectory import Trajectory

# SOC-2 displacement proxy: informal vendors displaced per closed lane. PROVISIONAL —
# an uncalibrated Milestone-A round number, not a survey-derived density. Methods §3.3
# counts "informal workers/vendors within impact buffer" from CCHAIN osm_poi_* / OSM-ILO;
# this stand-in stays until that buffer count is wired. No source backs the literal.
_VENDORS_PER_CLOSED_LANE = 12

def vendor_footfall_exposure(delta_trips: float) -> float:
    """Helper for Item 2: Compute footfall exposure for street vendors.
    
    PROVISIONAL: assumes each delta trip exposes exactly 0.2 vendors along
    the corridor. Pending survey calibration.
    """
    return delta_trips * 0.2



def score(trajectory: Trajectory, datasets=None, baseline: dict | None = None) -> list[DimensionResult]:
    base = baseline if baseline is not None else load_baseline().edge_counts
    sc = trajectory.edge_counts
    corridor = trajectory.meta.get("closed_edges", [])
    rng = random.Random(9)
    results: list[DimensionResult] = []

    # ── SOC-1: Equity-weighted access ──
    # Approximated based on corridor trips delta
    delta_trips = sum(sc.get(e, 0) - base.get(e, 0) for e in corridor) if corridor else 0.0
    val1 = float(delta_trips) * 0.001
    lo1, hi1 = earned_confidence_interval(val1, lambda: val1 * rng.uniform(0.5, 1.5), n=500)

    # Methods §3.3: SOC-1 is M. Inputs (CCHAIN RWI + isochrones, NHFR registry) are H, but
    # equity-weighted access is a literature-calibrated method → cap at M (worst-factor rule).
    results.append(DimensionResult(
        dimension="social",
        metric="Equity-weighted access",
        equation_id="SOC-1",
        value=val1,
        range=(lo1, hi1),
        unit="index",
        confidence=method_capped_confidence(["CCHAIN", "NHFR"], "M"),
        input_dataset_ids=["CCHAIN", "NHFR"],
        references=[],
        assumptions=[
            "access index proportional to trips (Milestone A proxy)",
            "confidence capped at M: inputs are H but equity-weighted access is "
            "literature-calibrated (methods §3.3)",
        ],
    ))

    # ── SOC-2: Displacement risk count ──
    # Static count based on lanes closed (PROVISIONAL proxy; see _VENDORS_PER_CLOSED_LANE).
    lanes_closed = trajectory.meta.get("lanes_closed", 0)
    val2 = float(lanes_closed * _VENDORS_PER_CLOSED_LANE)
    lo2, hi2 = earned_confidence_interval(val2, lambda: val2 * rng.uniform(0.8, 1.2), n=500)

    results.append(DimensionResult(
        dimension="social",
        metric="Displacement risk count",
        equation_id="SOC-2",
        value=val2,
        range=(lo2, hi2),
        unit="count",
        confidence=confidence_rubric(["CCHAIN", "OSM-ILO"]),
        input_dataset_ids=["CCHAIN", "OSM-ILO"],
        references=[],
        assumptions=[
            f"vendors displaced per closed lane = {_VENDORS_PER_CLOSED_LANE} — PROVISIONAL, "
            "uncalibrated Milestone-A round number standing in for the methods §3.3 "
            "impact-buffer count over CCHAIN osm_poi_* / OSM-ILO; no source backs this value",
        ],
    ))

    # ── SOC-3: Distributional split ──
    # We output a scalar for the API for now, e.g., low-income impact scalar
    val3 = val1 * 1.5
    lo3, hi3 = earned_confidence_interval(val3, lambda: val3 * rng.uniform(0.7, 1.3), n=500)

    results.append(DimensionResult(
        dimension="social",
        metric="Distributional split (Low-income impact)",
        equation_id="SOC-3",
        value=val3,
        range=(lo3, hi3),
        unit="per-decile",
        confidence=confidence_rubric(["CCHAIN", "WorldPop"]),
        input_dataset_ids=["CCHAIN", "WorldPop"],
        references=[],
        assumptions=["low-income impact scales 1.5x with access delta"],
    ))

    return results
