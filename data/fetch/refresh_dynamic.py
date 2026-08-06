#!/usr/bin/env python3
"""Force-refresh open/dynamic data vintages (Credibility Phase 4).

Unlike the idempotent fetch_* scripts (skip-if-exists), this entrypoint deletes
selected targets then re-runs the fetchers so OSM / PSA / HDX CCHAIN can update.

  python data/fetch/refresh_dynamic.py
  python data/fetch/refresh_dynamic.py --force-osm --force-economic
  python data/fetch/refresh_dynamic.py --subset-cchain
  python data/fetch/refresh_dynamic.py --all

Does NOT rebuild SUMO net/demand (call build_network.py / build_demand.py --calibrate
separately after OSM refresh). Writes data/last_refresh.json.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FETCH_DIR = Path(__file__).resolve().parent
DATA = FETCH_DIR.parent
RAW = DATA / "raw"

# Targets safe to delete for a re-fetch (regenerable / open-licensed).
_OSM_TARGETS = [RAW / "osm" / "iloilo_osm.json"]
_ECONOMIC_GLOBS = [
    "economic/psa_openstat_*.csv",
    "economic/worldbank_*.json",
]
_CCHAIN_MARKER = RAW / "hdx"  # CKAN dump dir; subset regenerates processed/


def _unlink(paths: list[Path]) -> list[str]:
    removed = []
    for p in paths:
        if p.is_file():
            p.unlink()
            removed.append(str(p.relative_to(DATA)))
        elif p.is_dir():
            # Only clear files, keep directory.
            for child in p.rglob("*"):
                if child.is_file():
                    child.unlink()
                    removed.append(str(child.relative_to(DATA)))
    return removed


def _run(script: str, extra_env: dict[str, str] | None = None) -> int:
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    cmd = [sys.executable, str(FETCH_DIR / script)]
    print(f"\n== running {script} ==")
    return subprocess.call(cmd, cwd=str(DATA.parent), env=env)


def main() -> int:
    ap = argparse.ArgumentParser(description="Force-refresh MATRIX open data vintages")
    ap.add_argument("--force-osm", action="store_true", help="re-fetch OSM Overpass extract")
    ap.add_argument("--force-economic", action="store_true", help="re-fetch PSA OpenStat / World Bank")
    ap.add_argument("--force-cchain-raw", action="store_true", help="clear raw/hdx then re-fetch via fetch_open")
    ap.add_argument("--subset-cchain", action="store_true", help="re-run subset_iloilo.py after raw refresh")
    ap.add_argument("--all", action="store_true", help="OSM + economic + CCHAIN raw + subset")
    args = ap.parse_args()

    if args.all:
        args.force_osm = args.force_economic = args.force_cchain_raw = args.subset_cchain = True

    if not any([args.force_osm, args.force_economic, args.force_cchain_raw, args.subset_cchain]):
        ap.print_help()
        print("\nNo refresh flags given — pass --all or a specific --force-* flag.")
        return 2

    removed: list[str] = []
    osm_backups: list[tuple[Path, Path]] = []
    if args.force_osm:
        for p in _OSM_TARGETS:
            if p.is_file():
                bak = p.with_suffix(p.suffix + ".bak")
                p.replace(bak)
                osm_backups.append((p, bak))
                removed.append(str(p.relative_to(DATA)))
    if args.force_economic:
        for pattern in _ECONOMIC_GLOBS:
            removed.extend(_unlink(list((RAW).glob(pattern))))
    if args.force_cchain_raw and _CCHAIN_MARKER.exists():
        removed.extend(_unlink([_CCHAIN_MARKER]))

    rc = 0
    if args.force_osm or args.force_cchain_raw:
        # fetch_open always runs OSM + CCHAIN CKAN; skip-if-exists is defeated by deletes above.
        rc = _run("fetch_open.py") or rc
    # Restore OSM from .bak if the force re-fetch failed (avoid wiping the net rebuild input).
    for dest, bak in osm_backups:
        if (not dest.is_file() or dest.stat().st_size == 0) and bak.is_file():
            bak.replace(dest)
            print(f"[refresh] restored {dest.name} from backup after failed Overpass fetch")
        elif bak.is_file():
            bak.unlink()
    if args.force_economic:
        rc = _run("fetch_economic.py") or rc
    if args.subset_cchain:
        rc = _run("subset_iloilo.py") or rc

    log = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "removed": removed,
        "flags": {
            "force_osm": args.force_osm,
            "force_economic": args.force_economic,
            "force_cchain_raw": args.force_cchain_raw,
            "subset_cchain": args.subset_cchain,
        },
        "exit_code": rc,
        "next_steps": [
            "If OSM changed: rebuild net via packages/data/build_network.py",
            "Then: build_demand.py --calibrate && run_nightly_baseline()",
            "Then: python -m matrix_kernel.build_validation_report",
        ],
    }
    out = DATA / "last_refresh.json"
    out.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"\n[refresh] wrote {out} (removed {len(removed)} file(s), exit={rc})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
