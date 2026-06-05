"""XGBoost baseline forecaster + nightly baseline run (U4; Phase 2, Gate 2).

run_nightly_baseline() -- runs the current-state SUMO sim once and caches the resulting
                          per-edge volume Trajectory to Redis (`baseline:iloilo:latest`) so
                          scenario runs are cheap deltas (the 90 s budget depends on this being
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
from matrix_kernel.trajectory import Trajectory

KERNEL_DATA = Path(__file__).resolve().parent.parent / "data"
NET = KERNEL_DATA / "iloilo.net.xml"
ROU = KERNEL_DATA / "iloilo.rou.xml"
REDIS_URL = os.environ.get("MATRIX_REDIS_URL", "redis://localhost:6379/0")
BASELINE_KEY = "baseline:iloilo:latest"
# Shared sim horizon (an AM-peak slice). Baseline + scenario MUST use the same window for a
# fair BEH-1 delta. ~15 min keeps the slice tractable; the full-day expansion is an assumption
# carried on BEH-1. Longer horizons raise fidelity at a (Phase-6) latency cost.
SIM_END = 900.0


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


def run_nightly_baseline(end: float = SIM_END, redis_url: str = REDIS_URL) -> dict:
    """Materialize `baseline:iloilo:latest` in Redis; return a summary incl. the cold-run time."""
    t0 = time.perf_counter()
    edge_counts = run_sumo_edge_counts(NET, ROU, end)
    cold_ms = (time.perf_counter() - t0) * 1000.0
    traj = Trajectory(
        edge_counts=edge_counts,
        frames=[],
        meta={
            "kind": "baseline",
            "sim_end_s": end,
            "net": "iloilo.net.xml",
            "demand": "iloilo.rou.xml",
            "edges_with_traffic": len(edge_counts),
            "total_entries": sum(edge_counts.values()),
            "cold_ms": round(cold_ms, 1),
        },
    )
    import redis

    redis.from_url(redis_url).set(BASELINE_KEY, traj.to_json())
    return {
        "key": BASELINE_KEY,
        "edges_with_traffic": len(edge_counts),
        "total_entries": sum(edge_counts.values()),
        "cold_ms": round(cold_ms, 1),
    }


def load_baseline(redis_url: str = REDIS_URL) -> Trajectory:
    """Load the cached baseline trajectory (the delta source for runner.simulate)."""
    import redis

    raw = redis.from_url(redis_url).get(BASELINE_KEY)
    if raw is None:
        raise KeyError(f"{BASELINE_KEY} not in Redis — run run_nightly_baseline() first")
    return Trajectory.from_json(raw)


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
