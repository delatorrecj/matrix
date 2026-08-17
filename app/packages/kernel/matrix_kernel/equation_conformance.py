"""Equation conformance ledger (Credibility Phase 1).

Maps every shipped equation_id to an honesty tag so we never silently present a
scalar stand-in or §3.6 PROVISIONAL proxy as High-confidence precision.

Tags (methods §2 / §3.6):
  equation_backed   — computes the documented form from trajectory/network data
  provisional_proxy — uses a named §3.6 PROVISIONAL constant
  honest_stub       — intentionally zero / N/A for the scenario class (e.g. lane closure)
  scalar_standin    — Δtrips × ad-hoc scalar; not the methods equation body

Scalar stand-ins and provisional proxies MUST emit confidence L (directional only).
"""
from __future__ import annotations

from typing import Literal

Conformance = Literal[
    "equation_backed",
    "provisional_proxy",
    "honest_stub",
    "scalar_standin",
]

# equation_id -> (conformance, required_confidence_ceiling)
# Ceiling "L" means emitted confidence must be L; "M"/"H" means must be ≤ that tier
# via the worst-factor rule (may still be L if data is weaker).
EQUATION_CONFORMANCE: dict[str, tuple[Conformance, str]] = {
    "BEH-1": ("equation_backed", "H"),
    "BEH-2": ("equation_backed", "M"),  # stub value 0; literature mode-share cap M
    "BEH-3": ("equation_backed", "H"),
    "BEH-4": ("provisional_proxy", "L"),
    "ECO-1": ("equation_backed", "H"),  # simplified VKT×EF; EF band-checked externally
    "ECO-2": ("provisional_proxy", "L"),
    "ECO-3": ("honest_stub", "H"),
    "ECO-4": ("equation_backed", "M"),  # CCHAIN NOAH×WorldPop when flood_hazard; else 0
    "SOC-1": ("equation_backed", "M"),  # CCHAIN inverse-RWI × Δaccess
    "SOC-2": ("equation_backed", "M"),  # CCHAIN amenity density × lanes
    "SOC-3": ("equation_backed", "M"),  # CCHAIN RWI bottom-tercile split
    "ECON-1": ("equation_backed", "M"),  # BIR median CR × uplift
    "ECON-2": ("equation_backed", "M"),  # Δtrips × 1.2 × places density
    "ECON-3": ("equation_backed", "M"),  # PSA ASPBI regional employment × share
    "SOCI-1": ("scalar_standin", "L"),  # composite still L while SOCI-3 provisional
    "SOCI-2": ("equation_backed", "M"),  # OSM historic distance decay
    "SOCI-3": ("provisional_proxy", "L"),
    "SOCI-4": ("equation_backed", "M"),  # TSSP factors × OSM walk/bike density
}

# §3.6 PROVISIONAL constant literals retained as *fallbacks* when CSV loaders miss.
# Primary ECON-1 / SOC-2 paths now read BIR / CCHAIN (Credibility Phase 3).
PROVISIONAL_CONSTANTS: dict[str, float | int] = {
    "_PM25_PER_CO2E_PROXY": 0.05,
    "_PHP_PER_TRIP_PROXY": 50.0,  # fallback only if BIR CSV missing
    "_VENDORS_PER_CLOSED_LANE": 12,  # fallback only if CCHAIN amenity missing
    "_GENERIC_POP_DENSITY": 5843.0,
}

_RANK = {"L": 1, "M": 2, "H": 3}


def requires_low_confidence(equation_id: str) -> bool:
    """True when the conformance tag forces directional-only (L)."""
    tag, ceiling = EQUATION_CONFORMANCE[equation_id]
    return tag in ("provisional_proxy", "scalar_standin") or ceiling == "L"


def confidence_within_ceiling(confidence: str, equation_id: str) -> bool:
    """Emitted confidence must not exceed the ledger ceiling."""
    _, ceiling = EQUATION_CONFORMANCE[equation_id]
    return _RANK[confidence] <= _RANK[ceiling]
