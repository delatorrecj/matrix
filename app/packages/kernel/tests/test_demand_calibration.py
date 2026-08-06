"""Tests for Tier-B demand calibration (CR-012 T1.3) — no SUMO required."""
from __future__ import annotations

import json
from pathlib import Path

from matrix_kernel.demand_calibration import (
    independent_am_peak_vehicles,
    period_for_target,
    recommend_calibration,
    write_calibration_artifact,
)


def test_independent_vehicles_scales_with_population_and_scale():
    # Stay under _MAX_VEHICLES_PER_HOUR so the population/scale relationship is visible.
    a = independent_am_peak_vehicles(10_000, end_s=3600, scale=1.0)
    b = independent_am_peak_vehicles(20_000, end_s=3600, scale=1.0)
    c = independent_am_peak_vehicles(10_000, end_s=3600, scale=2.0)
    assert b > a
    assert abs(c - 2 * a) < 1e-6
    # Cap engages at large populations.
    capped = independent_am_peak_vehicles(10_000_000, end_s=3600, scale=1.0)
    assert capped == 8_000.0


def test_period_clamped():
    assert period_for_target(3600, 1e9) == 0.5  # min period
    assert period_for_target(3600, 1) == 30.0  # max period
    assert abs(period_for_target(3600, 1800) - 2.0) < 1e-9


def test_recommend_uses_worldpop_when_present():
    cal = recommend_calibration(end_s=3600, env={"MATRIX_DEMAND_SCALE": "1.0"})
    # Repo ships CCHAIN worldpop — expect real calibration, not missing fallback.
    assert cal.source == "cchain_worldpop_tier_b"
    assert cal.population > 100_000
    assert 0.5 <= cal.period_s <= 30.0
    assert any("NOT fitted to Calderon" in a for a in cal.assumptions)


def test_write_calibration_artifact(tmp_path: Path):
    cal = recommend_calibration(end_s=3600)
    path = write_calibration_artifact(cal, tmp_path / "demand_calibration.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["source"] == cal.source
    assert "assumptions" in data
