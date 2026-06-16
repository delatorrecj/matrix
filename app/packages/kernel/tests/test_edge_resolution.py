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
