"""Hiligaynon gazetteer for semantic colloquial mapping (CR-008 Item 7).

Resolves regional colloquialisms to deterministic GIS/OSM edges before or alongside LLM orchestration.
Glass-box guarantee: the LLM may extract/normalize the phrase, but the node id is sourced from the
gazetteer mapping, never invented.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

GAZETTEER_FILE = os.path.join(os.path.dirname(__file__), "gazetteer_iloilo.json")


@dataclass(frozen=True)
class GazetteerEntry:
    canonical_name: str
    feature_type: str
    osm_id: str
    sumo_edge: str
    coordinates: list[float]


def load_gazetteer() -> dict[str, GazetteerEntry]:
    """Load the JSON gazetteer map into memory."""
    if not os.path.exists(GAZETTEER_FILE):
        return {}
    with open(GAZETTEER_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    return {
        key.lower(): GazetteerEntry(**val)
        for key, val in raw_data.items()
    }


def resolve_colloquial_term(term: str) -> GazetteerEntry | None:
    """Attempt to resolve a raw text string to a gazetteer entry.
    
    Checks exact matches or substring inclusion.
    Returns the first matching entry, or None if no alias matches.
    """
    term_lower = term.lower()
    gaz = load_gazetteer()
    
    # Direct hit
    if term_lower in gaz:
        return gaz[term_lower]
        
    # Substring hit (e.g., "siraduhon ang tulay sa forbes" -> matches "tulay sa forbes")
    for key, entry in gaz.items():
        if key in term_lower:
            return entry
            
    return None


def annotate_query_with_gazetteer(query: str) -> str:
    """Pre-process a query string by injecting canonical context if a colloquial term hits.
    
    This helps the LLM orchestrator ground its extraction in deterministic node IDs.
    """
    entry = resolve_colloquial_term(query)
    if not entry:
        return query
        
    # Inject canonical context into the query for the LLM to consume
    injection = (
        f"\n[GAZETTEER HIT: '{entry.canonical_name}' (OSM: {entry.osm_id}, "
        f"SUMO Edge: {entry.sumo_edge})]"
    )
    return query + injection
