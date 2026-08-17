#!/usr/bin/env python3
"""Fetch recent OpenAQ PM2.5 near Iloilo and write the kernel offline fixture.

Usage:
  set OPENAQ_API_KEY=...
  python data/fetch/fetch_openaq.py

Writes:
  app/packages/kernel/matrix_kernel/data/openaq_iloilo_fixture.json

Stdlib only. Missing key or network failure exits non-zero without inventing values.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Allow importing matrix_kernel when run from repo root / data/fetch.
KERNEL = ROOT / "app" / "packages" / "kernel"
sys.path.insert(0, str(KERNEL))

OUT = KERNEL / "matrix_kernel" / "data" / "openaq_iloilo_fixture.json"


def main() -> int:
    key = os.environ.get("OPENAQ_API_KEY", "").strip()
    if not key:
        print("OPENAQ_API_KEY unset — refusing to invent ambient PM2.5", file=sys.stderr)
        return 2
    from matrix_kernel.openaq_client import fetch_iloilo_pm25_median

    median = fetch_iloilo_pm25_median(api_key=key)
    if median is None:
        print("OpenAQ returned no PM2.5 values near Iloilo", file=sys.stderr)
        return 1
    payload = {
        "provenance": f"OpenAQ live fetch {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "location": "Iloilo City vicinity (50 km radius)",
        "median_pm25_ug_m3": median,
        "unit": "µg/m³",
        "note": "Order-of-magnitude ambient only — not a scenario dispersion ground truth.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[ok] wrote {OUT} median_pm25={median}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
