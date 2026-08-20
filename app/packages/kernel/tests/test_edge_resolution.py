"""Edge-resolution honesty (PRD-F14): _resolve_edges must report HOW it resolved.

The net now carries street names (build_network.py --output.street-names), so a named
corridor resolves by keyword. When nothing matches, the busiest-baseline edge is an honest
LAST RESORT -- it must be labeled a fallback, never mislabeled "keyword-match" (the prior
behavior, when the net had no names so every keyword silently fell back to the busiest edge).

The net/baseline/geometry seams are monkeypatched, so these run without a real net or Redis
(importing matrix_kernel.runner still needs the eclipse-sumo wheel -> guarded like the other
SUMO-dependent kernel tests)."""
import pytest

pytest.importorskip("sumo", reason="eclipse-sumo not installed (bare env)")

from matrix_kernel import runner
from matrix_kernel.scenario import Scenario


def test_keyword_match_is_labeled_keyword_match(monkeypatch):
    monkeypatch.setattr(runner, "_keyword_edges",
                        lambda loc: ["e1", "e2"] if "luna" in loc.lower() else [])
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    edges, method = runner._resolve_edges(Scenario("s", "d", location="General Luna Street"))
    assert edges == ["e1", "e2"]
    assert method == "keyword-match"


def test_no_name_match_is_labeled_fallback_and_names_the_location(monkeypatch):
    monkeypatch.setattr(runner, "_keyword_edges", lambda loc: [])
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    edges, method = runner._resolve_edges(Scenario("s", "d", location="Nonexistent Road"))
    assert edges == ["BUSIEST"]
    assert method.startswith("busiest-baseline-fallback")
    assert "Nonexistent Road" in method        # the unmatched location is named, not hidden
    assert "keyword-match" not in method        # the anti-regression: never mislabeled


def test_no_location_is_labeled_fallback(monkeypatch):
    monkeypatch.setattr(runner, "_keyword_edges", lambda loc: [])
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    _edges, method = runner._resolve_edges(Scenario("s", "d", location=""))
    assert method == "busiest-baseline-fallback (no location given)"


def test_geometry_resolution_wins(monkeypatch):
    import matrix_kernel.geometry as geo
    monkeypatch.setattr(runner, "_net", lambda: object())
    monkeypatch.setattr(geo, "resolve_geometry", lambda net, g: ["G1", "G2"])
    sc = Scenario("s", "d", location="ignored", geometry={"type": "Point", "coordinates": [122.5, 10.7]})
    edges, method = runner._resolve_edges(sc)
    assert edges == ["G1", "G2"]
    assert method == "geometry"


def test_geometry_off_network_falls_back_and_says_so(monkeypatch):
    import matrix_kernel.geometry as geo
    monkeypatch.setattr(runner, "_net", lambda: object())
    monkeypatch.setattr(geo, "resolve_geometry", lambda net, g: [])   # touches no edge
    monkeypatch.setattr(runner, "_keyword_edges", lambda loc: [])
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    sc = Scenario("s", "d", location="X", geometry={"type": "Point", "coordinates": [0.0, 0.0]})
    edges, method = runner._resolve_edges(sc)
    assert edges == ["BUSIEST"]
    assert "geometry off-network" in method


def test_geometry_off_network_keyword_still_matches(monkeypatch):
    """Off-network geometry but a resolvable location name -> keyword match, flagged."""
    import matrix_kernel.geometry as geo
    monkeypatch.setattr(runner, "_net", lambda: object())
    monkeypatch.setattr(geo, "resolve_geometry", lambda net, g: [])
    monkeypatch.setattr(runner, "_keyword_edges", lambda loc: ["e9"])
    sc = Scenario("s", "d", location="General Luna Street", geometry={"type": "Point", "coordinates": [0.0, 0.0]})
    edges, method = runner._resolve_edges(sc)
    assert edges == ["e9"]
    assert method == "keyword-match (geometry off-network)"


# --------------------------------------------------------------------------- #
# gazetteer hits must be validated against the real net (CR-013 honesty fix):
# a curated entry can carry a stale/placeholder sumo_edge id.
# --------------------------------------------------------------------------- #

class _FakeGazetteerEntry:
    def __init__(
        self,
        sumo_edge,
        provisional=True,
        street_name="",
        osm_id="",
        coordinates=None,
        feature_type="bridge",
        sumo_edges=(),
        snap_radius_m=None,
    ):
        self.sumo_edge = sumo_edge
        self.provisional = provisional
        self.street_name = street_name
        self.osm_id = osm_id
        self.coordinates = list(coordinates) if coordinates is not None else []
        self.feature_type = feature_type
        self.sumo_edges = tuple(sumo_edges)
        self.snap_radius_m = snap_radius_m


def test_gazetteer_match_requires_the_edge_to_exist_in_net(monkeypatch):
    import matrix_kernel.gazetteer as gaz
    monkeypatch.setattr(gaz, "resolve_colloquial_term", lambda loc: _FakeGazetteerEntry("E_real"))
    monkeypatch.setattr(runner, "_edge_ids", lambda: frozenset({"E_real"}))
    edges, method = runner._resolve_edges(Scenario("s", "d", location="merkado"))
    assert edges == ["E_real"]
    assert method.startswith("gazetteer-match")


def test_gazetteer_match_with_nonexistent_edge_falls_through_honestly(monkeypatch):
    """A gazetteer entry whose sumo_edge doesn't exist in the net must NOT be reported
    as a match (the prior bug: claims 'gazetteer-match' while touching zero edges)."""
    import matrix_kernel.gazetteer as gaz
    monkeypatch.setattr(gaz, "resolve_colloquial_term", lambda loc: _FakeGazetteerEntry("E_fake_placeholder"))
    monkeypatch.setattr(runner, "_edge_ids", lambda: frozenset())  # E_fake_placeholder not in net
    monkeypatch.setattr(runner, "_keyword_edges", lambda loc: [])
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    edges, method = runner._resolve_edges(Scenario("s", "d", location="merkado"))
    assert edges == ["BUSIEST"]
    assert "gazetteer-match" not in method
    assert method.startswith("busiest-baseline-fallback")


def test_gazetteer_match_with_nonexistent_edge_falls_to_keyword_match(monkeypatch):
    """When the gazetteer's edge is invalid but the location keyword also matches a
    real street name, keyword-match wins over the hash fallback."""
    import matrix_kernel.gazetteer as gaz
    monkeypatch.setattr(gaz, "resolve_colloquial_term", lambda loc: _FakeGazetteerEntry("E_fake_placeholder"))
    monkeypatch.setattr(runner, "_edge_ids", lambda: frozenset())
    monkeypatch.setattr(runner, "_keyword_edges", lambda loc: ["e9"])
    edges, method = runner._resolve_edges(Scenario("s", "d", location="merkado"))
    assert edges == ["e9"]
    assert method == "keyword-match"


def test_gazetteer_street_name_used_when_sumo_edge_missing(monkeypatch):
    """Molo / Diversion Rd: placeholder sumo_edge, but a curated street_name hits the net."""
    import matrix_kernel.gazetteer as gaz
    monkeypatch.setattr(
        gaz,
        "resolve_colloquial_term",
        lambda loc: _FakeGazetteerEntry("E_molo_plaza", street_name="Avanceña"),
    )
    monkeypatch.setattr(runner, "_edge_ids", lambda: frozenset())

    def kw(loc: str) -> list[str]:
        key = loc.lower()
        if "avanceña" in key or "avance" in key:
            return ["e-avancena"]
        return []

    monkeypatch.setattr(runner, "_keyword_edges", kw)
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    edges, method = runner._resolve_edges(Scenario("s", "d", location="Molo"))
    assert edges == ["e-avancena"]
    assert method == "gazetteer-alias"


_FORBES_LIVE = ("-937061655", "-306785269", "937061662", "306785268")


def test_english_forbes_bridge_location_is_gazetteer_not_fallback(monkeypatch):
    """LLM-extracted 'Forbes Bridge' must not hash onto a busy baseline edge."""
    monkeypatch.setattr(runner, "_edge_ids", lambda: frozenset(_FORBES_LIVE))
    monkeypatch.setattr(runner, "_osm_orig_ids", lambda: {})
    monkeypatch.setattr(runner, "_keyword_edges", lambda loc: [])
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    edges, method = runner._resolve_edges(Scenario("s", "d", location="Forbes Bridge"))
    assert "-937061655" in edges
    assert "gazetteer-match" in method
    assert not method.startswith("busiest-baseline-fallback")


def test_english_central_market_location_is_gazetteer_alias(monkeypatch):
    monkeypatch.setattr(runner, "_edge_ids", lambda: frozenset())
    monkeypatch.setattr(runner, "_osm_orig_ids", lambda: {})
    monkeypatch.setattr(
        runner, "_keyword_edges",
        lambda loc: ["e-valeria"] if "valeria" in loc.lower() else [],
    )
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    edges, method = runner._resolve_edges(
        Scenario("s", "d", location="Iloilo Central Market")
    )
    assert edges == ["e-valeria"]
    assert method == "gazetteer-alias"


def test_description_used_when_location_misses_gazetteer(monkeypatch):
    monkeypatch.setattr(runner, "_edge_ids", lambda: frozenset(_FORBES_LIVE))
    monkeypatch.setattr(runner, "_osm_orig_ids", lambda: {})
    monkeypatch.setattr(runner, "_keyword_edges", lambda loc: [])
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    edges, method = runner._resolve_edges(
        Scenario(
            "s",
            "close the bridge at Forbes for roadworks",
            location="unknown-place-xyz",
        )
    )
    assert "-937061655" in edges
    assert not method.startswith("busiest-baseline-fallback")


def test_gazetteer_match_uses_sumo_edges_list(monkeypatch):
    import matrix_kernel.gazetteer as gaz
    monkeypatch.setattr(
        gaz,
        "resolve_colloquial_term",
        lambda loc: _FakeGazetteerEntry("", sumo_edges=("a", "-a"), provisional=False),
    )
    monkeypatch.setattr(runner, "_edge_ids", lambda: frozenset({"a", "-a", "other"}))
    edges, method = runner._resolve_edges(Scenario("s", "d", location="tulay sa forbes"))
    assert edges == ["a", "-a"]
    assert method == "gazetteer-match"


def test_parse_osm_way_id():
    assert runner._parse_osm_way_id("way/108396738") == "108396738"
    assert runner._parse_osm_way_id("108396738") == "108396738"
    assert runner._parse_osm_way_id("node/molo-centroid") is None
    assert runner._parse_osm_way_id("way/benigno-aquino-jr") is None
    assert runner._parse_osm_way_id("") is None


def test_gazetteer_osmid_when_sumo_edge_missing(monkeypatch):
    import matrix_kernel.gazetteer as gaz
    monkeypatch.setattr(
        gaz,
        "resolve_colloquial_term",
        lambda loc: _FakeGazetteerEntry("E_fake", osm_id="way/108396738"),
    )
    monkeypatch.setattr(runner, "_edge_ids", lambda: frozenset())
    monkeypatch.setattr(
        runner, "_osm_orig_ids", lambda: {"108396738": ("108396738#0", "-108396738#0")}
    )
    monkeypatch.setattr(runner, "_keyword_edges", lambda loc: [])
    edges, method = runner._resolve_edges(Scenario("s", "d", location="tulay sa forbes"))
    assert edges == ["108396738#0", "-108396738#0"]
    assert method == "gazetteer-osmid"


def test_gazetteer_snap_when_no_id_or_street(monkeypatch):
    import matrix_kernel.gazetteer as gaz
    import matrix_kernel.geometry as geo
    monkeypatch.setattr(
        gaz,
        "resolve_colloquial_term",
        lambda loc: _FakeGazetteerEntry(
            "E_fake", coordinates=[122.563, 10.702], feature_type="bridge"
        ),
    )
    monkeypatch.setattr(runner, "_edge_ids", lambda: frozenset())
    monkeypatch.setattr(runner, "_osm_orig_ids", lambda: {})
    monkeypatch.setattr(runner, "_keyword_edges", lambda loc: [])
    monkeypatch.setattr(runner, "_net", lambda: object())
    monkeypatch.setattr(
        geo, "nearest_edges", lambda net, lon, lat, radius_m, cap: ["snap-a", "snap-b"]
    )
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    edges, method = runner._resolve_edges(Scenario("s", "d", location="merkado"))
    assert edges == ["snap-a", "snap-b"]
    assert method == "gazetteer-snap"


def test_gazetteer_empty_snap_keeps_hash_fallback(monkeypatch):
    import matrix_kernel.gazetteer as gaz
    import matrix_kernel.geometry as geo
    monkeypatch.setattr(
        gaz,
        "resolve_colloquial_term",
        lambda loc: _FakeGazetteerEntry(
            "E_fake", coordinates=[122.0, 10.0], feature_type="plaza"
        ),
    )
    monkeypatch.setattr(runner, "_edge_ids", lambda: frozenset())
    monkeypatch.setattr(runner, "_osm_orig_ids", lambda: {})
    monkeypatch.setattr(runner, "_keyword_edges", lambda loc: [])
    monkeypatch.setattr(runner, "_net", lambda: object())
    monkeypatch.setattr(geo, "nearest_edges", lambda *a, **k: [])
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    edges, method = runner._resolve_edges(Scenario("s", "d", location="plasa"))
    assert edges == ["BUSIEST"]
    assert method.startswith("busiest-baseline-fallback")
    assert "gazetteer-snap" not in method


# --------------------------------------------------------------------------- #
# _location_of_interest -- the results-view map marker/pan's ground truth
# (CR-013): only for a real resolution, never for a fallback.
# --------------------------------------------------------------------------- #

def test_location_of_interest_none_when_no_edges_affected():
    assert runner._location_of_interest([], "busiest-baseline-fallback (no location given)") is None


def test_location_of_interest_none_for_any_fallback_variant():
    assert runner._location_of_interest(["e1"], "busiest-baseline-fallback (deterministic-hash; x)") is None


def test_location_of_interest_set_for_keyword_match(monkeypatch):
    import matrix_kernel.geometry as geo
    # _location_of_interest evaluates _net() as the first argument, BEFORE the patched
    # midpoint runs -- patching only edge_midpoint_lonlat still reads the real (gitignored)
    # net, so this passed locally and failed in CI. Patch the net seam too, like the tests above.
    monkeypatch.setattr(runner, "_net", lambda: object())
    monkeypatch.setattr(geo, "edge_midpoint_lonlat", lambda net, eid: (122.123456, 10.654321))
    assert runner._location_of_interest(["e1", "e2"], "keyword-match") == [122.12346, 10.65432]


def test_location_of_interest_uses_first_edge_only_not_a_centroid(monkeypatch):
    """Multiple keyword-matched edges (e.g. a street name matching segments in two
    unrelated neighborhoods) must not be averaged into a meaningless midpoint."""
    import matrix_kernel.geometry as geo
    seen_edge_ids = []

    def fake_midpoint(net, eid):
        seen_edge_ids.append(eid)
        return (1.0, 2.0)

    monkeypatch.setattr(runner, "_net", lambda: object())   # see note above
    monkeypatch.setattr(geo, "edge_midpoint_lonlat", fake_midpoint)
    runner._location_of_interest(["first", "second", "third"], "keyword-match")
    assert seen_edge_ids == ["first"]


def test_new_facility_site_is_facility_adjacent_not_a_corridor(monkeypatch):
    """A school in Molo must not close Avanceña or hash onto the busiest edge."""
    import matrix_kernel.geometry as geo

    monkeypatch.setattr(runner, "_keyword_edges", lambda loc: ["AVANCENA"])
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    monkeypatch.setattr(runner, "_facility_adjacent_edges", lambda sc: ["E_molo_plaza"])
    monkeypatch.setattr(runner, "_net", lambda: object())
    monkeypatch.setattr(geo, "edge_midpoint_lonlat", lambda net, eid: (122.5446, 10.6969))
    sc = Scenario(
        "s1",
        "3000-seat school in Molo",
        intervention_type="new_facility",
        location="Molo",
        parameters={"facility_kind": "school", "capacity": 3000},
    )
    edges, method = runner.resolve_intervention_site(sc)
    assert edges == ["E_molo_plaza"]
    assert method == "facility-adjacent"
    assert "AVANCENA" not in edges
    assert "BUSIEST" not in edges
    assert not method.startswith("busiest-baseline-fallback")
    assert runner._location_of_interest(edges, method) == [122.5446, 10.6969]


def test_new_facility_without_adjacent_edges_is_facility_demand(monkeypatch):
    monkeypatch.setattr(runner, "_keyword_edges", lambda loc: ["AVANCENA"])
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    monkeypatch.setattr(runner, "_facility_adjacent_edges", lambda sc: [])
    sc = Scenario(
        "s1",
        "3000-seat school in Molo",
        intervention_type="new_facility",
        location="Molo",
        parameters={"facility_kind": "school", "capacity": 3000},
    )
    edges, method = runner.resolve_intervention_site(sc)
    assert edges == []
    assert method == "facility-demand"
    assert runner._location_of_interest(edges, method) is None


def test_facility_demand_meta_is_beh4_summary_without_trips():
    sc = Scenario(
        "s1",
        "3000-seat school in Molo",
        intervention_type="new_facility",
        location="Molo",
        parameters={"facility_kind": "school", "capacity": 3000},
    )
    meta = runner.facility_demand_meta(sc)
    assert meta is not None
    assert meta["demand_trips_total"] == 2700
    assert meta["equation_id"] == "BEH-4"
    assert meta["input_dataset_ids"] == ["Calderon2014"]
    assert meta["confidence"] == "L"
    assert "trips" not in meta
    assert runner.facility_demand_meta(Scenario("s", "d", location="Molo")) is None


def _live_net_path():
    from pathlib import Path
    from matrix_kernel.geometry import NET

    if NET.exists():
        return NET
    hf = Path(__file__).resolve().parents[4] / "deploy" / "hf-space" / "iloilo.net.xml"
    return hf if hf.is_file() else None


def test_demo_aliases_resolve_on_live_net(monkeypatch):
    """Non-provisional gazetteer aliases must hit the deployed net, never the hash."""
    net_path = _live_net_path()
    if net_path is None:
        pytest.skip("iloilo.net.xml missing")
    from matrix_kernel.geometry import load_net

    net = load_net(net_path)
    monkeypatch.setattr(runner, "_net", lambda: net)
    runner._edge_ids.cache_clear()
    runner._osm_orig_ids.cache_clear()

    honest = ("gazetteer-match", "gazetteer-osmid", "gazetteer-alias", "gazetteer-snap")
    for loc in (
        "tulay sa forbes",
        "Forbes Bridge",
        "Iloilo Central Market",
        "merkado",
        "Molo",
        "Diversion Road",
        "lopez jaena",
        "jaro",
        "plasa",
        "banwa",
        "Plaza Libertad",
        "Lopez Jaena Street",
    ):
        edges, method = runner._resolve_edges(Scenario("s", "d", location=loc))
        assert edges, loc
        assert any(method.startswith(prefix) for prefix in honest), (loc, method)
        assert not method.startswith("busiest-baseline-fallback")


# --------------------------------------------------------------------------- #
# Named spans (Cuartero from Fajardo to El 98). FakeNet — no live SUMO load.
# --------------------------------------------------------------------------- #

from tests.test_span import SPAN_IDS, cuartero_net


def _patch_cuartero(monkeypatch):
    net = cuartero_net()
    monkeypatch.setattr(runner, "_net", lambda: net)
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["busy-1"])
    import matrix_kernel.gazetteer as gaz
    monkeypatch.setattr(gaz, "resolve_colloquial_term", lambda loc: None)
    return net


def test_stuffed_location_extracts_cuartero_and_does_not_hash(monkeypatch):
    _patch_cuartero(monkeypatch)
    stuffed = "Cuartero Street, segment from Fajardo St. to EL98 st."
    edges, method = runner._resolve_edges(Scenario("s", "d", location=stuffed))
    assert edges
    assert all("154184307" in eid for eid in edges)
    assert "busy-1" not in edges
    assert not method.startswith("busiest-baseline-fallback")
    assert "cuartero" in method or method.startswith("keyword-")


def test_cuartero_span_fields_clip_to_fajardo_el98(monkeypatch):
    _patch_cuartero(monkeypatch)
    sc = Scenario(
        "s",
        "d",
        location="Cuartero Street",
        intervention_type="full_closure",
        parameters={"from_cross": "Fajardo Street", "to_cross": "El 98 Street"},
    )
    edges, method = runner._resolve_edges(sc)
    assert method == "keyword-span"
    assert set(edges) == SPAN_IDS


def test_whole_street_cuartero_is_all_24(monkeypatch):
    _patch_cuartero(monkeypatch)
    edges, method = runner._resolve_edges(Scenario("s", "d", location="Cuartero Street"))
    assert method == "keyword-match"
    assert len(edges) == 24
    assert all("154184307" in eid for eid in edges)


def test_unknown_place_still_hashes(monkeypatch):
    _patch_cuartero(monkeypatch)
    edges, method = runner._resolve_edges(Scenario("s", "d", location="No Such Place XYZ"))
    assert edges == ["busy-1"]
    assert method.startswith("busiest-baseline-fallback")


def test_cuartero_span_on_live_net(monkeypatch):
    net_path = _live_net_path()
    if net_path is None:
        pytest.skip("iloilo.net.xml missing")
    from matrix_kernel.geometry import load_net

    net = load_net(net_path)
    monkeypatch.setattr(runner, "_net", lambda: net)
    runner._edge_ids.cache_clear()
    runner._osm_orig_ids.cache_clear()
    sc = Scenario(
        "s",
        "d",
        location="Cuartero Street",
        intervention_type="full_closure",
        parameters={"from_cross": "Fajardo Street", "to_cross": "El 98 Street"},
    )
    edges, method = runner._resolve_edges(sc)
    assert method == "keyword-span"
    assert set(edges) == SPAN_IDS
