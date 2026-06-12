"""Facility demand redistribution — gravity-style trip deltas for new facilities (PRD-F1).

A `new_facility` scenario ("build a 3,000-seat school in Molo") must change TRAVEL DEMAND,
not road geometry. This module turns a facility (centroid + capacity + kind) into a
structured demand perturbation: trips drawn from a distance-decay catchment, each with an
origin, the facility destination, a depart second inside the AM-peak window, and a mode
hint sampled from the audited Iloilo mode-share anchor. The scenario runner applies the
perturbation downstream; this module never touches SUMO, sumolib, or Redis (pure Python +
stdlib math), and is deterministic given a seed (reproducibility, methods §7).

Glass box (PRD-F14): every constant is surfaced in `DemandDelta.assumptions` with its
provenance. The gravity constants are honestly labeled "PROVISIONAL — uncalibrated", so the
*computed* confidence is L — heuristic method maturity caps the tier (methods §2 worst-factor
rule) — and the output renders "directional only" (PRD-F5) until calibration lands. The
equation id is provisional too: facility gravity redistribution is NOT yet a row in the
Locked methods-matrix §3.1; promoting it to a real BEH-4 entry requires a Change Record.

Consumed by the scenario dispatcher as:

    delta = compute_demand_delta(scenario.geometry, scenario.parameters)

`Scenario.parameters` keys: `facility_kind` (school|market|terminal, required), `capacity`
(required, > 0), `facility_lonlat` ([lon, lat] fallback when geometry is None), and optional
overrides `catchment_radius_m`, `gravity_exponent`, `trips_per_capacity`,
`redirected_fraction`, `depart_window`, `max_trips`, `seed`.
"""
from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field
from typing import Sequence

from matrix_kernel.confidence import confidence_rubric
from matrix_kernel.personas import ILOILO_MODE_SHARE
from matrix_kernel.results import Confidence

EQUATION_ID = "BEH-4-PROVISIONAL"   # not in Locked methods §3.1 yet — promotion needs a CR
INPUT_DATASET_IDS = ["Calderon2014"]  # the mode-share anchor is the only dataset consumed
REFERENCES = ["Calderon2014"]

# Heuristic, uncalibrated gravity model -> method maturity is Low (methods §2: the worst
# factor caps the tier, and "heuristic / unvalidated" is the Low row of the rubric).
_METHOD_MATURITY: Confidence = "L"
_RANK: dict[Confidence, int] = {"L": 1, "M": 2, "H": 3}
_BY_RANK: dict[int, Confidence] = {1: "L", 2: "M", 3: "H"}

# Mirrors baseline.SIM_END (900 s AM-peak slice). Deliberately NOT imported from
# matrix_kernel.baseline — its import chain pulls sumo_env/eclipse-sumo and this module
# must stay importable on a bare venv.
DEFAULT_DEPART_WINDOW: tuple[float, float] = (0.0, 900.0)

# Minimum origin distance: the d^(1-beta) origin density diverges as d -> 0, so sampling
# starts here. PROVISIONAL — uncalibrated.
MIN_ORIGIN_DISTANCE_M = 100.0

# Classic spatial-interaction decay exponent (Wilson-type gravity family).
# PROVISIONAL for Iloilo — uncalibrated against any local travel survey.
DEFAULT_GRAVITY_EXPONENT = 2.0

# Latency-budget guard (90 s end-to-end, MATRIX.md §6): cap emitted trips and scale instead.
DEFAULT_MAX_TRIPS = 5000

_R_EARTH_M = 6371008.8  # IUGG mean Earth radius


@dataclass(frozen=True)
class FacilityProfile:
    """Per-kind default constants. Every value is PROVISIONAL — uncalibrated heuristics,
    declared in assumptions and capping confidence at L until calibration lands."""

    trips_per_capacity: float   # AM-window trips generated per unit of capacity
    redirected_fraction: float  # share redirected from existing travel (vs induced net-new)
    catchment_radius_m: float   # gravity catchment around the facility
    capacity_unit: str          # what "capacity" counts, for honest assumption text


FACILITY_PROFILES: dict[str, FacilityProfile] = {
    # ~1 AM inbound trip per enrolled seat x ~0.9 attendance proxy; enrollment mostly
    # transfers from existing schools; walk/short-ride school catchment heuristic.
    "school": FacilityProfile(0.9, 0.8, 3000.0, "seat"),
    # Shopper visits per stall per AM window; demand partly shifts from existing markets.
    "market": FacilityProfile(1.2, 0.6, 2000.0, "stall"),
    # Boardings per bay per AM window; terminals mostly re-route existing transit trips.
    "terminal": FacilityProfile(4.0, 0.7, 5000.0, "bay"),
}


@dataclass(frozen=True)
class TripDelta:
    """One perturbation trip. `redirected=True` means it replaces an existing baseline trip
    (retarget, not net-new travel); `redirected=False` means induced net-new demand."""

    origin_lonlat: tuple[float, float]   # (lon, lat) sampled from the gravity catchment
    dest_lonlat: tuple[float, float]     # (lon, lat) = the facility centroid
    depart_s: float                      # depart second inside the AM-peak window
    mode_hint: str                       # sampled from the Iloilo mode-share anchor
    redirected: bool


@dataclass(frozen=True)
class DemandDelta:
    """The structured demand perturbation a `new_facility` scenario applies (glass-box)."""

    facility_kind: str
    facility_lonlat: tuple[float, float]
    capacity: int
    trips: list[TripDelta]                # sorted by depart_s
    demand_trips_total: int               # round(capacity * trips_per_capacity)
    demand_scale: float                   # demand_trips_total / len(trips); 1.0 unless capped
    redirected_fraction: float
    catchment_radius_m: float
    gravity_exponent: float
    trips_per_capacity: float
    depart_window: tuple[float, float]
    seed: int
    equation_id: str
    input_dataset_ids: list[str]
    confidence: Confidence                # computed (rubric + method-maturity cap), never guessed
    unit: str = "trips/window"
    references: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    @property
    def n_redirected(self) -> int:
        return sum(1 for t in self.trips if t.redirected)

    @property
    def n_induced(self) -> int:
        return len(self.trips) - self.n_redirected

    @property
    def directional(self) -> bool:
        """Low confidence renders 'directional only', never as precision (PRD-F5)."""
        return self.confidence == "L"

    def as_dict(self) -> dict:
        """JSON-ready form for the API/Inspect layer."""
        return asdict(self)

    def __post_init__(self) -> None:
        # Glass-box invariants — fail fast if provenance is missing (PRD-F14).
        if not self.equation_id:
            raise ValueError("DemandDelta: missing equation_id (glass-box, PRD-F14)")
        if not self.input_dataset_ids:
            raise ValueError("DemandDelta: missing input_dataset_ids (glass-box, PRD-F14)")
        if not self.assumptions:
            raise ValueError("DemandDelta: missing assumptions (glass-box, PRD-F14)")
        if not 0.0 <= self.redirected_fraction <= 1.0:
            raise ValueError(f"DemandDelta: redirected_fraction {self.redirected_fraction} outside [0, 1]")
        lo, hi = self.depart_window
        if lo > hi:
            raise ValueError(f"DemandDelta: inverted depart_window ({lo} > {hi})")


# ── geometry helpers (tiny + local; the kernel-wide GeoJSON->edges resolver is a separate unit) ──

def geojson_centroid(geojson: dict) -> tuple[float, float]:
    """(lon, lat) vertex-average centroid of a GeoJSON Geometry/Feature/FeatureCollection.

    Adequate at facility-footprint scale; Polygon uses the exterior ring with the closing
    duplicate vertex dropped so it does not bias the average."""
    pts = _positions(geojson)
    if not pts:
        raise ValueError("geojson_centroid: geometry has no coordinates")
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _positions(geom: dict) -> list[tuple[float, float]]:
    gtype = geom.get("type")
    if gtype == "Feature":
        return _positions(geom["geometry"])
    if gtype == "FeatureCollection":
        return [p for f in geom["features"] for p in _positions(f)]
    if gtype == "GeometryCollection":
        return [p for g in geom["geometries"] for p in _positions(g)]
    coords = geom.get("coordinates")
    if coords is None:
        raise ValueError(f"geojson_centroid: unsupported geometry {gtype!r}")
    if gtype == "Point":
        return [(float(coords[0]), float(coords[1]))]
    if gtype in ("MultiPoint", "LineString"):
        return [(float(p[0]), float(p[1])) for p in coords]
    if gtype == "MultiLineString":
        return [(float(p[0]), float(p[1])) for line in coords for p in line]
    if gtype == "Polygon":
        return _ring_positions(coords[0])
    if gtype == "MultiPolygon":
        return [p for poly in coords for p in _ring_positions(poly[0])]
    raise ValueError(f"geojson_centroid: unsupported geometry {gtype!r}")


def _ring_positions(ring: list) -> list[tuple[float, float]]:
    pts = [(float(p[0]), float(p[1])) for p in ring]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]  # drop the GeoJSON closing duplicate
    return pts


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in meters between two (lon, lat) points."""
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2.0 * _R_EARTH_M * math.asin(math.sqrt(h))


def _destination(lonlat: tuple[float, float], distance_m: float,
                 bearing_rad: float) -> tuple[float, float]:
    """Spherical destination point: start (lon, lat) + distance along a bearing."""
    lon1, lat1 = math.radians(lonlat[0]), math.radians(lonlat[1])
    d = distance_m / _R_EARTH_M
    lat2 = math.asin(math.sin(lat1) * math.cos(d)
                     + math.cos(lat1) * math.sin(d) * math.cos(bearing_rad))
    lon2 = lon1 + math.atan2(math.sin(bearing_rad) * math.sin(d) * math.cos(lat1),
                             math.cos(d) - math.sin(lat1) * math.sin(lat2))
    return (math.degrees(lon2), math.degrees(lat2))


# ── gravity sampling ──

def _sample_distance(rng: random.Random, d_min: float, radius: float, beta: float) -> float:
    """Inverse-CDF draw of an origin distance on [d_min, radius].

    Trip attraction decays as d^-beta and producers in a ring grow as d (uniform density),
    so the origin-distance density is proportional to d^(1-beta). For beta == 2 the CDF is
    logarithmic; otherwise it is the power-law form with exponent p = 2 - beta."""
    u = rng.random()
    p = 2.0 - beta
    if abs(p) < 1e-9:
        return d_min * (radius / d_min) ** u
    return (d_min ** p + u * (radius ** p - d_min ** p)) ** (1.0 / p)


def _computed_confidence(input_dataset_ids: Sequence[str]) -> Confidence:
    """Worst factor caps the tier (methods §2): the dataset rubric AND the method maturity.
    The gravity model is heuristic/uncalibrated, so the method factor is L until the
    calibration ledger says otherwise — computed, never guessed."""
    data_tier = confidence_rubric(input_dataset_ids)
    return _BY_RANK[min(_RANK[data_tier], _RANK[_METHOD_MATURITY])]


# ── public entry point ──

def compute_demand_delta(geometry: dict | None, parameters: dict,
                         seed: int | None = None) -> DemandDelta:
    """Facility (geometry + parameters, as carried by a `new_facility` Scenario) -> DemandDelta.

    `geometry` is GeoJSON (Point/Polygon/Feature/...); when None, `parameters["facility_lonlat"]`
    ([lon, lat]) is the fallback. `seed` (argument > parameters["seed"] > 42) makes the draw
    deterministic. Raises ValueError on unknown kinds or unusable parameters — fail fast,
    never guess constants for an unknown facility (glass-box, PRD-F14)."""
    kind = parameters.get("facility_kind")
    if kind not in FACILITY_PROFILES:
        raise ValueError(
            f"compute_demand_delta: unknown facility_kind {kind!r} "
            f"(known: {sorted(FACILITY_PROFILES)}); refusing to guess constants (PRD-F14)")
    profile = FACILITY_PROFILES[kind]

    raw_capacity = parameters.get("capacity")
    if not isinstance(raw_capacity, (int, float)) or isinstance(raw_capacity, bool) or raw_capacity <= 0:
        raise ValueError(f"compute_demand_delta: capacity must be a number > 0, got {raw_capacity!r}")
    capacity = int(round(raw_capacity))
    if capacity < 1:
        raise ValueError(
            f"compute_demand_delta: capacity rounds to 0 (got {raw_capacity!r}); "
            f"need at least 1 {profile.capacity_unit}")

    facility = _resolve_facility_lonlat(geometry, parameters)
    if seed is None:
        seed = int(parameters.get("seed", 42))

    # Resolve each constant: caller override (Scenario.parameters) beats the PROVISIONAL
    # default; either way the provenance line lands in `assumptions`.
    assumptions: list[str] = [
        f"equation {EQUATION_ID}: facility gravity redistribution is not yet a row in the "
        "Locked methods-matrix §3.1 — promotion to BEH-4 requires a Change Record",
    ]
    tpc = _resolve_constant(parameters, "trips_per_capacity", profile.trips_per_capacity,
                            f"trips per {profile.capacity_unit} per AM window, "
                            f"{kind} default — PROVISIONAL, uncalibrated", assumptions)
    redirected_fraction = _resolve_constant(
        parameters, "redirected_fraction", profile.redirected_fraction,
        f"share redirected from existing travel vs induced net-new, "
        f"{kind} default — PROVISIONAL, uncalibrated", assumptions)
    radius = _resolve_constant(parameters, "catchment_radius_m", profile.catchment_radius_m,
                               f"gravity catchment, {kind} default — PROVISIONAL, uncalibrated",
                               assumptions)
    beta = _resolve_constant(parameters, "gravity_exponent", DEFAULT_GRAVITY_EXPONENT,
                             "Wilson-type spatial-interaction decay — PROVISIONAL for Iloilo, "
                             "uncalibrated", assumptions)
    # Coerce to int BEFORE logging so the provenance line matches the value actually applied.
    max_trips = int(round(float(parameters.get("max_trips", DEFAULT_MAX_TRIPS))))
    assumptions.append(
        f"max_trips = {max_trips} (caller override via Scenario.parameters)"
        if "max_trips" in parameters else
        f"max_trips = {max_trips} (latency-budget cap; 90 s end-to-end, MATRIX.md §6)")
    window = _resolve_window(parameters, assumptions)

    if tpc <= 0:
        raise ValueError(f"compute_demand_delta: trips_per_capacity must be > 0, got {tpc}")
    if not 0.0 <= redirected_fraction <= 1.0:
        raise ValueError(
            f"compute_demand_delta: redirected_fraction {redirected_fraction} outside [0, 1]")
    if radius <= MIN_ORIGIN_DISTANCE_M:
        raise ValueError(
            f"compute_demand_delta: catchment_radius_m {radius} must exceed the "
            f"{MIN_ORIGIN_DISTANCE_M} m minimum origin distance")
    if beta <= 0:
        raise ValueError(f"compute_demand_delta: gravity_exponent must be > 0, got {beta}")
    if max_trips < 1:
        raise ValueError(f"compute_demand_delta: max_trips must be >= 1, got {max_trips}")

    assumptions += [
        f"minimum origin distance = {MIN_ORIGIN_DISTANCE_M:.0f} m (avoids the d->0 "
        "singularity of the d^(1-beta) origin density) — PROVISIONAL",
        "origins sampled assuming uniform population density in the catchment "
        "(WorldPop-weighted sampling is a fidelity upgrade)",
        "mode_hint drawn from the Iloilo mode-share anchor (Calderon2014-derived); "
        "facility-specific mode profiles uncalibrated",
        "all trips are inbound (origin -> facility); the return leg falls outside the "
        "AM-peak window",
    ]

    demand_trips_total = round(capacity * tpc)
    n_emit = min(demand_trips_total, max_trips)
    demand_scale = (demand_trips_total / n_emit) if n_emit else 1.0
    if n_emit < demand_trips_total:
        assumptions.append(
            f"emitted {n_emit} of {demand_trips_total} trips (max_trips cap); "
            f"multiply applied counts by demand_scale = {demand_scale:.3f}")

    rng = random.Random(seed)
    modes, weights = list(ILOILO_MODE_SHARE), list(ILOILO_MODE_SHARE.values())
    n_redirected = round(n_emit * redirected_fraction)
    trips: list[TripDelta] = []
    for i in range(n_emit):
        distance = _sample_distance(rng, MIN_ORIGIN_DISTANCE_M, radius, beta)
        bearing = rng.uniform(0.0, 2.0 * math.pi)
        trips.append(TripDelta(
            origin_lonlat=_destination(facility, distance, bearing),
            dest_lonlat=facility,
            depart_s=rng.uniform(window[0], window[1]),
            mode_hint=rng.choices(modes, weights=weights)[0],
            redirected=i < n_redirected,
        ))
    trips.sort(key=lambda t: t.depart_s)

    return DemandDelta(
        facility_kind=kind,
        facility_lonlat=facility,
        capacity=capacity,
        trips=trips,
        demand_trips_total=demand_trips_total,
        demand_scale=demand_scale,
        redirected_fraction=redirected_fraction,
        catchment_radius_m=radius,
        gravity_exponent=beta,
        trips_per_capacity=tpc,
        depart_window=window,
        seed=seed,
        equation_id=EQUATION_ID,
        input_dataset_ids=list(INPUT_DATASET_IDS),
        confidence=_computed_confidence(INPUT_DATASET_IDS),
        references=list(REFERENCES),
        assumptions=assumptions,
    )


def _resolve_facility_lonlat(geometry: dict | None, parameters: dict) -> tuple[float, float]:
    if geometry is not None:
        return geojson_centroid(geometry)
    lonlat = parameters.get("facility_lonlat")
    if (isinstance(lonlat, (list, tuple)) and len(lonlat) == 2
            and all(isinstance(c, (int, float)) for c in lonlat)):
        return (float(lonlat[0]), float(lonlat[1]))
    raise ValueError(
        "compute_demand_delta: no facility location — pass GeoJSON `geometry` or "
        "parameters['facility_lonlat'] = [lon, lat]")


def _resolve_constant(parameters: dict, name: str, default: float, provenance: str,
                      assumptions: list[str]) -> float:
    """Caller override beats the default; either way the value + its provenance is declared."""
    if name in parameters:
        value = float(parameters[name])
        assumptions.append(f"{name} = {value:g} (caller override via Scenario.parameters)")
    else:
        value = default
        assumptions.append(f"{name} = {value:g} ({provenance})")
    return value


def _resolve_window(parameters: dict, assumptions: list[str]) -> tuple[float, float]:
    raw = parameters.get("depart_window")
    if raw is not None:
        if not (isinstance(raw, (list, tuple)) and len(raw) == 2):
            raise ValueError(f"compute_demand_delta: depart_window must be [start_s, end_s], got {raw!r}")
        window = (float(raw[0]), float(raw[1]))
        if window[0] < 0 or window[0] > window[1]:
            raise ValueError(f"compute_demand_delta: bad depart_window {window}")
        assumptions.append(
            f"depart window = [{window[0]:g}, {window[1]:g}] s (caller override via Scenario.parameters)")
        return window
    window = DEFAULT_DEPART_WINDOW
    assumptions.append(
        f"depart window = [{window[0]:g}, {window[1]:g}] s — mirrors the kernel's 900 s "
        "AM-peak baseline slice (not imported; this module stays SUMO-free)")
    return window
