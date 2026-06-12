"""Geometry engine -- GeoJSON -> SUMO edge IDs (pure resolvers; PRD-F14 honesty).

Planners drop arbitrary geometries on the map (a school footprint, a flood polygon,
a point of interest); the kernel needs the SUMO edges that geometry touches before it
can run a delta. ``resolve_geometry(net, geojson)`` is the single entrance:

    Point   -> edges strictly within ``radius_m`` (default 100 m) of the point
    Polygon -> edges whose centreline shape intersects or lies inside the polygon
    (+ Feature / FeatureCollection / GeometryCollection / Multi* wrappers)

Honesty contract (glass box, PRD-F14): a well-formed geometry that touches no edge
resolves to an EMPTY list -- never a silent fallback guess. Malformed GeoJSON
(unknown type, bad coordinates, the classic swapped lon/lat) raises ValueError
instead of quietly resolving to something.

The module imports no SUMO code at the top level: every resolver takes an already
loaded ``sumolib.net.Net`` (duck-typed -- it only needs ``convertLonLat2XY``,
``getEdges`` and ``getNeighboringEdges``), so the GeoJSON/planar helpers run on a
bare venv and only the sumolib-backed tests need the wheel. The engine is
city-agnostic (MATRIX.md §6): swap the net, not the code.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# Mirrors baseline.KERNEL_DATA/NET -- kept local so importing this module never pulls
# in the SUMO wheel (baseline imports sumo_env at module top; geometry stays pure).
KERNEL_DATA = Path(__file__).resolve().parent.parent / "data"
NET = KERNEL_DATA / "iloilo.net.xml"

Position = tuple[float, float]


# --------------------------------------------------------------------------- #
# GeoJSON parsing / validation (pure -- no SUMO, testable anywhere)
# --------------------------------------------------------------------------- #

def geometries(geojson: dict) -> list[dict]:
    """Flatten any supported GeoJSON object to its concrete Point/Polygon geometries.

    Accepts a bare ``Point``/``Polygon`` geometry, a ``Feature`` wrapper, a
    ``FeatureCollection``, a ``GeometryCollection``, or ``MultiPoint``/``MultiPolygon``
    (split into members). Anything else -- including a ``Feature`` with a null
    geometry -- raises ValueError: an unresolvable input is an error, not a miss.
    """
    if not isinstance(geojson, dict):
        raise ValueError(f"GeoJSON must be a dict, got {type(geojson).__name__}")
    gtype = geojson.get("type")
    if gtype == "FeatureCollection":
        feats = geojson.get("features")
        if not isinstance(feats, list) or not feats:
            raise ValueError("FeatureCollection without a non-empty 'features' list")
        return [g for f in feats for g in geometries(f)]
    if gtype == "Feature":
        geom = geojson.get("geometry")
        if geom is None:
            raise ValueError("Feature has a null geometry -- nothing to resolve")
        return geometries(geom)
    if gtype == "GeometryCollection":
        geoms = geojson.get("geometries")
        if not isinstance(geoms, list) or not geoms:
            raise ValueError("GeometryCollection without a non-empty 'geometries' list")
        return [g for m in geoms for g in geometries(m)]
    if gtype in ("MultiPoint", "MultiPolygon"):
        coords = geojson.get("coordinates")
        if not isinstance(coords, (list, tuple)) or not coords:
            raise ValueError(f"{gtype} without a non-empty 'coordinates' list")
        member = "Point" if gtype == "MultiPoint" else "Polygon"
        return [{"type": member, "coordinates": c} for c in coords]
    if gtype in ("Point", "Polygon"):
        if "coordinates" not in geojson:
            raise ValueError(f"{gtype} geometry without 'coordinates'")
        return [geojson]
    raise ValueError(
        f"unsupported GeoJSON type {gtype!r} -- the geometry engine resolves Point and "
        "Polygon (plus Feature/FeatureCollection/GeometryCollection/Multi* wrappers)"
    )


def _position(pos) -> Position:
    """Validate one GeoJSON position -> ``(lon, lat)``. Tolerates a trailing altitude.

    Out-of-range values raise -- the classic swapped lon/lat (Iloilo as
    ``[10.72, 122.56]``) must be an error, never a silent empty result.
    """
    if (
        not isinstance(pos, (list, tuple))
        or len(pos) < 2
        or not all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in pos[:2])
    ):
        raise ValueError(f"bad GeoJSON position {pos!r} (want [lon, lat])")
    lon, lat = float(pos[0]), float(pos[1])
    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        raise ValueError(f"position {pos!r} outside lon/lat range (swapped coordinates?)")
    return lon, lat


def polygon_rings(coordinates) -> list[list[Position]]:
    """Validate GeoJSON ``Polygon`` coordinates -> rings as closed ``(lon, lat)`` lists.

    Ring 0 is the exterior, the rest are holes (RFC 7946 §3.1.6). Unclosed rings are
    closed implicitly; a ring with fewer than 3 distinct positions raises ValueError.
    """
    if not isinstance(coordinates, (list, tuple)) or not coordinates:
        raise ValueError("Polygon needs a non-empty 'coordinates' list of rings")
    rings: list[list[Position]] = []
    for raw in coordinates:
        if not isinstance(raw, (list, tuple)):
            raise ValueError(f"bad Polygon ring {raw!r} (want a list of positions)")
        ring = [_position(p) for p in raw]
        if len(ring) >= 2 and ring[0] == ring[-1]:
            ring = ring[:-1]
        if len(set(ring)) < 3:
            raise ValueError("a Polygon ring needs at least 3 distinct positions")
        rings.append(ring + [ring[0]])  # stored closed: first == last
    return rings


# --------------------------------------------------------------------------- #
# Planar predicates (pure -- operate on already-projected XY metres)
# --------------------------------------------------------------------------- #

def _bbox(points: list[Position]) -> tuple[float, float, float, float]:
    """Axis-aligned bounding box ``(minx, miny, maxx, maxy)`` of a point list."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def point_in_ring(x: float, y: float, ring: list[Position]) -> bool:
    """Even-odd ray casting against one closed ring (first == last point)."""
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y):
            x_cross = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_cross:
                inside = not inside
    return inside


def point_in_polygon(x: float, y: float, rings: list[list[Position]]) -> bool:
    """True if (x, y) lies inside the exterior ring and outside every hole."""
    if not point_in_ring(x, y, rings[0]):
        return False
    return not any(point_in_ring(x, y, hole) for hole in rings[1:])


def _orient(p: Position, q: Position, r: Position) -> float:
    """Signed cross product: >0 left turn, <0 right turn, 0 collinear."""
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def _on_segment(p: Position, q: Position, r: Position) -> bool:
    """Given r collinear with segment pq: does r lie within pq's bounding box?"""
    return (
        min(p[0], q[0]) <= r[0] <= max(p[0], q[0])
        and min(p[1], q[1]) <= r[1] <= max(p[1], q[1])
    )


def _segments_intersect(p1: Position, p2: Position, q1: Position, q2: Position) -> bool:
    """True if segments p1p2 and q1q2 share any point (touching counts).

    The standard orientation test (CLRS 33.1) including the collinear special cases.
    """
    d1 = _orient(q1, q2, p1)
    d2 = _orient(q1, q2, p2)
    d3 = _orient(p1, p2, q1)
    d4 = _orient(p1, p2, q2)
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
        (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
    ):
        return True
    if d1 == 0 and _on_segment(q1, q2, p1):
        return True
    if d2 == 0 and _on_segment(q1, q2, p2):
        return True
    if d3 == 0 and _on_segment(p1, p2, q1):
        return True
    return d4 == 0 and _on_segment(p1, p2, q2)


def polyline_intersects_polygon(
    polyline: list[Position], rings: list[list[Position]]
) -> bool:
    """True if an open polyline touches the polygon's area.

    Either a polyline vertex lies inside the polygon, or some polyline segment crosses
    some ring segment -- hole rings included, because crossing a hole boundary means
    entering the polygon's actual area.
    """
    if any(point_in_polygon(x, y, rings) for x, y in polyline):
        return True
    for a, b in zip(polyline, polyline[1:]):
        for ring in rings:
            for c, d in zip(ring, ring[1:]):
                if _segments_intersect(a, b, c, d):
                    return True
    return False


# --------------------------------------------------------------------------- #
# Net-backed resolvers (take a loaded sumolib net; lon/lat in, edge IDs out)
# --------------------------------------------------------------------------- #

def load_net(path: str | Path = NET):
    """Read a SUMO net for the resolvers (cached -- the read is the slow part; the
    Iloilo pilot net has ~36k edges). Lazy-imports sumolib via sumo_env when the
    eclipse-sumo wheel is present, falling back to a standalone ``sumolib`` install,
    so importing this module stays SUMO-free.
    """
    # Normalize before the cache boundary so load_net(), load_net(NET) and a str
    # spelling of the same file share ONE cache entry (the net is ~42 MB on disk).
    return _read_net(str(Path(path).resolve()))


@lru_cache(maxsize=4)
def _read_net(path_str: str):
    try:
        from matrix_kernel import sumo_env  # noqa: F401  wires $SUMO_HOME/tools onto sys.path
    except ImportError:
        pass  # no eclipse-sumo wheel; a standalone `sumolib` package may still serve
    import sumolib

    if not Path(path_str).exists():
        raise FileNotFoundError(f"SUMO net {path_str} missing -- run build_network.py")
    return sumolib.net.readNet(path_str)


def edges_near_point(net, lon: float, lat: float, radius_m: float = 100.0) -> list[str]:
    """SUMO edge IDs strictly within ``radius_m`` metres of a lon/lat point.

    Sorted and deduped. ``[]`` is the honest miss for a point dropped off the network
    (PRD-F14) -- callers decide their own fallback. Raises ValueError on bad
    coordinates/radius and RuntimeError (sumolib) if the net has no geo-projection.
    """
    lon, lat = _position((lon, lat))
    if not radius_m > 0:  # also rejects NaN
        raise ValueError(f"radius_m must be > 0, got {radius_m!r}")
    x, y = net.convertLonLat2XY(lon, lat)
    return sorted({edge.getID() for edge, _dist in net.getNeighboringEdges(x, y, radius_m)})


def edges_in_polygon(net, polygon: dict) -> list[str]:
    """SUMO edge IDs whose centreline shape intersects or lies inside a GeoJSON Polygon.

    ``polygon`` is the geometry dict (``{"type": "Polygon", "coordinates": [...]}``),
    WGS84 lon/lat, holes honoured. Sorted and deduped; ``[]`` when the polygon covers
    no edge (honest miss, PRD-F14). Raises ValueError on malformed GeoJSON and
    RuntimeError (sumolib) if the net has no geo-projection.
    """
    if not isinstance(polygon, dict) or polygon.get("type") != "Polygon":
        raise ValueError("expected a GeoJSON Polygon geometry dict")
    rings_lonlat = polygon_rings(polygon.get("coordinates"))
    rings = [[net.convertLonLat2XY(lon, lat) for lon, lat in ring] for ring in rings_lonlat]
    minx, miny, maxx, maxy = _bbox(rings[0])
    hits: set[str] = set()
    for edge in net.getEdges():
        shape = edge.getShape()
        sminx, sminy, smaxx, smaxy = _bbox(shape)
        if sminx > maxx or smaxx < minx or sminy > maxy or smaxy < miny:
            continue  # cheap reject: disjoint bounding boxes
        if polyline_intersects_polygon(shape, rings):
            hits.add(edge.getID())
    return sorted(hits)


def resolve_geometry(net, geojson: dict, radius_m: float = 100.0) -> list[str]:
    """GeoJSON (Point/Polygon, wrappers tolerated) -> sorted SUMO edge IDs.

    The seam for ``runner.resolve_edges`` (a ``Scenario.geometry`` map-drop -> the
    affected edges). Dispatches each concrete geometry -- ``Point`` via
    :func:`edges_near_point` (``radius_m`` buffer), ``Polygon`` via
    :func:`edges_in_polygon` -- and returns the deduped, sorted union. ``[]`` only
    when every geometry is well-formed but touches no edge.
    """
    ids: set[str] = set()
    for geom in geometries(geojson):
        if geom["type"] == "Point":
            lon, lat = _position(geom["coordinates"])
            ids.update(edges_near_point(net, lon, lat, radius_m))
        else:  # "Polygon" -- geometries() admits nothing else
            ids.update(edges_in_polygon(net, geom))
    return sorted(ids)
