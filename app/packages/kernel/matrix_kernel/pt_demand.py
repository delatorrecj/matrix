"""Independent OSM / LPTRP public-transport headways → vehicles/hour.

Used as a *candidate* VAL-01 simulated-side source that is not fitted to Calderon
``passenger_flow_max`` (CR-012 §4 / CR-016). Missing ``interval`` / headway → 0.
We do not invent jeepney frequencies, copy Calderon f=22 / f=60, or treat
citywide fleet counts as corridor veh/h.

Live Iloilo Overpass (2026-08-20): 49 bus/jeepney relations, 4 with ``interval``,
all intercity. Published LPTRP pages (MC 2023-036, ilonggoengineer street tables)
name Lopez Jaena / Diversion but do not publish headways — urban corridor
veh/h stays 0 until a page states an interval.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass


def interval_to_veh_per_hour(interval_tag: str) -> float | None:
    """Parse OSM ``interval`` (HH:MM, minutes, or seconds) to vehicles/hour.

    Returns None when the tag is missing or unparseable — callers must skip,
    not guess a headway.
    """
    raw = (interval_tag or "").strip()
    if not raw:
        return None
    seconds: float | None = None
    if ":" in raw:
        parts = raw.split(":")
        try:
            nums = [float(p) for p in parts]
        except ValueError:
            return None
        if len(nums) == 2:
            seconds = nums[0] * 3600.0 + nums[1] * 60.0
        elif len(nums) == 3:
            seconds = nums[0] * 3600.0 + nums[1] * 60.0 + nums[2]
        else:
            return None
    else:
        try:
            value = float(raw)
        except ValueError:
            return None
        # OSM uses seconds when the number is large; minutes when small.
        seconds = value if value >= 60.0 else value * 60.0
    if seconds <= 0.0:
        return None
    return 3600.0 / seconds


def _haystack(tags: Mapping[str, str]) -> str:
    bits = [
        tags.get("name", ""),
        tags.get("ref", ""),
        tags.get("from", ""),
        tags.get("to", ""),
        tags.get("via", ""),
        tags.get("description", ""),
    ]
    return " ".join(bits).casefold()


def corridor_transit_veh_h(
    elements: Iterable[Mapping],
    needles: Sequence[str],
) -> float:
    """Sum veh/h for route relations matching ``needles`` that carry ``interval``.

    Does not accept Calderon passenger-flow targets. Untagged matches stay 0.
    """
    if not needles:
        return 0.0
    lowered = [n.casefold() for n in needles if n]
    total = 0.0
    for el in elements:
        tags = el.get("tags") or {}
        if not isinstance(tags, Mapping):
            continue
        blob = _haystack(tags)
        if not any(n in blob for n in lowered):
            continue
        veh_h = interval_to_veh_per_hour(str(tags.get("interval") or ""))
        if veh_h is None:
            continue
        total += veh_h
    return total


_STREET = re.compile(
    r"\b((?:[A-Z][A-Za-z0-9.'\-]+\s+)+"
    r"(?:Street|Road|Avenue|Blvd|Boulevard|Drive|Highway|Bridge))\b"
)
_HEADWAY = re.compile(
    r"\b(?:headway|interval)\b\s*[:=]?\s*(\d+(?:\.\d+)?)\s*"
    r"(minutes?|mins?|hours?|hrs?|h|seconds?|sec)?"
    r"|\bevery\s+(\d+(?:\.\d+)?)\s*(minutes?|mins?|hours?|hrs?|h)\b",
    re.I,
)


@dataclass(frozen=True)
class LptrpRoute:
    title: str
    streets: tuple[str, ...]
    interval: str | None
    url: str = ""


def _headway_to_interval_tag(value: float, unit: str | None) -> str:
    u = (unit or "minutes").lower()
    if u.startswith("hour") or u in {"h", "hr", "hrs"}:
        hours = int(value)
        mins = int(round((value - hours) * 60))
        return f"{hours:02d}:{mins:02d}"
    if u.startswith("sec"):
        return str(int(round(value)))
    if value == int(value):
        return str(int(value))
    return str(value)


def parse_lptrp_page(text: str, *, title: str = "", url: str = "") -> LptrpRoute:
    """Extract street names and an explicit headway, if the page states one.

    Fleet counts, dates, and route numbers are not headways.
    """
    blob = f"{title}\n{text}"
    streets: list[str] = []
    seen: set[str] = set()
    for match in _STREET.finditer(blob):
        name = re.sub(r"\s+", " ", match.group(1)).strip()
        key = name.casefold()
        if key not in seen:
            seen.add(key)
            streets.append(name)
    interval = None
    m = _HEADWAY.search(blob)
    if m:
        if m.group(1) is not None:
            interval = _headway_to_interval_tag(float(m.group(1)), m.group(2))
        else:
            interval = _headway_to_interval_tag(float(m.group(3)), m.group(4))
    return LptrpRoute(title=title, streets=tuple(streets), interval=interval, url=url)


def lptrp_corridor_veh_h(routes: Iterable[LptrpRoute], needles: Sequence[str]) -> float:
    """Sum veh/h for LPTRP routes whose title/streets match ``needles``.

    Untagged matches stay 0. Does not accept Calderon passenger-flow targets.
    """
    if not needles:
        return 0.0
    lowered = [n.casefold() for n in needles if n]
    total = 0.0
    for route in routes:
        blob = " ".join((route.title, *route.streets)).casefold()
        if not any(n in blob for n in lowered):
            continue
        veh_h = interval_to_veh_per_hour(route.interval or "")
        if veh_h is None:
            continue
        total += veh_h
    return total


# Aligned with build_validation_report.CALDERON_CORRIDOR_STREETS (street names only).
VAL01_CORRIDOR_NEEDLES: dict[str, tuple[str, ...]] = {
    "lopez_jaena": ("Lopez Jaena",),
    "diversion": ("Diversion", "Aquino"),
}


def lptrp_val01_veh_h(routes: Iterable[LptrpRoute]) -> dict[str, float]:
    """Independent transit veh/h on the two VAL-01 corridors, or 0 if untagged.

    Does not take Calderon passenger_flow_max. A published FAIL stays a FAIL
    until LPTRP/OSM pages actually state headways.
    """
    materialized = list(routes)
    return {
        corridor: lptrp_corridor_veh_h(materialized, needles)
        for corridor, needles in VAL01_CORRIDOR_NEEDLES.items()
    }

