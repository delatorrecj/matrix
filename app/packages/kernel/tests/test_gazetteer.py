"""Tests for the Hiligaynon Gazetteer semantic mapping (CR-008 Item 7)."""
from __future__ import annotations

import json
import os

from matrix_kernel.gazetteer import (
    GAZETTEER_FILE,
    annotate_query_with_gazetteer,
    live_sumo_edges,
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
    assert gaz["merkado"].osm_id == "way/935651848"
    assert gaz["merkado"].street_name == "Valeria"
    assert gaz["merkado"].provisional is False


def test_resolve_colloquial_term_exact_match():
    entry = resolve_colloquial_term("banwa")
    assert entry is not None
    assert entry.canonical_name == "Iloilo City Proper (Downtown)"


def test_resolve_colloquial_term_substring_match():
    # The term appears inside a larger query
    entry = resolve_colloquial_term("ano matabo kung siraduhon ang tulay sa forbes?")
    assert entry is not None
    assert entry.canonical_name == "Forbes Bridge"
    assert "-937061655" in live_sumo_edges(entry)


def test_resolve_colloquial_term_miss():
    entry = resolve_colloquial_term("this has no colloquial terms in it")
    assert entry is None


def test_annotate_query_injects_context():
    query = "siraduhon ang merkado"
    annotated = annotate_query_with_gazetteer(query)
    
    assert annotated != query
    assert "GAZETTEER HIT" in annotated
    assert "Iloilo Central Market" in annotated
    assert "way/935651848" in annotated


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


def test_resolve_canonical_english_names():
    """LLM-extracted English names must hit the same entries as Hiligaynon keys."""
    forbes = resolve_colloquial_term("Forbes Bridge")
    assert forbes is not None
    assert forbes.canonical_name == "Forbes Bridge"
    assert "-937061655" in live_sumo_edges(forbes)

    merkado = resolve_colloquial_term("Iloilo Central Market")
    assert merkado is not None
    assert merkado.canonical_name == "Iloilo Central Market"
    assert merkado.street_name == "Valeria"

    plasa = resolve_colloquial_term("Plaza Libertad")
    assert plasa is not None
    assert plasa.canonical_name == "Plaza Libertad"

    diversion = resolve_colloquial_term("Benigno S. Aquino Jr. Avenue")
    assert diversion is not None
    assert diversion.canonical_name == "Benigno S. Aquino Jr. Avenue"
    assert diversion.street_name == "Aquino Jr"

    lopez = resolve_colloquial_term("Lopez Jaena Street")
    assert lopez is not None
    assert lopez.canonical_name == "Lopez Jaena Street"


def test_english_alias_keys_resolve():
    assert resolve_colloquial_term("forbes").canonical_name == "Forbes Bridge"
    assert resolve_colloquial_term("downtown").canonical_name == "Iloilo City Proper (Downtown)"
    assert resolve_colloquial_term("central market").street_name == "Valeria"


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


def test_live_sumo_edges_prefers_list_over_single_id(tmp_path, monkeypatch):
    payload = {
        "forbes": {
            "canonical_name": "Forbes Bridge",
            "feature_type": "bridge",
            "osm_id": "way/108396738",
            "sumo_edge": "",
            "sumo_edges": ["108396738#0", "-108396738#0"],
            "coordinates": [122.563, 10.702],
            "provisional": False,
        }
    }
    path = tmp_path / "gazetteer.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr("matrix_kernel.gazetteer.GAZETTEER_FILE", str(path))
    entry = load_gazetteer()["forbes"]
    assert live_sumo_edges(entry) == ("108396738#0", "-108396738#0")
    assert entry.snap_radius_m is None


def test_live_sumo_edges_falls_back_to_legacy_sumo_edge(tmp_path, monkeypatch):
    payload = {
        "molo": {
            "canonical_name": "Molo",
            "feature_type": "district",
            "osm_id": "node/molo-centroid",
            "sumo_edge": "E_molo_plaza",
            "coordinates": [122.5446, 10.6969],
            "provisional": True,
            "street_name": "Avanceña",
            "snap_radius_m": 120.0,
        }
    }
    path = tmp_path / "gazetteer.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr("matrix_kernel.gazetteer.GAZETTEER_FILE", str(path))
    entry = load_gazetteer()["molo"]
    assert live_sumo_edges(entry) == ("E_molo_plaza",)
    assert entry.snap_radius_m == 120.0


def test_live_sumo_edges_empty_when_no_ids(tmp_path, monkeypatch):
    payload = {
        "diversion": {
            "canonical_name": "Benigno S. Aquino Jr. Avenue",
            "feature_type": "corridor",
            "osm_id": "way/benigno-aquino-jr",
            "sumo_edge": "",
            "coordinates": [122.555, 10.720],
            "street_name": "Aquino Jr",
        }
    }
    path = tmp_path / "gazetteer.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr("matrix_kernel.gazetteer.GAZETTEER_FILE", str(path))
    assert live_sumo_edges(load_gazetteer()["diversion"]) == ()
