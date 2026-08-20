"""Economic impact module (U8).

Equations (docs/methods-matrix.md §3.4):
  ECON-1  Land-value Δ (≤1 km)  -- BIR-ZV median CR zonal × accessibility uplift
  ECON-2  Footfall Δ per zone   -- persona pool, OVERTURE places
  ECON-3  Employment Δ          -- PSA-ASPBI/OpenStat, ADB/NEDA multiplier

Returns one DimensionResult per equation.
"""
from __future__ import annotations

import random

from matrix_kernel.baseline import load_baseline
from matrix_kernel.confidence import (
    earned_confidence_interval,
    provisional_capped_confidence,
)
from matrix_kernel.datasets import bir_median_commercial_php_sqm
from matrix_kernel.results import DimensionResult
from matrix_kernel.scoring_aperture import (
    REROUTING_ASSUMPTION,
    network_delta,
    resolve_val01_status,
    val01_volume_note,
    volume_confidence,
)
from matrix_kernel.trajectory import Trajectory

# Fallback only when BIR CSV is missing (tests / incomplete checkout).
_PHP_PER_TRIP_PROXY = 50.0
# Declared corridor impact footprint for ΔLV = LV_base · footprint · uplift (methods §3.4).
_IMPACT_FOOTPRINT_SQM = 1_000.0
# Literature-style accessibility → land-value elasticity (tier M planning norm).
_LV_ACCESSIBILITY_ELASTICITY = 0.08


def _econ1_land_value_delta(delta_trips: float, base_trips: float) -> tuple[float, list[str], str, list[str]]:
    """Return (value, assumptions, confidence_mode, input_ids).

    confidence_mode: "bir" → method_capped M; "proxy" → provisional L.
    """
    bir = bir_median_commercial_php_sqm()
    if bir is None:
        val = float(delta_trips) * _PHP_PER_TRIP_PROXY
        return (
            val,
            [
                "BIR zonal CSV missing — fallback ₱/trip proxy",
                f"land-value proxy = ₱{_PHP_PER_TRIP_PROXY:g} per unit trip delta — PROVISIONAL",
                "confidence capped at L: §3.6 fallback (methods §2)",
            ],
            "proxy",
            ["BIR-ZV", "CCHAIN"],
        )

    lv_base, n_rows = bir
    denom = max(abs(base_trips), 1.0)
    delta_acc = float(delta_trips) / denom
    uplift = max(-0.25, min(0.25, _LV_ACCESSIBILITY_ELASTICITY * delta_acc))
    val = lv_base * _IMPACT_FOOTPRINT_SQM * uplift
    return (
        val,
        [
            f"LV_base = median CR zonal ₱{lv_base:,.0f}/sqm from BIR RDO 74 ({n_rows} CR rows)",
            f"footprint = {_IMPACT_FOOTPRINT_SQM:g} sqm (declared corridor impact buffer)",
            f"uplift = clamp(elasticity×Δtrips/base_trips, ±25%) "
            f"elasticity={_LV_ACCESSIBILITY_ELASTICITY} (planning norm, tier M)",
            f"Δaccessibility proxy = {delta_acc:.4f}; uplift = {uplift:.4f}",
            "equation: ΔLV = LV_base · footprint · uplift (methods §3.4)",
        ],
        "bir",
        ["BIR-ZV", "CCHAIN"],
    )


def score(trajectory: Trajectory, datasets=None, baseline: dict | None = None) -> list[DimensionResult]:
    base = baseline if baseline is not None else load_baseline().edge_counts
    rng = random.Random(10)
    results: list[DimensionResult] = []
    val01 = resolve_val01_status(trajectory.meta)
    vol_note = val01_volume_note(val01)

    delta_trips = network_delta(trajectory, base)
    base_trips = float(sum(base.values())) if base else 0.0

    # ── ECON-1: Land-value Δ (≤1 km) ──
    val1, assumptions1, mode, ids = _econ1_land_value_delta(delta_trips, base_trips)
    assumptions1 = assumptions1 + [vol_note, REROUTING_ASSUMPTION]
    lo1, hi1 = earned_confidence_interval(val1, lambda: val1 * rng.uniform(0.6, 1.4), n=500)
    conf = (
        provisional_capped_confidence(ids)
        if mode == "proxy"
        else volume_confidence(ids, val01, pass_method="M")
    )

    results.append(DimensionResult(
        dimension="economic",
        metric="Land-value Δ (≤1 km)",
        equation_id="ECON-1",
        value=val1,
        range=(lo1, hi1),
        unit="PHP",
        confidence=conf,
        input_dataset_ids=ids,
        references=["BIR-ZV"],
        assumptions=assumptions1,
    ))

    # ── ECON-2: Footfall Δ per zone ──
    places = None
    try:
        from matrix_kernel.datasets import overture_place_count_proxy
        places = overture_place_count_proxy()
    except Exception:
        places = None
    if places is None:
        val2 = float(delta_trips) * 1.2
        conf2 = volume_confidence(["PERSONA-POOL", "OVERTURE"], val01, pass_method="L")
        assumptions2 = [
            "Overture/OSM places missing — footfall = Δtrips × 1.2 scalar stand-in",
            "confidence capped at L",
            vol_note,
            REROUTING_ASSUMPTION,
        ]
    else:
        n_places, place_src = places
        # Scale footfall by places density proxy (methods §3.4 form with sourced factor).
        places_factor = max(0.5, min(2.0, n_places / 10_000.0))
        val2 = float(delta_trips) * 1.2 * places_factor
        conf2 = volume_confidence(["PERSONA-POOL", "OVERTURE"], val01, pass_method="M")
        assumptions2 = [
            f"footfall = Δtrips × 1.2 × places_factor ({places_factor:.3f})",
            f"places_factor from {place_src}",
            "equation: methods §3.4 footfall ∝ trip delta × places density",
            vol_note,
            REROUTING_ASSUMPTION,
        ]

    lo2, hi2 = earned_confidence_interval(val2, lambda: val2 * rng.uniform(0.75, 1.25), n=500)

    results.append(DimensionResult(
        dimension="economic",
        metric="Footfall Δ per zone",
        equation_id="ECON-2",
        value=val2,
        range=(lo2, hi2),
        unit="visits/day",
        confidence=conf2,
        input_dataset_ids=["PERSONA-POOL", "OVERTURE"],
        references=[],
        assumptions=assumptions2,
    ))

    # ── ECON-3: Employment Δ ──
    aspbi = None
    try:
        from matrix_kernel.datasets import western_visayas_aspbi_employment
        aspbi = western_visayas_aspbi_employment()
    except Exception:
        aspbi = None
    if aspbi is None:
        val3 = float(delta_trips) * 0.05
        conf3 = volume_confidence(["PSA-ASPBI", "PSA-OpenStat"], val01, pass_method="L")
        assumptions3 = [
            "PSA ASPBI missing — employment = Δtrips × 0.05 scalar stand-in",
            "confidence capped at L",
            vol_note,
            REROUTING_ASSUMPTION,
        ]
    else:
        emp_base, emp_src = aspbi
        denom = max(abs(base_trips), 1.0)
        share = float(delta_trips) / denom
        # Jobs Δ ≈ regional employment × corridor trip-share × small multiplier
        val3 = emp_base * share * 0.001
        conf3 = volume_confidence(["PSA-ASPBI", "PSA-OpenStat"], val01, pass_method="M")
        assumptions3 = [
            f"regional employment base = {emp_base:,.0f} ({emp_src})",
            f"network trip share = {share:.4f}; jobs = emp × share × 0.001",
            "equation: direct+indirect employment proxy from PSA ASPBI (methods §3.4)",
            vol_note,
            REROUTING_ASSUMPTION,
        ]

    lo3, hi3 = earned_confidence_interval(val3, lambda: val3 * rng.uniform(0.5, 1.5), n=500)

    results.append(DimensionResult(
        dimension="economic",
        metric="Employment Δ",
        equation_id="ECON-3",
        value=val3,
        range=(lo3, hi3),
        unit="jobs",
        confidence=conf3,
        input_dataset_ids=["PSA-ASPBI", "PSA-OpenStat"],
        references=[],
        assumptions=assumptions3,
    ))

    return results
