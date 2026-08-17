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
                        lambda loc: ["e1", "e2"] if "aquino" in loc.lower() else [])
    monkeypatch.setattr(runner, "_busiest_baseline_edges", lambda top_n=1: ["BUSIEST"])
    edges, method = runner._resolve_edges(Scenario("s", "d", location="Benigno S. Aquino Jr. Avenue"))
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
    sc = Scenario("s", "d", location="Lopez Jaena Street", geometry={"type": "Point", "coordinates": [0.0, 0.0]})
    edges, method = runner._resolve_edges(sc)
    assert edges == ["e9"]
    assert method == "keyword-match (geometry off-network)"


# --------------------------------------------------------------------------- #
# gazetteer hits must be validated against the real net (CR-013 honesty fix):
# a curated entry can carry a stale/placeholder sumo_edge id.
# --------------------------------------------------------------------------- #

class _FakeGazetteerEntry:
    def __init__(self, sumo_edge, provisional=True):
        self.sumo_edge = sumo_edge
        self.provisional = provisional


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
