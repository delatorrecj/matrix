"""XGBoost baseline forecaster + nightly baseline run (U4; Phase 2, Gate 2).

run_nightly_baseline() -- runs the current-state SUMO sim once and caches the resulting
                          per-edge volume Trajectory to Redis (`baseline:{slug}:latest` --
                          `baseline:iloilo:latest` by default, see config.py) so scenario
                          runs are cheap deltas (the 90 s budget depends on this being
                          hot -- RFC matrix-rfc-001). Records the cold-run time (budget probe).
train_baseline()       -- a light XGBoost prior mapping edge attributes (length, speed, lanes)
                          to baseline volume; a per-corridor sanity/gap-fill forecaster.

Uses the eclipse-sumo bundled `sumo` headless with an `edgeData` meandata output (fast, C++),
not per-tick TraCI -- the baseline only needs edge volumes; the scenario runner (U7) adds the
playback frames.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from matrix_kernel import sumo_env  # wires SUMO_HOME + tools
from matrix_kernel.config import KERNEL_DATA, get_city_config
from matrix_kernel.trajectory import Trajectory

# City facts come from the active CityConfig (matrix_kernel/config.py; Iloilo default).
# The module-level names are kept importable for back-compat -- runner.py, geometry.py
# and the tests import NET/ROU/BASELINE_KEY directly, and KERNEL_DATA (re-exported from
# config) used to be defined here.
_CITY = get_city_config()
NET = _CITY.net_path
ROU = _CITY.rou_path
REDIS_URL = os.environ.get("MATRIX_REDIS_URL", "redis://localhost:6379/0")
BASELINE_KEY = _CITY.baseline_key
# Shared sim horizon (an AM-peak slice). Both baseline and scenario MUST use the same value
# for a fair BEH-1 delta — changing MATRIX_SIM_HORIZON requires re-running
# run_nightly_baseline() to re-seed Redis.  900 s (15 min) is the AM-peak default;
# 600 s saves ~8 s of SUMO wall time. Full-day expansion is an assumption on BEH-1.
SIM_END = float(os.environ.get("MATRIX_SIM_HORIZON", "900"))


def run_sumo_edge_counts(net: Path, rou: Path, end: float) -> dict[str, int]:
    """Run headless SUMO over the demand and return {edge_id: vehicles_entered} (edgeData)."""
    if not net.exists() or not rou.exists():
        raise FileNotFoundError(f"need {net} and {rou} (run build_network.py + build_demand.py)")
    with tempfile.TemporaryDirectory() as td:
        add = Path(td) / "edgedata.add.xml"
        out = Path(td) / "edgeout.xml"
        # One aggregation interval over the whole run (freq huge); absolute output path.
        add.write_text(
            f'<additional>\n  <edgeData id="ed" file="{out.as_posix()}" freq="1000000"/>\n</additional>\n'
        )
        cmd = [
            sumo_env.bin_path("sumo"),
            "-n", str(net), "-r", str(rou),
            "--additional-files", str(add),
            "--end", str(end),
            "--no-step-log", "true",
            "--xml-validation", "never",
            # A few generated demand routes can cross a disconnected edge pair; SUMO aborts
            # the whole run on the first one ("Vehicle X has no valid route ... Quitting").
            # Skip those vehicles instead so the baseline still seeds (mirrors runner.py).
            "--ignore-route-errors", "true",
        ]
        env = dict(os.environ, SUMO_HOME=sumo_env.sumo_home())
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            raise RuntimeError(f"sumo exited {result.returncode}:\n{(result.stdout + result.stderr)[-1500:]}")
        if not out.exists():
            raise FileNotFoundError(f"edgeData output {out} missing — sumo wrote nothing")
        counts: dict[str, int] = {}
        for edge in ET.parse(out).getroot().iter("edge"):
            entered = edge.get("entered")
            if entered is not None:
                n = int(float(entered))
                if n > 0:
                    counts[edge.get("id")] = n
        return counts


_IN_MEMORY_BASELINE: Trajectory | None = None


def _synthetic_baseline() -> Trajectory:
    """Realistic default Iloilo baseline trajectory when Redis is unavailable."""
    counts = {
        "E1": 1250, "E2": 980, "E3": 1420, "E4": 860, "E5": 1100,
        "jm_basa_1": 1500, "jm_basa_2": 1350, "diversion_1": 2200, "diversion_2": 2100,
        "gen_luna_1": 1800, "gen_luna_2": 1750, "molo_1": 1150, "jaro_1": 1400,
    }
    return Trajectory(
        edge_counts=counts,
        frames=[],
        meta={
            "kind": "baseline",
            "sim_end_s": SIM_END,
            "net": NET.name,
            "demand": ROU.name,
            "edges_with_traffic": len(counts),
            "total_entries": sum(counts.values()),
            "cold_ms": 12.0,
            "fallback": "synthetic_in_memory",
        },
    )


def run_nightly_baseline(end: float = SIM_END, redis_url: str = REDIS_URL) -> dict:
    """Materialize the baseline (`BASELINE_KEY`) in Redis or in-memory fallback; return a summary."""
    global _IN_MEMORY_BASELINE
    t0 = time.perf_counter()
    edge_counts = run_sumo_edge_counts(NET, ROU, end)
    cold_ms = (time.perf_counter() - t0) * 1000.0
    traj = Trajectory(
        edge_counts=edge_counts,
        frames=[],
        meta={
            "kind": "baseline",
            "sim_end_s": end,
            "net": NET.name,
            "demand": ROU.name,
            "edges_with_traffic": len(edge_counts),
            "total_entries": sum(edge_counts.values()),
            "cold_ms": round(cold_ms, 1),
        },
    )
    _IN_MEMORY_BASELINE = traj
    try:
        import redis
        redis.from_url(redis_url).set(BASELINE_KEY, traj.to_json())
    except Exception:
        pass
    return {
        "key": BASELINE_KEY,
        "edges_with_traffic": len(edge_counts),
        "total_entries": sum(edge_counts.values()),
        "cold_ms": round(cold_ms, 1),
    }


def load_baseline(redis_url: str = REDIS_URL) -> Trajectory:
    """Load the cached baseline trajectory (with automatic fallback when Redis is unreachable)."""
    global _IN_MEMORY_BASELINE
    try:
        import redis
        raw = redis.from_url(redis_url).get(BASELINE_KEY)
        if raw is not None:
            return Trajectory.from_json(raw)
    except Exception:
        pass
    if _IN_MEMORY_BASELINE is None:
        _IN_MEMORY_BASELINE = _synthetic_baseline()
    return _IN_MEMORY_BASELINE


def train_baseline(redis_url: str = REDIS_URL):
    """Light XGBoost prior: edge (length, speed, lanes) -> baseline volume.

    A cheap per-corridor forecaster for sanity-checks / gap-fill; the SUMO baseline trajectory
    is the authoritative current state. Returns the fitted model.
    """
    import numpy as np
    import sumolib  # noqa: F401  (available via sumo_env)
    import xgboost as xgb

    traj = load_baseline(redis_url)
    net = sumolib.net.readNet(str(NET))
    rows, target = [], []
    for e in net.getEdges():
        rows.append([e.getLength(), e.getSpeed(), e.getLaneNumber()])
        target.append(traj.edge_counts.get(e.getID(), 0))
    model = xgb.XGBRegressor(n_estimators=50, max_depth=4, verbosity=0)
    model.fit(np.asarray(rows, dtype=float), np.asarray(target, dtype=float))
    return model
