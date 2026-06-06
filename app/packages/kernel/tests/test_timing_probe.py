import os
import time
import pytest

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
