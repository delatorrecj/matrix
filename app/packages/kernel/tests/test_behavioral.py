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
        meta={"closed_edges": ["C0", "C1"], "edge_lanes": {"C0": 2, "C1": 1}, "lanes_closed": 1},
    )
    results = score(scenario, baseline=baseline)

    assert {r.equation_id for r in results} == {"BEH-1", "BEH-2", "BEH-3"}
    for r in results:
        assert r.dimension == "behavioral"
        assert r.equation_id and r.input_dataset_ids          # glass-box invariants hold
        assert r.range[0] <= r.value <= r.range[1]            # value sits inside the earned range

    beh1 = next(r for r in results if r.equation_id == "BEH-1")
    assert beh1.value == -90.0          # (20-100) + (40-50)
    assert beh1.confidence == "H"       # OSM-ILO + OVERTURE + PERSONA-POOL all High
    assert beh1.range[0] < beh1.range[1]

    beh2 = next(r for r in results if r.equation_id == "BEH-2")
    assert beh2.confidence == "M"       # Calderon2014 caps mode-share at Medium

    beh3 = next(r for r in results if r.equation_id == "BEH-3")
    assert beh3.confidence == "H"
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
