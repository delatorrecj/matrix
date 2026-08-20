"""Ecological impact module (U8).

Equations (docs/methods-matrix.md §3.2):
  ECO-1  Transport CO2e Δ      -- ΔVKT on impacted edges, WHO/EMEP emission factors
  ECO-2  Air-quality delta     -- EMB/OPENAQ, S5P-NO2  (PROVISIONAL L)
  ECO-3  Green-cover loss      -- not_applicable until a construction footprint exists
  ECO-4  Flood-exposure Δ      -- computed only when flood_hazard is set
"""
from __future__ import annotations

import random

from matrix_kernel.baseline import SIM_END, load_baseline
from matrix_kernel.confidence import (
    earned_confidence_interval,
    method_capped_confidence,
    provisional_capped_confidence,
)
from matrix_kernel.results import DimensionResult
from matrix_kernel.scoring_aperture import (
    FALLBACK_EDGE_LENGTH_KM,
    REROUTING_ASSUMPTION,
    na_result,
    resolve_val01_status,
    val01_volume_note,
    volume_confidence,
    vkt_delta_km,
)
from matrix_kernel.trajectory import Trajectory

_EF_CO2_G_PER_KM = 120.0     # fleet average emission factor
_DAYS_PER_YR = 365.0
_PM25_PER_CO2E_PROXY = 0.05


def score(trajectory: Trajectory, datasets=None, baseline: dict | None = None) -> list[DimensionResult]:
    base = baseline if baseline is not None else load_baseline().edge_counts
    rng = random.Random(8)
    results: list[DimensionResult] = []
    val01 = resolve_val01_status(trajectory.meta)
    vol_note = val01_volume_note(val01)

    delta_vkt = vkt_delta_km(trajectory, base)
    used_fallback = not (trajectory.meta.get("edge_lengths_km") or {})
    # 900 s AM-peak slice annualized as if it were a daily total — named, VAL-01-capped.
    delta_co2e_kt_yr = (delta_vkt * _EF_CO2_G_PER_KM * _DAYS_PER_YR) / 1e9

    lo1, hi1 = earned_confidence_interval(
        delta_co2e_kt_yr, lambda: delta_co2e_kt_yr * rng.uniform(0.8, 1.2), n=500)

    eco1_assumptions = [
        f"fleet average EF = {_EF_CO2_G_PER_KM} g/km",
        f"AM-peak window = {SIM_END:.0f}s expanded × {_DAYS_PER_YR:g} as if the slice were a daily total",
        "VKT summed over impacted edges (count changed vs baseline), not the edited site alone",
        vol_note,
        REROUTING_ASSUMPTION,
    ]
    if used_fallback:
        eco1_assumptions.append(
            f"edge length fallback = {FALLBACK_EDGE_LENGTH_KM} km "
            "(runner did not stamp edge_lengths_km)"
        )
    else:
        eco1_assumptions.append("edge lengths from the live SUMO net (m → km)")

    results.append(DimensionResult(
        dimension="ecological",
        metric="Transport CO₂e Δ",
        equation_id="ECO-1",
        value=delta_co2e_kt_yr,
        range=(lo1, hi1),
        unit="ktCO₂e/yr",
        confidence=volume_confidence(["SUMO-NET", "WHO-EMEP"], val01, pass_method="H"),
        input_dataset_ids=["SUMO-NET", "WHO-EMEP"],
        references=["WHO-EMEP"],
        assumptions=eco1_assumptions,
    ))

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
            "OpenAQ/EMB ambient is a scale check only — not a sourced ΔPM2.5/Δemissions "
            "coefficient (fixture median is not a dispersion calibration)",
            REROUTING_ASSUMPTION,
        ],
    ))

    results.append(na_result(
        dimension="ecological",
        metric="Green-cover loss",
        equation_id="ECO-3",
        unit="hectares",
        input_dataset_ids=["CCHAIN", "WORLDCOVER"],
        applicability="not_applicable",
        confidence="H",
        assumptions=[
            "not applicable: no construction footprint on this intervention "
            "(lane/speed/capacity/facility edits do not remove WorldCover cells)"
        ],
    ))

    flood = bool(
        trajectory.meta.get("flood_hazard")
        or trajectory.meta.get("scenario_kind") == "flood"
        or trajectory.meta.get("compound_flood")
    )
    if not flood:
        results.append(na_result(
            dimension="ecological",
            metric="Flood-exposure Δ",
            equation_id="ECO-4",
            unit="persons",
            input_dataset_ids=["CCHAIN", "LIPAD", "DEM"],
            applicability="not_applicable",
            confidence=method_capped_confidence(["CCHAIN", "LIPAD", "DEM"], "M"),
            assumptions=[
                "not applicable: flood-exposure Δ only runs when flood_hazard is set "
                "(a full_closure from flooding must carry that flag — closing lanes is not a flood model)"
            ],
        ))
        return results

    from matrix_kernel.datasets import (
        flood_exposed_population_100yr,
        lipad_hazard_closed_edges,
    )

    loaded = flood_exposed_population_100yr()
    lipad = lipad_hazard_closed_edges()
    corridor = list(trajectory.meta.get("affected_edges") or trajectory.meta.get("closed_edges") or [])
    if loaded is None:
        val4 = 0.0
        assumptions4 = [
            "flood scenario requested but CCHAIN NOAH/WorldPop missing — exposure = 0",
            "confidence capped at M: method maturity (methods §3.2)",
        ]
    else:
        city_exposed, haz_year = loaded
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
