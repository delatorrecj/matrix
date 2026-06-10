"""sumolib-backed integration tests for the geometry engine (real Iloilo net).

Guarded like the other SUMO-dependent test modules: a bare venv (no eclipse-sumo)
skips at collection, and a venv without the built network skips at module level
(data/iloilo.net.xml is gitignored -- run build_network.py to materialize it).
With the kernel venv + net present these exercise the real projection and
getNeighboringEdges paths that test_geometry.py only fakes. Anchors derive from
the net itself (no hard-coded Iloilo coordinates), so they stay city-agnostic.
"""
import pytest

pytest.importorskip(
    "sumo", reason="eclipse-sumo not installed; run `uv sync` in app/packages/kernel"
)

from matrix_kernel.geometry import (  # noqa: E402  (import after the SUMO guard)
    NET,
    edges_in_polygon,
    edges_near_point,
    load_net,
    resolve_geometry,
)

if not NET.exists():
    pytest.skip(f"{NET} missing -- run build_network.py", allow_module_level=True)


@pytest.fixture(scope="module")
def net():
    return load_net()


@pytest.fixture(scope="module")
def anchor(net):
    """A real edge + one of its shape vertices in lon/lat -- derived, not hard-coded."""
    edge = max(net.getEdges(), key=lambda e: (len(e.getShape()), e.getID()))
    x, y = edge.getShape()[0]
    lon, lat = net.convertXY2LonLat(x, y)
    return edge, lon, lat


def test_load_net_is_cached_across_path_spellings():
    # Default, Path, and str spellings of the same file share ONE cache entry --
    # the ~42 MB net must never be parsed twice.
    assert load_net() is load_net(NET) is load_net(str(NET))


def test_point_on_known_edge_resolves_it(net, anchor):
    edge, lon, lat = anchor
    ids = edges_near_point(net, lon, lat, radius_m=50.0)
    assert edge.getID() in ids
    assert ids == sorted(set(ids))  # deterministic: sorted + deduped


def test_polygon_around_known_edge_resolves_it(net, anchor):
    edge, lon, lat = anchor
    d = 0.002  # ~220 m of latitude around the anchor vertex
    ring = [
        [lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d],
        [lon - d, lat + d], [lon - d, lat - d],
    ]
    ids = edges_in_polygon(net, {"type": "Polygon", "coordinates": [ring]})
    assert edge.getID() in ids
    assert ids == sorted(set(ids))


def test_offnetwork_point_is_honest_empty(net):
    # Null Island is nowhere near the pilot net: honest miss, no fallback guess (PRD-F14).
    assert edges_near_point(net, 0.0, 0.0, radius_m=100.0) == []


def test_resolve_geometry_feature_on_real_net(net, anchor):
    edge, lon, lat = anchor
    feature = {
        "type": "Feature",
        "properties": {"name": "proposed school"},
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }
    assert edge.getID() in resolve_geometry(net, feature, radius_m=50.0)
