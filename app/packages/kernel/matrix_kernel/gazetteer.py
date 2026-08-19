"""Hiligaynon gazetteer for semantic colloquial mapping (CR-008 Item 7).

Resolves regional colloquialisms to deterministic GIS/OSM edges before or alongside LLM orchestration.
Glass-box guarantee: the LLM never *originates* a GIS node id — it can only extract/normalize the
phrase; the id always comes from this curated map, not the model.

PROVISIONAL DATA (CR-008, verified CR-018): entries in `gazetteer_iloilo.json` that
still cannot be tied to the live net stay `"provisional": true`. Verified entries
carry live OSM way ids / SUMO edge ids / street_name aliases from the deployed net.
The "never invented" guarantee is about *who produces the id* (the map, not the
model).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, fields
from typing import Any

GAZETTEER_FILE = os.path.join(os.path.dirname(__file__), "gazetteer_iloilo.json")


@dataclass(frozen=True)
class GazetteerEntry:
    canonical_name: str
    feature_type: str
    osm_id: str
    sumo_edge: str
    coordinates: list[float]
    # True until osm_id/sumo_edge are verified against the deployed OSM extract + SUMO net.
    # Defaults True so an entry missing the flag is treated as unverified, never as ground truth.
    provisional: bool = True
    # OSM/SUMO street-name keyword used when `sumo_edge` is missing from the live net.
    street_name: str = ""
    # Both-direction / multi-segment live SUMO ids. Wins over `sumo_edge` when non-empty.
    sumo_edges: tuple[str, ...] = ()
    # Override for gazetteer-snap radius (metres). None -> feature_type default in runner.
    snap_radius_m: float | None = None


_ENTRY_FIELDS = {f.name for f in fields(GazetteerEntry)}


def _entry_from_raw(val: dict[str, Any]) -> GazetteerEntry:
    """Build an entry from JSON, ignoring keys the dataclass does not declare."""
    raw = {k: v for k, v in val.items() if k in _ENTRY_FIELDS}
    edges = raw.get("sumo_edges") or ()
    raw["sumo_edges"] = tuple(str(e) for e in edges if str(e).strip())
    snap = raw.get("snap_radius_m")
    raw["snap_radius_m"] = None if snap is None else float(snap)
    return GazetteerEntry(**raw)


def live_sumo_edges(entry: GazetteerEntry) -> tuple[str, ...]:
    """Edge ids to try against the live net: `sumo_edges` if set, else the legacy single id."""
    listed = tuple(e for e in (getattr(entry, "sumo_edges", ()) or ()) if str(e).strip())
    if listed:
        return listed
    single = (getattr(entry, "sumo_edge", "") or "").strip()
    if single:
        return (single,)
    return ()


def load_gazetteer() -> dict[str, GazetteerEntry]:
    """Load the JSON gazetteer map into memory."""
    if not os.path.exists(GAZETTEER_FILE):
        return {}
    with open(GAZETTEER_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    return {
        key.lower(): _entry_from_raw(val)
        for key, val in raw_data.items()
    }


def resolve_colloquial_term(term: str) -> GazetteerEntry | None:
    """Resolve a raw location or query string to a gazetteer entry.

    Order: exact JSON key, exact canonical_name, exact street_name, then
    longest-first substrings of key / canonical_name / street_name (street
    names shorter than 4 characters are skipped so fragments like "Jr" do
    not false-hit). The LLM often extracts the English canonical name
    ("Forbes Bridge") rather than the Hiligaynon key ("tulay sa forbes").
    """
    term_lower = (term or "").strip().lower()
    if not term_lower:
        return None
    gaz = load_gazetteer()

    if term_lower in gaz:
        return gaz[term_lower]

    for entry in gaz.values():
        name = (entry.canonical_name or "").strip().lower()
        if name and term_lower == name:
            return entry

    for entry in gaz.values():
        street = (entry.street_name or "").strip().lower()
        if street and term_lower == street:
            return entry

    for key, entry in sorted(gaz.items(), key=lambda kv: len(kv[0]), reverse=True):
        if key and key in term_lower:
            return entry

    by_canonical = sorted(
        gaz.values(),
        key=lambda e: len((e.canonical_name or "").strip()),
        reverse=True,
    )
    for entry in by_canonical:
        name = (entry.canonical_name or "").strip().lower()
        if name and name in term_lower:
            return entry

    by_street = sorted(
        gaz.values(),
        key=lambda e: len((e.street_name or "").strip()),
        reverse=True,
    )
    for entry in by_street:
        street = (entry.street_name or "").strip().lower()
        if len(street) >= 4 and street in term_lower:
            return entry

    return None


def location_coordinates(term: str) -> list[float] | None:
    """Camera [lon, lat] for a place name. Does not require a live SUMO edge."""
    entry = resolve_colloquial_term(term)
    if not entry or len(entry.coordinates) < 2:
        return None
    return [float(entry.coordinates[0]), float(entry.coordinates[1])]


def annotate_query_with_gazetteer(query: str) -> str:
    """Pre-process a query string by injecting canonical context if a colloquial term hits.
    
    This helps the LLM orchestrator ground its extraction in deterministic node IDs.
    """
    entry = resolve_colloquial_term(query)
    if not entry:
        return query
        
    # Inject canonical context into the query for the LLM to consume. The PROVISIONAL marker
    # rides along so the model never treats an unverified placeholder id as ground truth.
    flag = " PROVISIONAL-id" if entry.provisional else ""
    street = f", street: {entry.street_name}" if entry.street_name else ""
    injection = (
        f"\n[GAZETTEER HIT{flag}: '{entry.canonical_name}' (OSM: {entry.osm_id}, "
        f"SUMO Edge: {entry.sumo_edge}{street})]"
    )
    return query + injection
