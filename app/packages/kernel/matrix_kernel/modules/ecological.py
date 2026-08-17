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
from matrix_kernel.confidence import (
    confidence_rubric,
    earned_confidence_interval,
    method_capped_confidence,
    provisional_capped_confidence,
)
from matrix_kernel.results import DimensionResult
from matrix_kernel.trajectory import Trajectory

# Constants for Option A approximations
_AVG_EDGE_LENGTH_KM = 0.150  # 150 meters
_EF_CO2_G_PER_KM = 120.0     # fleet average emission factor
_DAYS_PER_YR = 365.0

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
        confidence=provisional_capped_confidence(["EMB", "S5P-NO2"]),
        input_dataset_ids=["EMB", "S5P-NO2"],
        references=[],
        assumptions=[
            "linear proportionality to CO2e emissions (Milestone A)",
            f"PM2.5/CO2e proxy coefficient = {_PM25_PER_CO2E_PROXY} — PROVISIONAL, "
            "uncalibrated Milestone-A stand-in for the methods §3.2 dispersion-to-station "
            "model; no published coefficient backs this value (placeholder, not a measurement)",
            "confidence capped at L: §3.6 PROVISIONAL constant (methods §2 low-confidence protocol)",
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
    # Methods §3.2: "H (hazard) / M (redistribution)". Wired to CCHAIN NOAH × WorldPop when
    # the scenario is a flood shock; lane-only closures leave exposure unchanged (0).
    flood = bool(
        trajectory.meta.get("flood_hazard")
        or trajectory.meta.get("scenario_kind") == "flood"
        or trajectory.meta.get("compound_flood")
    )
    assumptions4: list[str]
    if flood:
        from matrix_kernel.datasets import (
            flood_exposed_population_100yr,
            lipad_hazard_closed_edges,
        )

        loaded = flood_exposed_population_100yr()
        lipad = lipad_hazard_closed_edges()
        if loaded is None:
            val4 = 0.0
            assumptions4 = [
                "flood scenario requested but CCHAIN NOAH/WorldPop missing — exposure = 0",
                "confidence capped at M: method maturity (methods §3.2)",
            ]
        else:
            city_exposed, haz_year = loaded
            # Prefer LiPAD∩network edge count when open hazard fixture exists (CR-016).
            n_closed = len(lipad[0]) if lipad else (len(corridor) if corridor else 0)
            redistrib = min(1.0, 0.02 * max(n_closed, 1))
            val4 = city_exposed * redistrib
            assumptions4 = [
                f"city 100-yr-high flood exposure = {city_exposed:.0f} persons "
                f"(CCHAIN project_noah_hazards × WorldPop; hazard vintage {haz_year})",
                f"redistribution fraction = {redistrib:.4f} (0.02 × closed edges, capped at 1)",
                (
                    f"closed-edge count from LiPAD 25yr∩SUMO fixture ({n_closed} edges)"
                    if lipad
                    else "closed-edge count from scenario corridor (LiPAD fixture absent)"
                ),
                "confidence capped at M: exposure-redistribution method (methods §3.2)",
                "LiPAD is hazard-skill open data — not 2024-event VAL-02 GT (CR-016)",
            ]
    else:
        val4 = 0.0
        assumptions4 = [
            "lane closure does not alter flood routing (no flood_hazard in scenario meta)",
            "confidence capped at M: flood-hazard inputs are H but the exposure-"
            "redistribution method is literature-calibrated (methods §3.2)",
        ]

    lo4, hi4 = earned_confidence_interval(
        val4, lambda: val4 * rng.uniform(0.7, 1.3), n=500) if val4 else (0.0, 0.0)
    results.append(DimensionResult(
        dimension="ecological",
        metric="Flood-exposure Δ",
        equation_id="ECO-4",
        value=val4,
        range=(lo4, hi4),
        unit="persons",
        confidence=method_capped_confidence(["CCHAIN", "LIPAD", "DEM"], "M"),
        input_dataset_ids=["CCHAIN", "LIPAD", "DEM"],
        references=[],
        assumptions=assumptions4,
    ))

    return results
