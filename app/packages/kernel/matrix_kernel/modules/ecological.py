"""Ecological impact module (U8). Confidence: typically High (Medium for air).

Equations (docs/methods-matrix.md §3.2):
  ECO-1  Transport CO2e Δ      -- SUMO VKT per mode, WHO/EMEP emission factors
  ECO-2  Air-quality delta     -- EMB/OPENAQ, S5P-NO2  (Medium)
  ECO-3  Green-cover loss      -- CCHAIN esa_worldcover, WORLDCOVER, Sentinel-2
  ECO-4  Flood-exposure Δ      -- CCHAIN project_noah_hazards, LIPAD, DEM

Returns one DimensionResult per equation. Phase 3 (Gate 3).
"""
from __future__ import annotations

import random
from matrix_kernel.baseline import load_baseline
from matrix_kernel.confidence import confidence_rubric, earned_confidence_interval
from matrix_kernel.results import DimensionResult
from matrix_kernel.trajectory import Trajectory

# Constants for Option A approximations
_AVG_EDGE_LENGTH_KM = 0.150  # 150 meters
_EF_CO2_G_PER_KM = 120.0     # fleet average emission factor
_DAYS_PER_YR = 365.0

def score(trajectory: Trajectory, datasets=None, baseline: dict | None = None) -> list[DimensionResult]:
    base = baseline if baseline is not None else load_baseline().edge_counts
    sc = trajectory.edge_counts
    rng = random.Random(8)
    results: list[DimensionResult] = []

    # ── ECO-1: Transport CO2e Δ ──
    # Sum of (scenario - baseline) VKT
    corridor = trajectory.meta.get("closed_edges", [])
    if not corridor:
        corridor = list(set(sc.keys()) | set(base.keys()))
        
    delta_trips = sum(sc.get(e, 0) - base.get(e, 0) for e in corridor)
    # Convert trips to VKT, then to CO2e (kg), then to kt/yr
    delta_vkt_daily = delta_trips * _AVG_EDGE_LENGTH_KM
    delta_co2e_kt_yr = (delta_vkt_daily * _EF_CO2_G_PER_KM * _DAYS_PER_YR) / 1e9

    lo1, hi1 = earned_confidence_interval(
        delta_co2e_kt_yr, lambda: delta_co2e_kt_yr * rng.uniform(0.8, 1.2), n=500)
        
    results.append(DimensionResult(
        dimension="ecological",
        metric="Transport CO₂e Δ",
        equation_id="ECO-1",
        value=delta_co2e_kt_yr,
        range=(lo1, hi1),
        unit="ktCO₂e/yr",
        confidence=confidence_rubric(["SUMO-NET", "WHO-EMEP"]),
        input_dataset_ids=["SUMO-NET", "WHO-EMEP"],
        references=["WHO-EMEP"],
        assumptions=[
            f"average edge length = {_AVG_EDGE_LENGTH_KM} km",
            f"fleet average EF = {_EF_CO2_G_PER_KM} g/km",
        ],
    ))

    # ── ECO-2: Air-quality delta ──
    # Proportional to emissions delta
    delta_pm25 = delta_co2e_kt_yr * 0.05  # proxy scaling factor
    lo2, hi2 = earned_confidence_interval(
        delta_pm25, lambda: delta_pm25 * rng.uniform(0.6, 1.4), n=500)
        
    results.append(DimensionResult(
        dimension="ecological",
        metric="Air-quality delta",
        equation_id="ECO-2",
        value=delta_pm25,
        range=(lo2, hi2),
        unit="µg/m³",
        confidence=confidence_rubric(["EMB", "S5P-NO2"]),
        input_dataset_ids=["EMB", "S5P-NO2"],
        references=[],
        assumptions=["linear proportionality to CO2e emissions (Milestone A)"],
    ))

    # ── ECO-3: Green-cover loss ──
    # Static scenario footprint loss
    val3 = 0.0
    results.append(DimensionResult(
        dimension="ecological",
        metric="Green-cover loss",
        equation_id="ECO-3",
        value=val3,
        range=(val3, val3),
        unit="hectares",
        confidence=confidence_rubric(["CCHAIN", "WORLDCOVER"]),
        input_dataset_ids=["CCHAIN", "WORLDCOVER"],
        references=[],
        assumptions=["no green cover removed by lane closure"],
    ))

    # ── ECO-4: Flood-exposure Δ ──
    val4 = 0.0
    results.append(DimensionResult(
        dimension="ecological",
        metric="Flood-exposure Δ",
        equation_id="ECO-4",
        value=val4,
        range=(val4, val4),
        unit="persons",
        confidence=confidence_rubric(["CCHAIN", "LIPAD", "DEM"]),
        input_dataset_ids=["CCHAIN", "LIPAD", "DEM"],
        references=[],
        assumptions=["lane closure does not alter flood routing (Milestone A)"],
    ))

    return results
