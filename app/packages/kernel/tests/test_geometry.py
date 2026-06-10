"""Tests for the geometry engine's pure paths (no SUMO wheel needed).

`matrix_kernel.geometry` imports no SUMO code at module top and its resolvers take a
duck-typed net, so everything here runs on a bare venv: GeoJSON parsing/validation,
the planar predicates, and the resolvers against a FakeNet with an identity
projection. The sumolib-backed integration lives in test_geometry_sumolib.py.
"""
import math

import pytest

from matrix_kernel import geometry
from matrix_kernel.geometry import (
    edges_in_polygon,
    edges_near_point,
    geometries,
    point_in_polygon,
    point_in_ring,
    polygon_rings,
    polyline_intersects_polygon,
    resolve_geometry,
)


# --------------------------------------------------------------------------- #
# Duck-typed stand-ins for sumolib (identity lon/lat -> XY projection)
# --------------------------------------------------------------------------- #

def _dist_point_segment(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class FakeEdge:
    def __init__(self, eid, shape):
        self._id = eid
        self._shape = [tuple(p) for p in shape]

    def getID(self):
        return self._id

    def getShape(self, includeJunctions=False):
        return list(self._shape)


class FakeNet:
    """Mimics the slice of sumolib.net.Net the resolvers use. Identity projection
    keeps the test coordinates readable (degrees == metres here). Distance filter
    is strict (`d < r`), matching sumolib's getNeighboringEdges."""

    def __init__(self, edges):
        self._edges = list(edges)

    def convertLonLat2XY(self, lon, lat):
        return lon, lat

    def getEdges(self):
        return list(self._edges)

    def getNeighboringEdges(self, x, y, r=0.1, includeJunctions=True, allowFallback=True):
        out = []
        for edge in self._edges:
            shape = edge.getShape()
            if len(shape) == 1:
                d = math.hypot(x - shape[0][0], y - shape[0][1])
            else:
                d = min(_dist_point_segment((x, y), a, b) for a, b in zip(shape, shape[1:]))
            if d < r:
                out.append((edge, d))
        return out


@pytest.fixture
def net():
    # Three edges on a 10x10 lon/lat patch: a horizontal road through the middle,
    # a vertical road on the east side, and a short stub in the north-west corner.
    return FakeNet(
        [
            FakeEdge("B_horizontal", [(0.0, 5.0), (10.0, 5.0)]),
            FakeEdge("A_vertical", [(8.0, 0.0), (8.0, 10.0)]),
            FakeEdge("C_stub", [(1.0, 9.0), (2.0, 9.0)]),
        ]
    )


def square(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]


# --------------------------------------------------------------------------- #
# geometries() -- GeoJSON flattening + validation
# --------------------------------------------------------------------------- #

def test_geometries_passes_bare_point_and_polygon_through():
    pt = {"type": "Point", "coordinates": [1.0, 2.0]}
    poly = {"type": "Polygon", "coordinates": [square(0, 0, 1, 1)]}
    assert geometries(pt) == [pt]
    assert geometries(poly) == [poly]


def test_geometries_unwraps_feature_and_collections():
    pt = {"type": "Point", "coordinates": [1.0, 2.0]}
    poly = {"type": "Polygon", "coordinates": [square(0, 0, 1, 1)]}
    assert geometries({"type": "Feature", "properties": {}, "geometry": pt}) == [pt]
    fc = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": pt},
            {"type": "Feature", "geometry": poly},
        ],
    }
    assert geometries(fc) == [pt, poly]
    gc = {"type": "GeometryCollection", "geometries": [pt, poly]}
    assert geometries(gc) == [pt, poly]


def test_geometries_splits_multi_types():
    mp = {"type": "MultiPoint", "coordinates": [[1.0, 2.0], [3.0, 4.0]]}
    assert geometries(mp) == [
        {"type": "Point", "coordinates": [1.0, 2.0]},
        {"type": "Point", "coordinates": [3.0, 4.0]},
    ]
    mpoly = {"type": "MultiPolygon", "coordinates": [[square(0, 0, 1, 1)], [square(2, 2, 3, 3)]]}
    assert [g["type"] for g in geometries(mpoly)] == ["Polygon", "Polygon"]


@pytest.mark.parametrize(
    "bad",
    [
        "not a dict",
        {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},  # unsupported type
        {"type": "Feature", "geometry": None},                    # null geometry
        {"type": "FeatureCollection", "features": []},            # nothing to resolve
        {"type": "GeometryCollection", "geometries": []},
        {"type": "MultiPolygon", "coordinates": []},
        {"type": "Point"},                                        # no coordinates
        {"coordinates": [1, 2]},                                  # no type
    ],
)
def test_geometries_rejects_unresolvable_input(bad):
    with pytest.raises(ValueError):
        geometries(bad)


# --------------------------------------------------------------------------- #
# polygon_rings() -- ring validation
# --------------------------------------------------------------------------- #

def test_polygon_rings_accepts_closed_and_closes_unclosed():
    closed = polygon_rings([square(0, 0, 2, 2)])
    unclosed = polygon_rings([square(0, 0, 2, 2)[:-1]])
    assert closed == unclosed
    assert closed[0][0] == closed[0][-1]


def test_polygon_rings_keeps_holes():
    rings = polygon_rings([square(0, 0, 10, 10), square(4, 4, 6, 6)])
    assert len(rings) == 2


@pytest.mark.parametrize(
    "bad",
    [
        [],                                       # no rings
        [[[0, 0], [1, 1]]],                       # < 3 distinct positions
        [[[0, 0], [1, 1], [0, 0], [1, 1]]],       # degenerate after closing
        [[[0, 0], [1, "x"], [1, 1]]],             # non-numeric coordinate
        [[[200.0, 0], [1, 0], [1, 1]]],           # lon out of range
        [[[122.56, 10.72], [10.72, 122.56], [0, 0]]],  # swapped lon/lat
        "nope",
    ],
)
def test_polygon_rings_rejects_malformed(bad):
    with pytest.raises(ValueError):
        polygon_rings(bad)


# --------------------------------------------------------------------------- #
# Planar predicates
# --------------------------------------------------------------------------- #

def test_point_in_ring_and_polygon_with_hole():
    rings = polygon_rings([square(0, 0, 10, 10), square(4, 4, 6, 6)])
    assert point_in_ring(1.0, 1.0, rings[0])
    assert not point_in_ring(11.0, 1.0, rings[0])
    assert point_in_polygon(1.0, 1.0, rings)        # inside, clear of the hole
    assert not point_in_polygon(5.0, 5.0, rings)    # inside the hole -> outside the area
    assert not point_in_polygon(-1.0, 5.0, rings)   # outside the exterior


def test_segments_intersect_cases():
    seg = geometry._segments_intersect
    assert seg((0, 0), (2, 2), (0, 2), (2, 0))      # proper crossing
    assert seg((0, 0), (2, 0), (1, 0), (3, 0))      # collinear overlap
    assert seg((0, 0), (2, 0), (2, 0), (2, 2))      # touching at an endpoint
    assert seg((0, 0), (2, 0), (1, -1), (1, 1))     # crossing through the interior
    assert not seg((0, 0), (1, 0), (0, 1), (1, 1))  # parallel, disjoint
    assert not seg((0, 0), (1, 0), (2, 0), (3, 0))  # collinear, disjoint


def test_polyline_intersects_polygon_modes():
    rings = polygon_rings([square(2, 2, 8, 8)])
    assert polyline_intersects_polygon([(3.0, 3.0), (4.0, 3.0)], rings)   # vertex inside
    assert polyline_intersects_polygon([(0.0, 5.0), (10.0, 5.0)], rings)  # crosses, no vertex inside
    assert not polyline_intersects_polygon([(0.0, 0.0), (1.0, 0.0)], rings)  # disjoint
    # Inside a hole and never crossing its ring -> not in the polygon's area.
    holed = polygon_rings([square(0, 0, 10, 10), square(2, 2, 8, 8)])
    assert not polyline_intersects_polygon([(4.0, 5.0), (6.0, 5.0)], holed)
    # Crossing out of the hole re-enters the area.
    assert polyline_intersects_polygon([(4.0, 5.0), (9.0, 5.0)], holed)


# --------------------------------------------------------------------------- #
# Resolvers against the FakeNet
# --------------------------------------------------------------------------- #

def test_edges_near_point_filters_by_radius_and_sorts():
    fake = FakeNet(
        [
            FakeEdge("B", [(0.0, 5.0), (10.0, 5.0)]),
            FakeEdge("A", [(8.0, 0.0), (8.0, 10.0)]),
            FakeEdge("C", [(1.0, 9.0), (2.0, 9.0)]),
        ]
    )
    # A and B both pass through (8, 5); C's nearest point is (2, 9), sqrt(52) ~ 7.21 away.
    assert edges_near_point(fake, 8.0, 5.0, radius_m=0.5) == ["A", "B"]  # sorted by ID
    assert edges_near_point(fake, 8.0, 5.0, radius_m=8.0) == ["A", "B", "C"]
    assert edges_near_point(fake, 50.0, 50.0, radius_m=1.0) == []  # honest miss


@pytest.mark.parametrize("radius", [0.0, -5.0, float("nan")])
def test_edges_near_point_rejects_bad_radius(net, radius):
    with pytest.raises(ValueError):
        edges_near_point(net, 5.0, 5.0, radius_m=radius)


def test_edges_near_point_rejects_swapped_lonlat(net):
    with pytest.raises(ValueError):
        edges_near_point(net, 10.72, 122.56)  # lat in the lon slot


def test_edges_in_polygon_contained_crossing_and_miss(net):
    # Contains C_stub entirely, B_horizontal crosses it, A_vertical stays clear.
    poly = {"type": "Polygon", "coordinates": [square(0.5, 4.0, 3.0, 9.5)]}
    assert edges_in_polygon(net, poly) == ["B_horizontal", "C_stub"]
    # Far corner: covers nothing -> honest empty, no fallback guess.
    miss = {"type": "Polygon", "coordinates": [square(20.0, 20.0, 21.0, 21.0)]}
    assert edges_in_polygon(net, miss) == []


def test_edges_in_polygon_honours_holes(net):
    # Donut whose hole swallows C_stub: the stub must NOT resolve.
    poly = {
        "type": "Polygon",
        "coordinates": [square(0.0, 8.0, 4.0, 10.0), square(0.5, 8.5, 3.0, 9.5)],
    }
    assert edges_in_polygon(net, poly) == []


def test_edges_in_polygon_rejects_non_polygon(net):
    with pytest.raises(ValueError):
        edges_in_polygon(net, {"type": "Point", "coordinates": [1.0, 1.0]})


def test_resolve_geometry_dispatches_and_unions(net):
    point = {"type": "Point", "coordinates": [8.0, 5.0]}
    assert resolve_geometry(net, point, radius_m=0.5) == ["A_vertical", "B_horizontal"]

    feature = {"type": "Feature", "properties": {"name": "school"}, "geometry": point}
    assert resolve_geometry(net, feature, radius_m=0.5) == ["A_vertical", "B_horizontal"]

    fc = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": point},
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [square(0.5, 8.5, 3.0, 9.5)]},
            },
        ],
    }
    # Union across features, deduped, sorted.
    assert resolve_geometry(net, fc, radius_m=0.5) == ["A_vertical", "B_horizontal", "C_stub"]


def test_resolve_geometry_honest_empty_for_offnetwork(net):
    off = {"type": "Point", "coordinates": [80.0, 80.0]}
    assert resolve_geometry(net, off) == []


def test_resolve_geometry_raises_for_unsupported(net):
    with pytest.raises(ValueError):
        resolve_geometry(net, {"type": "LineString", "coordinates": [[0, 0], [1, 1]]})
