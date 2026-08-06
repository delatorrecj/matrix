import os
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

# Needs the eclipse-sumo wheel (runner -> sumo_env) at import; skip cleanly without it.
pytest.importorskip("sumo", reason="eclipse-sumo not installed; run `uv sync` in app/packages/kernel")

from matrix_kernel.runner import Scenario, simulate
from matrix_kernel.trajectory import Trajectory
from matrix_kernel.baseline import load_baseline

REDIS_URL = os.environ.get("MATRIX_REDIS_URL", "redis://localhost:6379/0")

def test_timing_probe():
    """End-to-end timing probe of a bare scenario run (S5)."""
    redis = pytest.importorskip("redis")
    try:
        r = redis.from_url(REDIS_URL)
        r.ping()
    except Exception as e:
        pytest.skip(f"Redis not reachable: {e}")

    # 1. Measure baseline load time (should be instant from Redis)
    t0 = time.perf_counter()
    base = load_baseline()
    t1 = time.perf_counter()
    baseline_load_ms = (t1 - t0) * 1000

    # 2. Measure scenario delta run time
    sc = Scenario("s1", "close a lane on Diversion Rd", corridor="diversion")
    
    t2 = time.perf_counter()
    traj = simulate(sc)
    t3 = time.perf_counter()
    warm_delta_ms = (t3 - t2) * 1000
    
    # Extract the simulated duration from the trajectory meta
    sim_end_s = traj.meta.get("sim_end_s", 0)
    
    print("\n--- S5 Timing Probe Results ---")
    print(f"Baseline cache load : {baseline_load_ms:.2f} ms")
    print(f"Warm delta scenario : {warm_delta_ms:.2f} ms")
    print(f"Simulation window   : {sim_end_s:.2f} s")
    print("-------------------------------")
    
    assert warm_delta_ms > 0
    assert traj.meta["edges_with_traffic"] > 0
    
    # QAD PERF-01: End-to-end simulation budget must be under 90s
    assert warm_delta_ms < 90000, f"PERF-01 Budget Exceeded: Delta run took {warm_delta_ms} ms (limit 90000)"


def test_concurrent_simulate_calls_do_not_collide():
    """The /simulate concurrency gate (matrix_api.runtime.SimGate) admits up to
    MATRIX_MAX_CONCURRENT_SIMS (default 2) simultaneous runs -- simulate() must give each
    its own traci label (not the implicit "default"), or the second call's Connection()
    raises TraCIException("Connection 'default' is already active."). Two real threads,
    two real SUMO subprocesses."""
    scenarios = [
        Scenario("concurrent-1", "close a lane on Diversion Rd", corridor="diversion"),
        Scenario("concurrent-2", "close a lane on JM Basa", corridor="basa"),
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        trajectories = list(pool.map(simulate, scenarios))
    for traj in trajectories:
        assert traj.meta["edges_with_traffic"] > 0


def test_location_of_interest_is_ground_truth_from_the_real_net():
    """CR-013 end-to-end: a keyword-matched location gets a real [lon, lat] derived
    from the actual matched edge (real net, real SUMO) -- not a pre-simulation guess."""
    traj = simulate(Scenario("s-loi", "close a lane on Iznart St", location="Iznart"))
    assert traj.meta["edge_resolution"] == "keyword-match"
    loi = traj.meta["location_of_interest"]
    assert loi is not None
    lon, lat = loi
    assert 122.4 < lon < 122.7   # within the Iloilo pilot bbox (MATRIX_Iloilo_Data_Sources.md)
    assert 10.6 < lat < 10.8


def test_location_of_interest_is_none_for_unresolvable_location():
    """An unresolvable location falls back to busiest-baseline -- honestly no marker."""
    traj = simulate(Scenario("s-loi-none", "close a lane somewhere unnamed", location="Nonexistent Road XYZ"))
    assert traj.meta["edge_resolution"].startswith("busiest-baseline-fallback")
    assert traj.meta["location_of_interest"] is None
