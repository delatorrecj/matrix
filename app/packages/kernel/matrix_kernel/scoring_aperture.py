"""Scoring aperture — site vs impacted network, VAL-01 volume confidence.

Modules must not each re-implement `sum(scenario − baseline for e in closed_edges)`.
This helper is SUMO-free so unit tests can import it on a bare venv.

Glass box: network deltas include scenario-only dynamic rerouting (the nightly
baseline has no rerouting device). Every volume-derived card must cite
`REROUTING_ASSUMPTION`.
"""
from __future__ import annotations

from typing import Sequence

from matrix_kernel.confidence import validation_capped_confidence
from matrix_kernel.results import Applicability, Confidence, Dimension, DimensionResult
from matrix_kernel.trajectory import Trajectory

FALLBACK_EDGE_LENGTH_KM = 0.150
REROUTING_ASSUMPTION = (
    "network deltas include scenario-only dynamic rerouting "
    "(baseline SUMO has no rerouting device; scenario uses "
    "--device.rerouting.probability 1)"
)


def resolve_val01_status(meta: dict) -> str:
    """Prefer an injected gate status (tests); else the published validation report."""
    injected = meta.get("val01_status")
    if injected:
        return str(injected).strip().upper()
    try:
        from matrix_kernel.validation import published_val01_status
        return published_val01_status()
    except Exception:
        return "NOT_RUN"


def val01_volume_note(status: str) -> str:
    if status == "PASS":
        return (
            "VAL-01 PASS against Calderon 2014 (NRMSE vs threshold in GET /validation) "
            "— corridor volume magnitudes are city-back-tested (demand not fitted to "
            "passenger_flow_max; CR-012 §4)"
        )
    if status == "FAIL":
        return (
            "confidence capped at L: VAL-01 published FAIL against Calderon 2014 "
            "(NRMSE vs threshold in GET /validation) — Iloilo corridor volumes are "
            "directional, not city-calibrated (uncalibrated demand)"
        )
    return (
        "confidence capped at L: VAL-01 not computed (NOT_RUN) — Iloilo corridor "
        "volumes are directional, not city-calibrated"
    )


def volume_confidence(
    input_dataset_ids: Sequence[str],
    gate_status: str | None,
    *,
    pass_method: Confidence = "M",
) -> Confidence:
    """VAL-01 is a worst factor for every metric that is a function of delta_trips."""
    return validation_capped_confidence(
        input_dataset_ids, gate_status, pass_method=pass_method
    )


def affected_edges(meta: dict) -> list[str]:
    """Intervention site. Prefer v2 `affected_edges`; fall back to legacy `closed_edges`."""
    raw = meta.get("affected_edges")
    if raw:
        return list(raw)
    return list(meta.get("closed_edges") or [])


def impacted_edges(trajectory: Trajectory, baseline: dict) -> list[str]:
    """Edges whose entered-count changed vs baseline (displacement the sim already computed).

    An explicit `meta["impacted_edges"]` wins so the runner can stamp the set once.
    """
    stamped = trajectory.meta.get("impacted_edges")
    if stamped:
        return list(stamped)
    sc = trajectory.edge_counts
    keys = set(sc) | set(baseline)
    return [e for e in keys if sc.get(e, 0) != baseline.get(e, 0)]


def site_delta(trajectory: Trajectory, baseline: dict) -> float:
    """Δ entered on the intervention site (edited / facility-adjacent edges)."""
    sc = trajectory.edge_counts
    return float(sum(sc.get(e, 0) - baseline.get(e, 0) for e in affected_edges(trajectory.meta)))


def network_delta(trajectory: Trajectory, baseline: dict) -> float:
    """Δ entered on impacted edges (site + detours)."""
    sc = trajectory.edge_counts
    return float(
        sum(sc.get(e, 0) - baseline.get(e, 0) for e in impacted_edges(trajectory, baseline))
    )


def edge_length_km(edge_id: str, lengths: dict | None) -> float:
    if lengths and edge_id in lengths:
        return float(lengths[edge_id])
    return FALLBACK_EDGE_LENGTH_KM


def vkt_delta_km(trajectory: Trajectory, baseline: dict) -> float:
    """Δ vehicle-km over impacted edges. Uses `meta["edge_lengths_km"]` when present."""
    lengths = trajectory.meta.get("edge_lengths_km") or {}
    sc = trajectory.edge_counts
    total = 0.0
    for e in impacted_edges(trajectory, baseline):
        total += (sc.get(e, 0) - baseline.get(e, 0)) * edge_length_km(e, lengths)
    return total


def intervention_type(trajectory: Trajectory) -> str:
    applied = trajectory.meta.get("applied") or {}
    return str(
        trajectory.meta.get("intervention_type")
        or applied.get("intervention_type")
        or "lane_closure"
    )


def applied_parameters(trajectory: Trajectory) -> dict:
    applied = trajectory.meta.get("applied") or {}
    params = applied.get("parameters")
    if isinstance(params, dict):
        return params
    return {}


def na_result(
    *,
    dimension: Dimension,
    metric: str,
    equation_id: str,
    unit: str,
    input_dataset_ids: list[str],
    applicability: Applicability,
    assumptions: list[str],
    confidence: Confidence = "M",
    references: list[str] | None = None,
) -> DimensionResult:
    """A glass-box N/A card: Inspect still resolves; the chip is not a measurement."""
    return DimensionResult(
        dimension=dimension,
        metric=metric,
        equation_id=equation_id,
        value=0.0,
        range=(0.0, 0.0),
        unit=unit,
        confidence=confidence,
        input_dataset_ids=input_dataset_ids,
        references=list(references or []),
        assumptions=list(assumptions),
        applicability=applicability,
    )
