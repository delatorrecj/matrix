"""Tier-B demand volume calibration (CR-012 T1.3) — independent of Calderon targets.

Uses CCHAIN WorldPop (city population) + documented planning trip rates to recommend
a randomTrips `--period`. Does **not** fit to VAL-01 Calderon passenger_flow_max
(circularity guard, CR-012 §4).

Override: MATRIX_DEMAND_SCALE multiplies the WorldPop-derived vehicle target
(1.0 = use the independent estimate as-is).
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from matrix_kernel.datasets import latest_worldpop_total

# Planning-norm trip rates (tier M — PH secondary-city order of magnitude; not an
# Iloilo household travel survey). Sources: JICA MUCEP/MMUTIS planning ranges
# condensed to a single AM-peak motorized rate for the pilot network window.
_TRIPS_PER_CAPITA_DAY = 1.2
_MOTORIZED_SHARE = 0.70
_AM_PEAK_SHARE_OF_DAILY = 0.10
# Cap so the synthetic network is not flooded beyond a reproducible envelope.
_MAX_VEHICLES_PER_HOUR = 8_000.0
_MIN_PERIOD_S = 0.5
_MAX_PERIOD_S = 30.0
_DEFAULT_END_S = 3600.0
_DEFAULT_PERIOD_S = 2.0  # historical Milestone-A default


@dataclass(frozen=True)
class DemandCalibration:
    population: float
    population_vintage: str
    target_vehicles: float
    period_s: float
    end_s: float
    scale: float
    source: str
    assumptions: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _env_scale(env: dict[str, str] | None = None) -> float:
    raw = (env or os.environ).get("MATRIX_DEMAND_SCALE", "1.0")
    try:
        scale = float(raw)
    except (TypeError, ValueError) as e:
        raise ValueError(f"MATRIX_DEMAND_SCALE must be a float, got {raw!r}") from e
    if scale <= 0:
        raise ValueError(f"MATRIX_DEMAND_SCALE must be > 0, got {scale}")
    return scale


def independent_am_peak_vehicles(
    population: float,
    *,
    end_s: float = _DEFAULT_END_S,
    scale: float = 1.0,
) -> float:
    """WorldPop-derived AM-peak vehicle departures for a sim window of `end_s` seconds.

    Independent of Calderon corridor maxima — may still leave VAL-01 FAIL/PASS as a
    true validation result after rebuild.
    """
    hourly = (
        population
        * _TRIPS_PER_CAPITA_DAY
        * _MOTORIZED_SHARE
        * _AM_PEAK_SHARE_OF_DAILY
    )
    hourly = min(hourly, _MAX_VEHICLES_PER_HOUR)
    window_frac = max(end_s, 1.0) / 3600.0
    return max(1.0, hourly * window_frac * scale)


def period_for_target(end_s: float, target_vehicles: float) -> float:
    """randomTrips period (seconds between departures) for ~target vehicles over end_s."""
    if target_vehicles <= 0:
        return _DEFAULT_PERIOD_S
    period = end_s / target_vehicles
    return float(min(_MAX_PERIOD_S, max(_MIN_PERIOD_S, period)))


def recommend_calibration(
    *,
    end_s: float = _DEFAULT_END_S,
    env: dict[str, str] | None = None,
) -> DemandCalibration:
    """Build a DemandCalibration from WorldPop (+ optional MATRIX_DEMAND_SCALE)."""
    scale = _env_scale(env)
    loaded = latest_worldpop_total()
    if loaded is None:
        # No CCHAIN on disk — keep Milestone-A period; document the gap.
        return DemandCalibration(
            population=0.0,
            population_vintage="missing",
            target_vehicles=end_s / _DEFAULT_PERIOD_S,
            period_s=_DEFAULT_PERIOD_S,
            end_s=end_s,
            scale=scale,
            source="fallback_default_period",
            assumptions=[
                "CCHAIN worldpop_population.csv missing — using Milestone-A period=2.0s",
                "NOT calibrated to Calderon VAL-01 targets (CR-012 circularity guard)",
            ],
        )
    pop, year = loaded
    target = independent_am_peak_vehicles(pop, end_s=end_s, scale=scale)
    period = period_for_target(end_s, target)
    return DemandCalibration(
        population=pop,
        population_vintage=year,
        target_vehicles=target,
        period_s=period,
        end_s=end_s,
        scale=scale,
        source="cchain_worldpop_tier_b",
        assumptions=[
            f"population = {pop:.0f} (CCHAIN WorldPop {year}, Iloilo barangay sum)",
            f"trips/capita/day = {_TRIPS_PER_CAPITA_DAY} (PH secondary-city planning norm, tier M)",
            f"motorized share = {_MOTORIZED_SHARE}",
            f"AM-peak share of daily = {_AM_PEAK_SHARE_OF_DAILY}",
            f"MATRIX_DEMAND_SCALE = {scale}",
            f"target vehicles capped at {_MAX_VEHICLES_PER_HOUR:.0f}/h then scaled to window",
            "Independent Tier-B anchor — NOT fitted to Calderon passenger_flow_max (CR-012 §4)",
        ],
    )


def write_calibration_artifact(cal: DemandCalibration, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cal.to_dict(), indent=2), encoding="utf-8")
    return path
