"""Minimal OpenAQ v3 client for Iloilo PM2.5 median (Credibility Phase 1).

Uses stdlib urllib so the kernel stays dependency-light. Callers catch exceptions
and treat failures as SKIPPED — never invent ambient values.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from statistics import median
from typing import Any


# Iloilo City approximate center (OpenAQ location search).
_ILOILO_LAT = 10.7202
_ILOILO_LON = 122.5621
_RADIUS_M = 50_000
_OPENAQ_LOCATIONS = "https://api.openaq.org/v3/locations"
_OPENAQ_SENSORS = "https://api.openaq.org/v3/sensors/{sensor_id}/hours"


def fetch_iloilo_pm25_median(*, api_key: str, timeout_s: float = 15.0) -> float | None:
    """Return median recent PM2.5 (µg/m³) near Iloilo, or None if unavailable."""
    if not api_key:
        return None
    locations = _get_json(
        _OPENAQ_LOCATIONS,
        {
            "coordinates": f"{_ILOILO_LAT},{_ILOILO_LON}",
            "radius": _RADIUS_M,
            "limit": 20,
            "parameters_id": 2,  # PM2.5 in OpenAQ v3
        },
        api_key=api_key,
        timeout_s=timeout_s,
    )
    results = locations.get("results") or []
    values: list[float] = []
    for loc in results:
        for sensor in loc.get("sensors") or []:
            param = (sensor.get("parameter") or {}).get("name") or sensor.get("parameter")
            if str(param).lower() not in ("pm25", "pm2.5"):
                # OpenAQ v3 may use parameter object with name pm25
                continue
            sid = sensor.get("id")
            if sid is None:
                continue
            try:
                hours = _get_json(
                    _OPENAQ_SENSORS.format(sensor_id=sid),
                    {"limit": 48},
                    api_key=api_key,
                    timeout_s=timeout_s,
                )
            except Exception:
                continue
            for row in hours.get("results") or []:
                val = row.get("value")
                if isinstance(val, (int, float)):
                    values.append(float(val))
    if not values:
        # Broader fallback: any numeric value under sensors without strict param filter
        for loc in results:
            for sensor in loc.get("sensors") or []:
                latest = sensor.get("latest") or {}
                val = latest.get("value")
                if isinstance(val, (int, float)):
                    values.append(float(val))
    return float(median(values)) if values else None


def _get_json(
    url: str,
    params: dict[str, Any],
    *,
    api_key: str,
    timeout_s: float,
) -> dict[str, Any]:
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{url}?{qs}",
        headers={
            "X-API-Key": api_key,
            "Accept": "application/json",
            "User-Agent": "MATRIX-credibility/0.1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"OpenAQ HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAQ network error: {exc.reason}") from exc
