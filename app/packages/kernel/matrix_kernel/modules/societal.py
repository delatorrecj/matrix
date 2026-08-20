"""Societal impact module (U8).

Equations (docs/methods-matrix.md §3.5):
  SOCI-1  Societal composite      -- weighted sum of the subscores below
  SOCI-2  Heritage proximity      -- OSM historic points (NHCP interim)
  SOCI-3  Health-exposure proxy   -- ECO-2 × WorldPop population density
  SOCI-4  Walkability Δ           -- OSM walk/bike density × TSSP-2019 factors
"""
from __future__ import annotations

import math
import random

from matrix_kernel.baseline import load_baseline
from matrix_kernel.confidence import (
    earned_confidence_interval,
    provisional_capped_confidence,
)
from matrix_kernel.datasets import (
    osm_historic_points,
    osm_walk_bike_tag_density,
    tssp2019_walk_factors,
)
from matrix_kernel.results import DimensionResult
from matrix_kernel.scoring_aperture import (
    REROUTING_ASSUMPTION,
    network_delta,
    resolve_val01_status,
    val01_volume_note,
    volume_confidence,
)
from matrix_kernel.trajectory import Trajectory

_GENERIC_POP_DENSITY = 5843.0  # persons/km², PSA 2020 CPH Iloilo City average
# Iloilo City Proper approximate centroid (for heritage distance decay).
_CITY_LAT, _CITY_LON = 10.7202, 122.5621


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def score(trajectory: Trajectory, datasets=None, baseline: dict | None = None, eco2_val: float = 0.0) -> list[DimensionResult]:
    base = baseline if baseline is not None else load_baseline().edge_counts
    rng = random.Random(11)
    results: list[DimensionResult] = []
    val01 = resolve_val01_status(trajectory.meta)
    vol_note = val01_volume_note(val01)

    delta_trips = network_delta(trajectory, base)

    # ── SOCI-2: Heritage proximity ──
    hist = osm_historic_points()
    if hist is None:
        val2 = float(delta_trips) * 0.01
        conf2 = volume_confidence(["OSM-ILO"], val01, pass_method="L")
        assumptions2 = [
            "OSM historic tags missing — heritage = Δtrips × 0.01 scalar stand-in",
            "confidence capped at L",
            vol_note,
            REROUTING_ASSUMPTION,
        ]
        ids2 = ["OSM-ILO"]
    else:
        pts, n_sites = hist
        # Mean distance-decay score: closer heritage → higher score; trip surge lowers it.
        decays = [math.exp(-_haversine_km(_CITY_LAT, _CITY_LON, lat, lon) / 2.0) for lat, lon in pts]
        mean_decay = sum(decays) / len(decays)
        stress = abs(delta_trips) / max(abs(sum(base.values()) if base else 0.0), 1.0)
        val2 = mean_decay * (1.0 - min(0.5, 0.1 * stress))
        conf2 = volume_confidence(["OSM-ILO"], val01, pass_method="M")
        assumptions2 = [
            f"OSM historic sites = {n_sites} (interim NHCP substitute; methods §3.5)",
            f"mean distance-decay from city centroid = {mean_decay:.4f}",
            f"network stress = {stress:.4f}",
            "equation: heritage = mean(exp(-d/2km)) × (1 − stress penalty)",
            vol_note,
            REROUTING_ASSUMPTION,
        ]
        ids2 = ["OSM-ILO"]

    lo2, hi2 = earned_confidence_interval(val2, lambda: val2 * rng.uniform(0.8, 1.2), n=500)
    results.append(DimensionResult(
        dimension="societal",
        metric="Heritage proximity",
        equation_id="SOCI-2",
        value=val2,
        range=(lo2, hi2),
        unit="score",
        confidence=conf2,
        input_dataset_ids=ids2,
        references=[],
        assumptions=assumptions2,
    ))

    # ── SOCI-3: Health-exposure proxy ──
    val3 = eco2_val * _GENERIC_POP_DENSITY
    lo3, hi3 = earned_confidence_interval(val3, lambda: val3 * rng.uniform(0.7, 1.3), n=500)
    results.append(DimensionResult(
        dimension="societal",
        metric="Health-exposure proxy",
        equation_id="SOCI-3",
        value=val3,
        range=(lo3, hi3),
        unit="index",
        confidence=provisional_capped_confidence(["EMB", "S5P-NO2", "WorldPop"]),
        input_dataset_ids=["EMB", "S5P-NO2", "WorldPop"],
        references=[],
        assumptions=[
            "uses ECO-2 passed value × population density",
            f"population density = {_GENERIC_POP_DENSITY:.0f} persons/km² (PSA 2020 CPH)",
            "confidence capped at L: §3.6 PROVISIONAL density (methods §2)",
            REROUTING_ASSUMPTION,
        ],
    ))

    # ── SOCI-4: Walkability Δ ──
    density = osm_walk_bike_tag_density()
    factors = tssp2019_walk_factors()
    if density is None:
        val4 = float(delta_trips) * -0.005
        conf4 = volume_confidence(["OSM-ILO", "TSSP-2019"], val01, pass_method="L")
        assumptions4 = [
            "OSM walk/bike tags missing — walkability = Δtrips × -0.005 scalar",
            "confidence capped at L",
            vol_note,
            REROUTING_ASSUMPTION,
        ]
    else:
        frac, n_ways = density
        w_side = float(factors.get("sidewalk_weight", 0.45))
        w_bike = float(factors.get("bike_infra_weight", 0.35))
        w_stress = float(factors.get("traffic_stress_penalty", 0.20))
        base_walk = frac * (w_side + w_bike)
        trip_stress = min(1.0, abs(delta_trips) / 500.0) * w_stress
        val4 = base_walk - trip_stress
        conf4 = volume_confidence(["OSM-ILO", "TSSP-2019"], val01, pass_method="M")
        assumptions4 = [
            f"OSM highway ways with walk/bike tags = {frac:.3%} of {n_ways}",
            f"TSSP factors: sidewalk={w_side}, bike={w_bike}, stress={w_stress} "
            f"({factors.get('source', 'TSSP-2019')})",
            f"walkability = tag_fraction×(sidewalk+bike) − trip_stress = {val4:.4f}",
            vol_note,
            REROUTING_ASSUMPTION,
        ]

    lo4, hi4 = earned_confidence_interval(val4, lambda: val4 * rng.uniform(0.6, 1.4), n=500)
    results.append(DimensionResult(
        dimension="societal",
        metric="Walkability Δ",
        equation_id="SOCI-4",
        value=val4,
        range=(lo4, hi4),
        unit="score",
        confidence=conf4,
        input_dataset_ids=["OSM-ILO", "TSSP-2019"],
        references=["TSSP-2019"],
        assumptions=assumptions4,
    ))

    # ── SOCI-1: Societal composite ──
    val1 = (val2 * 0.3) + (val3 * -0.001) + (val4 * 0.5)
    lo1, hi1 = earned_confidence_interval(val1, lambda: val1 * rng.uniform(0.8, 1.2), n=500)
    # Worst of component ceilings: SOCI-3 still L → composite L
    conf1 = volume_confidence(["OSM-ILO", "WorldPop", "TSSP-2019"], val01, pass_method="L")
    results.insert(0, DimensionResult(
        dimension="societal",
        metric="Societal composite",
        equation_id="SOCI-1",
        value=val1,
        range=(lo1, hi1),
        unit="0-100",
        confidence=conf1,
        input_dataset_ids=["OSM-ILO", "WorldPop", "TSSP-2019"],
        references=[],
        assumptions=[
            "composite of SOCI-2, SOCI-3, SOCI-4",
            "confidence capped at L while SOCI-3 remains PROVISIONAL",
        ],
    ))

    return results
