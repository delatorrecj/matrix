"""Tests for the Behavioral module (U8; methods §3.1 BEH-1/2/3, glass-box PRD-F14).

The synthetic test runs anywhere (no Redis/SUMO); the real-scenario integration loads the
cached scenario:demo:latest + baseline and skips if Redis isn't up.
"""
import os

import pytest

# Import chain (modules.behavioral -> baseline -> sumo_env) needs the eclipse-sumo wheel
# at import time. Skip cleanly on a bare venv instead of erroring at collection; `uv sync`
# in app/packages/kernel (or the Docker image) provides SUMO and runs the full suite.
pytest.importorskip("sumo", reason="eclipse-sumo not installed; run `uv sync` in app/packages/kernel")

from matrix_kernel.modules.behavioral import score
from matrix_kernel.trajectory import Trajectory

REDIS_URL = os.environ.get("MATRIX_REDIS_URL", "redis://localhost:6379/0")


def test_beh_results_are_glass_box():
    baseline = {"C0": 100, "C1": 50, "OTHER": 200}
    scenario = Trajectory(
        edge_counts={"C0": 20, "C1": 40, "OTHER": 210},
        frames=[],
        meta={
            "closed_edges": ["C0", "C1"],
            "edge_lanes": {"C0": 2, "C1": 1},
            "lanes_closed": 1,
            # Published live gate (CR-014). Injected so the test does not depend on
            # validation_report.json I/O — FAIL must keep BEH-1/BEH-3 at L.
            "val01_status": "FAIL",
        },
    )
    results = score(scenario, baseline=baseline)

    assert {r.equation_id for r in results} == {"BEH-1", "BEH-2", "BEH-3"}
    for r in results:
        assert r.dimension == "behavioral"
        assert r.equation_id and r.input_dataset_ids          # glass-box invariants hold
        assert r.range[0] <= r.value <= r.range[1]            # value sits inside the earned range

    beh1 = next(r for r in results if r.equation_id == "BEH-1")
    assert beh1.value == -90.0          # (20-100) + (40-50)
    # VAL-01 FAIL / uncalibrated demand caps corridor *magnitudes* at L (directional),
    # even though OSM/SUMO inputs are H (methods §2: validation is a worst factor).
    assert beh1.confidence == "L"
    assert beh1.directional is True
    assert any("VAL-01" in a and "FAIL" in a for a in beh1.assumptions)
    assert any("not city-calibrated" in a.lower() or "uncalibrated" in a.lower()
               for a in beh1.assumptions)
    assert beh1.range[0] < beh1.range[1]

    beh2 = next(r for r in results if r.equation_id == "BEH-2")
    assert beh2.confidence == "M"       # Calderon2014 caps mode-share at Medium

    beh3 = next(r for r in results if r.equation_id == "BEH-3")
    assert beh3.confidence == "L"
    assert beh3.directional is True
    assert beh3.value > 0


def test_beh_on_real_cached_scenario():
    """End-to-end on the real cached SUMO scenario (skips if Redis/scenario not present)."""
    redis = pytest.importorskip("redis")
    try:
        raw = redis.from_url(REDIS_URL).get("scenario:demo:latest")
    except Exception as e:
        pytest.skip(f"Redis not reachable: {e}")
    if raw is None:
        pytest.skip("scenario:demo:latest not cached yet")

    traj = Trajectory.from_json(raw)
    results = score(traj)  # loads the real baseline from Redis
    assert {r.equation_id for r in results} == {"BEH-1", "BEH-2", "BEH-3"}
    beh1 = next(r for r in results if r.equation_id == "BEH-1")
    assert beh1.value <= 0.0            # closing a corridor lane removes trips from it
    assert beh1.input_dataset_ids and beh1.confidence in ("H", "M", "L")


def test_beh4_emitted_only_when_demand_delta_on_trajectory():
    """Inspectable BEH-4: 3000 seats × 0.9 = 2700 trips, copied from the demand summary."""
    demand = {
        "facility_kind": "school",
        "capacity": 3000,
        "facility_lonlat": [122.5446, 10.6969],
        "demand_trips_total": 2700,
        "equation_id": "BEH-4",
        "input_dataset_ids": ["Calderon2014"],
        "confidence": "L",
        "unit": "trips/window",
        "references": ["Calderon2014"],
        "assumptions": [
            "equation BEH-4: facility gravity redistribution (methods-matrix §3.1)",
        ],
    }
    traj = Trajectory(
        edge_counts={},
        frames=[],
        meta={
            "closed_edges": [],
            "edge_lanes": {},
            "lanes_closed": 0,
            "demand_delta": demand,
        },
    )
    results = score(traj, baseline={})
    ids = {r.equation_id for r in results}
    assert ids == {"BEH-1", "BEH-2", "BEH-3", "BEH-4"}
    beh4 = next(r for r in results if r.equation_id == "BEH-4")
    assert beh4.value == 2700.0
    assert beh4.confidence == "L"
    assert beh4.directional is True
    assert beh4.input_dataset_ids == ["Calderon2014"]
    assert beh4.unit == "trips/window"
    assert beh4.range[0] <= beh4.value <= beh4.range[1]


def test_beh1_beh3_lift_only_when_val01_pass():
    """Corridor-volume chips follow the VAL-01 factor — they must not stay hardcoded L.

    Injecting PASS is the legitimate unlock (independent demand already back-tested).
    This test fails if BEH-1/BEH-3 ignore gate status and stamp L forever.
    """
    baseline = {"C0": 100, "C1": 50}
    traj = Trajectory(
        edge_counts={"C0": 20, "C1": 40},
        frames=[],
        meta={
            "closed_edges": ["C0", "C1"],
            "edge_lanes": {"C0": 2, "C1": 1},
            "lanes_closed": 1,
            "val01_status": "PASS",
        },
    )
    results = score(traj, baseline=baseline)
    beh1 = next(r for r in results if r.equation_id == "BEH-1")
    beh3 = next(r for r in results if r.equation_id == "BEH-3")
    assert beh1.confidence == "H"
    assert beh1.directional is False
    assert beh3.confidence == "H"
    assert any("VAL-01" in a and "PASS" in a for a in beh1.assumptions)
    assert not any("capped at L" in a for a in beh1.assumptions)
