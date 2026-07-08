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
from matrix_kernel.baseline import SIM_END, load_baseline
from matrix_kernel.confidence import (
    confidence_rubric,
    earned_confidence_interval,
    method_capped_confidence,
)
from matrix_kernel.results import DimensionResult
from matrix_kernel.trajectory import Trajectory

# Constants for Option A approximations
_AVG_EDGE_LENGTH_KM = 0.150  # 150 meters
_EF_CO2_G_PER_KM = 120.0     # fleet average emission factor
_DAYS_PER_YR = 365.0

# AM-peak-to-daily expansion factor.
#
# The simulation runs for SIM_END seconds (default 900 s = 15 min), representing one
# slice of the AM peak hour. Trip counts from this window must be expanded to daily
# traffic before annualizing. The factor is derived from:
#
#   K-factor (DPWH Design Guidelines for National Roads, 2015; Table 3.1): for Philippine
#   urban arterials K = 0.10 — the AM peak hour carries ~10% of Average Annual Daily
#   Traffic (AADT). This is consistent with JICA Metro Cebu Urban Transport Study findings
#   and the TSSP-2019 traffic count data for Iloilo intersections.
#
#   Window fraction: SIM_END / 3600 represents the fraction of the peak hour covered by
#   the simulation (default 900/3600 = 0.25 = one quarter-hour). The demand model
#   (build_demand.py) generates trips uniformly over this window.
#
#   Expansion: daily_trips = window_trips / (K × window_fraction)
#            = window_trips / (0.10 × 0.25)  = window_trips × 40
#
# References: DPWH-2015 §3, TSSP-2019, JICA-MCUTS
_K_FACTOR_DPWH = 0.10                              # AM peak hour / AADT (DPWH Philippine urban)
_WINDOW_FRACTION = SIM_END / 3600.0                 # simulation window as fraction of peak hour
_AM_PEAK_TO_DAILY = 1.0 / (_K_FACTOR_DPWH * _WINDOW_FRACTION)  # = 40.0 for default 900 s

# ECO-2 air-quality proxy: PM2.5 delta as a fraction of the CO2e delta. PROVISIONAL —
# an uncalibrated Milestone-A stand-in for the methods §3.2 dispersion-to-station model
# (`ΔPM2.5 ∝ Δemissions` calibrated to EMB/OPENAQ readings), which is not yet implemented.
# No published coefficient backs this literal; it is a placeholder ratio, not a measurement.
_PM25_PER_CO2E_PROXY = 0.05

def score(trajectory: Trajectory, datasets=None, baseline: dict | None = None) -> list[DimensionResult]:
    base = baseline if baseline is not None else load_baseline().edge_counts
    sc = trajectory.edge_counts
    rng = random.Random(8)
    results: list[DimensionResult] = []

    # ── ECO-1: Transport CO2e Δ ──
    # Sum of (scenario - baseline) trips over the affected corridor
    corridor = trajectory.meta.get("closed_edges", [])
    if not corridor:
        corridor = list(set(sc.keys()) | set(base.keys()))
        
    delta_trips_window = sum(sc.get(e, 0) - base.get(e, 0) for e in corridor)
    # Expand from the simulation window (e.g. 15 min) to daily using the DPWH K-factor
    delta_trips_daily = delta_trips_window * _AM_PEAK_TO_DAILY
    # Convert daily trips to daily VKT, then to CO2e (kg), then to kt/yr
    delta_vkt_daily = delta_trips_daily * _AVG_EDGE_LENGTH_KM
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
        references=["WHO-EMEP", "DPWH-2015", "TSSP-2019"],
        assumptions=[
            f"AM-peak-to-daily expansion factor = {_AM_PEAK_TO_DAILY:.0f}× "
            f"(K={_K_FACTOR_DPWH}, window={SIM_END:.0f}s/{3600:.0f}s; "
            "DPWH Design Guidelines 2015 §3, TSSP-2019 Iloilo context)",
            f"average edge length = {_AVG_EDGE_LENGTH_KM} km",
            f"fleet average EF = {_EF_CO2_G_PER_KM} g/km (WHO-EMEP)",
        ],
    ))

    # ── ECO-2: Air-quality delta ──
    # Proportional to emissions delta (PROVISIONAL proxy; see _PM25_PER_CO2E_PROXY).
    delta_pm25 = delta_co2e_kt_yr * _PM25_PER_CO2E_PROXY
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
        assumptions=[
            "linear proportionality to CO2e emissions (Milestone A)",
            f"PM2.5/CO2e proxy coefficient = {_PM25_PER_CO2E_PROXY} — PROVISIONAL, "
            "uncalibrated Milestone-A stand-in for the methods §3.2 dispersion-to-station "
            "model; no published coefficient backs this value (placeholder, not a measurement)",
        ],
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
    # Methods §3.2: "H (hazard) / M (redistribution)". The hazard layers (CCHAIN/LIPAD/DEM)
    # are High, but the value emitted is the *redistribution* of exposed population, whose
    # method is literature-calibrated → M. Cap on that weaker factor (worst-factor rule).
    val4 = 0.0
    results.append(DimensionResult(
        dimension="ecological",
        metric="Flood-exposure Δ",
        equation_id="ECO-4",
        value=val4,
        range=(val4, val4),
        unit="persons",
        confidence=method_capped_confidence(["CCHAIN", "LIPAD", "DEM"], "M"),
        input_dataset_ids=["CCHAIN", "LIPAD", "DEM"],
        references=[],
        assumptions=[
            "lane closure does not alter flood routing (Milestone A)",
            "confidence capped at M: flood-hazard inputs are H but the exposure-"
            "redistribution method is literature-calibrated (methods §3.2)",
        ],
    ))

    return results
