"""Social impact module (U8).

Equations (docs/methods-matrix.md §3.3):
  SOC-1  Equity-weighted access  -- CCHAIN RWI × hospital isochrones
  SOC-2  Displacement risk count -- CCHAIN osm_poi amenity density × lanes closed
  SOC-3  Distributional split    -- CCHAIN RWI bottom-tercile emphasis (PRD-F17)
"""
from __future__ import annotations

import random
import statistics

from matrix_kernel.baseline import load_baseline
from matrix_kernel.confidence import (
    earned_confidence_interval,
    method_capped_confidence,
    provisional_capped_confidence,
)
from matrix_kernel.datasets import (
    brgy_rwi_and_hospital_access,
    inverse_rwi_equity_weight,
    latest_rwi_means,
    mean_market_convenience_pois,
)
from matrix_kernel.results import DimensionResult
from matrix_kernel.scoring_aperture import (
    REROUTING_ASSUMPTION,
    intervention_type,
    na_result,
    network_delta,
    resolve_val01_status,
    val01_volume_note,
    volume_confidence,
)
from matrix_kernel.trajectory import Trajectory

_VENDORS_PER_CLOSED_LANE = 12


def score(trajectory: Trajectory, datasets=None, baseline: dict | None = None) -> list[DimensionResult]:
    base = baseline if baseline is not None else load_baseline().edge_counts
    rng = random.Random(9)
    results: list[DimensionResult] = []
    val01 = resolve_val01_status(trajectory.meta)
    vol_note = val01_volume_note(val01)
    itype = intervention_type(trajectory)

    delta_trips = network_delta(trajectory, base)
    base_trips = float(sum(base.values())) if base else 0.0
    access_delta = float(delta_trips) / max(abs(base_trips), 1.0)

    # ── SOC-1: Equity-weighted access (isochrones × RWI) ──
    joined = brgy_rwi_and_hospital_access(minutes=15)
    if joined is None:
        rwi_w = inverse_rwi_equity_weight()
        if rwi_w is None:
            val1 = float(delta_trips) * 0.001
            conf1 = volume_confidence(["CCHAIN", "NHFR"], val01, pass_method="L")
            assumptions1 = [
                "CCHAIN RWI/isochrones missing — scalar stand-in",
                "confidence L",
                vol_note,
                REROUTING_ASSUMPTION,
            ]
        else:
            weight, year = rwi_w
            val1 = weight * access_delta
            conf1 = volume_confidence(["CCHAIN", "NHFR"], val01, pass_method="M")
            assumptions1 = [
                f"fallback city-mean inverse RWI = {weight:.4f} ({year}); isochrones unavailable",
                f"Δaccess = {access_delta:.4f}",
                vol_note,
                REROUTING_ASSUMPTION,
            ]
    else:
        rows, vintage = joined
        # A = Σ_b w_b · Δaccess_b ; w_b ∝ 1/rwi ; Δaccess_b ∝ hospital_pct × corridor share
        total_w = 0.0
        acc = 0.0
        for _code, rwi, pct in rows:
            w = 1.0 / (rwi + 0.05)
            d_b = (pct / 100.0) * access_delta
            acc += w * d_b
            total_w += w
        val1 = acc / total_w if total_w else 0.0
        conf1 = volume_confidence(["CCHAIN", "NHFR"], val01, pass_method="M")
        assumptions1 = [
            f"equity-weighted access over {len(rows)} barangays ({vintage})",
            "A = mean_w( (1/(rwi+ε)) · (hospital_15min_pct/100) · Δtrips/base )",
            f"network Δaccess share = {access_delta:.4f}",
            vol_note,
            REROUTING_ASSUMPTION,
        ]

    lo1, hi1 = earned_confidence_interval(val1, lambda: val1 * rng.uniform(0.5, 1.5), n=500)
    results.append(DimensionResult(
        dimension="social",
        metric="Equity-weighted access",
        equation_id="SOC-1",
        value=val1,
        range=(lo1, hi1),
        unit="index",
        confidence=conf1,
        input_dataset_ids=["CCHAIN", "NHFR"],
        references=[],
        assumptions=assumptions1,
    ))

    # ── SOC-2: Displacement risk count ──
    lanes_closed = int(trajectory.meta.get("lanes_closed", 0) or 0)
    if itype not in ("lane_closure", "full_closure"):
        results.append(na_result(
            dimension="social",
            metric="Displacement risk count",
            equation_id="SOC-2",
            unit="count",
            input_dataset_ids=["CCHAIN", "OSM-ILO"],
            applicability="not_applicable",
            confidence="M",
            assumptions=[
                f"not applicable: vendor displacement is a closure metric "
                f"(intervention_type={itype})"
            ],
        ))
    else:
        poi = mean_market_convenience_pois()
        if poi is None:
            val2 = float(lanes_closed * _VENDORS_PER_CLOSED_LANE)
            conf2 = provisional_capped_confidence(["CCHAIN", "OSM-ILO"])
            assumptions2 = [
                f"CCHAIN amenity missing — fallback vendors/lane = {_VENDORS_PER_CLOSED_LANE} PROVISIONAL",
            ]
        else:
            dens, year = poi
            val2 = float(lanes_closed) * dens
            conf2 = method_capped_confidence(["CCHAIN", "OSM-ILO"], "M")
            assumptions2 = [
                f"vendors/lane = city-mean(market+convenience) = {dens:.3f} (CCHAIN amenity {year})",
                f"lanes_closed = {lanes_closed}",
            ]

        lo2, hi2 = earned_confidence_interval(val2, lambda: val2 * rng.uniform(0.8, 1.2), n=500)
        results.append(DimensionResult(
            dimension="social",
            metric="Displacement risk count",
            equation_id="SOC-2",
            value=val2,
            range=(lo2, hi2),
            unit="count",
            confidence=conf2,
            input_dataset_ids=["CCHAIN", "OSM-ILO"],
            references=[],
            assumptions=assumptions2,
        ))

    # ── SOC-3: Distributional split ──
    rwi_means = latest_rwi_means()
    if rwi_means is None:
        val3 = val1 * 1.5
        conf3 = volume_confidence(["CCHAIN", "WorldPop"], val01, pass_method="L")
        assumptions3 = [
            "CCHAIN RWI missing — 1.5× access scalar",
            "confidence L",
            vol_note,
            REROUTING_ASSUMPTION,
        ]
    else:
        means, year = rwi_means
        cutoff = statistics.quantiles(means, n=3)[0] if len(means) >= 3 else statistics.median(means)
        low_share = sum(1 for r in means if r <= cutoff) / len(means)
        val3 = val1 * (1.0 + low_share)
        conf3 = volume_confidence(["CCHAIN", "WorldPop"], val01, pass_method="M")
        assumptions3 = [
            f"bottom-tercile RWI cutoff = {cutoff:.4f} (CCHAIN {year})",
            f"low-income barangay share = {low_share:.3f}",
            "low_income_impact = A · (1 + low_share)",
            vol_note,
            REROUTING_ASSUMPTION,
        ]

    lo3, hi3 = earned_confidence_interval(val3, lambda: val3 * rng.uniform(0.7, 1.3), n=500)
    results.append(DimensionResult(
        dimension="social",
        metric="Distributional split (Low-income impact)",
        equation_id="SOC-3",
        value=val3,
        range=(lo3, hi3),
        unit="per-decile",
        confidence=conf3,
        input_dataset_ids=["CCHAIN", "WorldPop"],
        references=[],
        assumptions=assumptions3,
    ))

    return results
