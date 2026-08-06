"""Open third-party spot-checks for Credibility Phase 1 (Layer C).

WHO-EMEP / HBEFA-style emission-factor band for ECO-1 fleet average.
OpenAQ ambient PM2.5 scale check for ECO-2 magnitudes (order-of-magnitude only).

Checks never fabricate PASS: missing network/key → SKIPPED.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Kernel package root (external_checks.py -> matrix_kernel -> ...)
_PKG = Path(__file__).resolve().parent
_WHO_EMEP_TABLE = _PKG / "data" / "who_emep_ef_excerpt.json"
_OPENAQ_FIXTURE = _PKG / "data" / "openaq_iloilo_fixture.json"

# ECO-1 fleet-average EF in ecological.py (g CO2 / km). Band from WHO-EMEP excerpt.
_ECO1_EF_G_PER_KM = 120.0


def check_who_emep_ef_band(
    *,
    ef_g_per_km: float = _ECO1_EF_G_PER_KM,
    table_path: Path | None = None,
) -> dict[str, Any]:
    """PASS if ECO-1 EF sits inside the published fleet-mix band in the excerpt table."""
    path = table_path or _WHO_EMEP_TABLE
    if not path.is_file():
        return {
            "status": "SKIPPED",
            "reason": f"WHO-EMEP excerpt missing at {path}",
        }
    try:
        table = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "SKIPPED", "reason": f"unreadable WHO-EMEP table ({exc})"}

    lo = float(table["fleet_average_co2_g_per_km"]["band_lo"])
    hi = float(table["fleet_average_co2_g_per_km"]["band_hi"])
    ok = lo <= ef_g_per_km <= hi
    return {
        "status": "PASS" if ok else "FAIL",
        "ef_g_per_km": ef_g_per_km,
        "band_lo": lo,
        "band_hi": hi,
        "source": table.get("provenance"),
        "note": table.get("note"),
    }


def _load_openaq_ambient_pm25() -> tuple[float | None, str]:
    """Return (median_pm25, source_label). Prefer live fetch when key present; else fixture."""
    api_key = os.environ.get("OPENAQ_API_KEY", "").strip()
    if api_key:
        try:
            from matrix_kernel.openaq_client import fetch_iloilo_pm25_median

            median = fetch_iloilo_pm25_median(api_key=api_key)
            if median is not None:
                return median, "openaq_live"
        except Exception as exc:
            # Fall through to fixture — live failure is not a FAIL of the sim.
            live_err = str(exc)
        else:
            live_err = "live returned None"
    else:
        live_err = "OPENAQ_API_KEY unset"

    if _OPENAQ_FIXTURE.is_file():
        try:
            fx = json.loads(_OPENAQ_FIXTURE.read_text(encoding="utf-8"))
            return float(fx["median_pm25_ug_m3"]), f"fixture ({fx.get('provenance', 'local')})"
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            return None, f"fixture unreadable ({exc}); live: {live_err}"
    return None, f"no fixture; live: {live_err}"


def check_openaq_pm25_scale(
    *,
    eco2_abs_ug_m3: float | None = None,
    max_ratio: float = 10.0,
) -> dict[str, Any]:
    """Order-of-magnitude check: |ECO-2| should not dwarf ambient PM2.5 by > max_ratio.

    When eco2_abs_ug_m3 is None, only reports ambient availability (status SKIPPED for
    the scale comparison — ambient alone is not a sim PASS/FAIL).
    """
    ambient, source = _load_openaq_ambient_pm25()
    if ambient is None or ambient <= 0:
        return {
            "status": "SKIPPED",
            "reason": f"no ambient PM2.5 available ({source})",
        }
    if eco2_abs_ug_m3 is None:
        return {
            "status": "SKIPPED",
            "reason": "no ECO-2 magnitude supplied for scale comparison",
            "ambient_pm25_ug_m3": ambient,
            "ambient_source": source,
        }
    ratio = abs(eco2_abs_ug_m3) / ambient if ambient else float("inf")
    ok = ratio <= max_ratio
    return {
        "status": "PASS" if ok else "FAIL",
        "eco2_abs_ug_m3": eco2_abs_ug_m3,
        "ambient_pm25_ug_m3": ambient,
        "ambient_source": source,
        "ratio": round(ratio, 3),
        "max_ratio": max_ratio,
        "note": (
            "Order-of-magnitude only — not a dispersion validation. "
            "FAIL means ECO-2 magnitudes are implausibly large vs ambient."
        ),
    }
