"""Tests for the Hiligaynon Gazetteer semantic mapping (CR-008 Item 7)."""
from __future__ import annotations

import json
import os

from matrix_kernel.gazetteer import (
    GAZETTEER_FILE,
    annotate_query_with_gazetteer,
    load_gazetteer,
    location_coordinates,
    resolve_colloquial_term,
)


def test_gazetteer_json_is_valid():
    """Ensure the JSON file is parsable and contains expected structure."""
    assert os.path.exists(GAZETTEER_FILE)
    with open(GAZETTEER_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "tulay sa forbes" in data
    assert "sumo_edge" in data["tulay sa forbes"]


def test_load_gazetteer():
    gaz = load_gazetteer()
    assert len(gaz) > 0
    assert "merkado" in gaz
    assert gaz["merkado"].osm_id == "way/87654321"


def test_resolve_colloquial_term_exact_match():
    entry = resolve_colloquial_term("banwa")
    assert entry is not None
    assert entry.canonical_name == "Iloilo City Proper (Downtown)"


def test_resolve_colloquial_term_substring_match():
    # The term appears inside a larger query
    entry = resolve_colloquial_term("ano matabo kung siraduhon ang tulay sa forbes?")
    assert entry is not None
    assert entry.sumo_edge == "E_forbes_bridge"


def test_resolve_colloquial_term_miss():
    entry = resolve_colloquial_term("this has no colloquial terms in it")
    assert entry is None


def test_annotate_query_injects_context():
    query = "siraduhon ang merkado"
    annotated = annotate_query_with_gazetteer(query)
    
    assert annotated != query
    assert "GAZETTEER HIT" in annotated
    assert "Iloilo Central Market" in annotated
    assert "way/87654321" in annotated


def test_annotate_query_noop_on_miss():
    query = "what if we add a roundabout with no named place"
    annotated = annotate_query_with_gazetteer(query)
    assert annotated == query


def test_molo_exact_and_query_substring():
    entry = resolve_colloquial_term("Molo")
    assert entry is not None
    assert entry.canonical_name == "Molo"
    assert entry.street_name == "Avanceña"
    assert location_coordinates("Molo") == [122.5446, 10.6969]
    assert location_coordinates("3-storey school in MOLO") == [122.5446, 10.6969]


def test_diversion_aliases_resolve_to_aquino():
    for term in ("Diversion Road", "Diversion Rd", "diversion"):
        entry = resolve_colloquial_term(term)
        assert entry is not None, term
        assert entry.canonical_name == "Benigno S. Aquino Jr. Avenue"
        assert entry.street_name == "Aquino Jr"


def test_location_coordinates_miss():
    assert location_coordinates("this has no colloquial terms in it") is None


def test_load_gazetteer_ignores_unknown_json_keys(tmp_path, monkeypatch):
    """JSON can grow new keys without crashing Scenario parse (street_name TypeError)."""
    payload = {
        "molo": {
            "canonical_name": "Molo",
            "feature_type": "district",
            "osm_id": "node/molo-centroid",
            "sumo_edge": "E_molo_plaza",
            "coordinates": [122.5446, 10.6969],
            "provisional": True,
            "street_name": "Avanceña",
            "future_field": "must-not-crash",
        }
    }
    path = tmp_path / "gazetteer.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr("matrix_kernel.gazetteer.GAZETTEER_FILE", str(path))
    gaz = load_gazetteer()
    assert gaz["molo"].street_name == "Avanceña"
    assert gaz["molo"].canonical_name == "Molo"
