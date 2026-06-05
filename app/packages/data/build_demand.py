#!/usr/bin/env python3
"""Phase 2.1 / U3 — Baseline vehicle demand for the Iloilo SUMO network.

Generates `iloilo.rou.xml`: routed passenger-vehicle trips across the network. This is the
baseline demand the nightly run (U4) simulates and the scenario delta (U7) perturbs. For
Milestone A the demand is a *reproducible* random trip set, fringe-weighted so arterials
(e.g. Diversion Rd) carry through-traffic. POI/TAZ/LPTRP + Calderon-2014 calibration is a
fidelity upgrade (Milestone B) — so Behavioral *behavior* confidence stays Medium (methods §3.1).

  input_dataset_ids: ["OSM-ILO", "SUMO-NET"]   confidence: M (uncalibrated random demand)

Uses the eclipse-sumo bundled randomTrips.py + duarouter + sumo (via matrix_kernel.sumo_env),
so it must run with the kernel venv python:
  uv run --directory app/packages/kernel python -X utf8 -u packages/data/build_demand.py
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
KERNEL_DATA = APP / "packages" / "kernel" / "data"

sys.path.insert(0, str(APP / "packages" / "kernel"))
from matrix_kernel import sumo_env  # noqa: E402  (wires SUMO_HOME + tools onto sys.path)

DEMAND_PROVENANCE = {
    "input_dataset_ids": ["OSM-ILO", "SUMO-NET"],
    "confidence": "M",
    "generator": "build_demand.py randomTrips (Phase 2.1 / U3)",
}


def _sumo_env() -> dict[str, str]:
    return dict(os.environ, SUMO_HOME=sumo_env.sumo_home())


def build_demand(net: Path, rou: Path, end: float, period: float, seed: int, fringe: float) -> Path:
    """Generate validated (duarouter-routed) trips with randomTrips.py."""
    if not net.exists():
        raise FileNotFoundError(f"network not found: {net} (run build_network.py first)")
    randomtrips = os.path.join(sumo_env.sumo_home(), "tools", "randomTrips.py")
    trips = rou.with_name("iloilo.trips.xml")
    cmd = [
        sys.executable, randomtrips,
        "-n", str(net),
        "-o", str(trips),            # intermediate trip file
        "-r", str(rou),              # routed output (randomTrips invokes duarouter)
        "-e", str(end),
        "-p", str(period),           # one departure every `period` s -> ~end/period vehicles
        "--fringe-factor", str(fringe),
        "--seed", str(seed),
        "--validate",                # duarouter validates routes; drops unroutable
        "--prefix", "veh",
    ]
    print(f"[demand] randomTrips -> {rou.name}  (end={end}s period={period}s seed={seed} fringe={fringe})")
    result = subprocess.run(cmd, capture_output=True, text=True, env=_sumo_env())
    for line in (result.stdout + result.stderr).strip().splitlines()[-12:]:
        print(f"  [rt] {line}")
    if result.returncode != 0:
        raise RuntimeError(f"randomTrips exited {result.returncode} — see output above")
    if not rou.exists():
        raise FileNotFoundError(f"randomTrips returned 0 but {rou} missing")
    if trips.exists():
        trips.unlink()  # intermediate, regenerable
    print(f"[demand] OK wrote {rou.name} ({rou.stat().st_size:,} bytes)")
    return rou


def smoke_sim(net: Path, rou: Path, end: float = 1200.0) -> bool:
    """Run headless sumo over the demand to confirm vehicles insert + route end-to-end."""
    cmd = [
        sumo_env.bin_path("sumo"),
        "-n", str(net), "-r", str(rou),
        "--end", str(end),
        "--no-step-log", "true",
        "--duration-log.statistics", "true",
        "--xml-validation", "never",
    ]
    print(f"[smoke] sumo headless over {rou.name} (--end {end}s) …")
    result = subprocess.run(cmd, capture_output=True, text=True, env=_sumo_env())
    out = result.stdout + result.stderr
    for line in out.splitlines():
        if any(k in line for k in ("Inserted:", "Running:", "Waiting:", "Statistics", "DijkstraRouter", "Loaded:")):
            print(f"  [sumo] {line.strip()}")
    if result.returncode != 0:
        print(f"[smoke] FAIL: sumo exited {result.returncode}")
        print(out[-1500:])
        return False
    print("[smoke] OK sumo ran the demand to completion")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Build MATRIX baseline vehicle demand (Phase 2.1 / U3)")
    ap.add_argument("--end", type=float, default=3600.0, help="departure horizon in sim seconds")
    ap.add_argument("--period", type=float, default=2.0, help="seconds between departures (~end/period vehicles)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed (reproducibility, methods §7)")
    ap.add_argument("--fringe-factor", type=float, default=5.0, help="bias trips to start/end at the network fringe")
    ap.add_argument("--no-smoke", action="store_true", help="skip the headless sumo smoke run")
    args = ap.parse_args()

    net = KERNEL_DATA / "iloilo.net.xml"
    rou = KERNEL_DATA / "iloilo.rou.xml"
    try:
        build_demand(net, rou, args.end, args.period, args.seed, args.fringe_factor)
        ok = True if args.no_smoke else smoke_sim(net, rou)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"\n[build_demand] ERROR: {e}", file=sys.stderr)
        return 1
    if ok:
        print(f"\n[build_demand] Demand ready: {rou}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
