"""Tests for facility demand redistribution (demand_delta; glass-box PRD-F14, PRD-F5).

Pure Python — no SUMO, no Redis, no network. Everything here runs in bare mode
(`python -m pytest`) alongside the other non-SUMO kernel tests.
"""
import math

import pytest

from matrix_kernel.demand_delta import (
    DEFAULT_DEPART_WINDOW,
    EQUATION_ID,
    FACILITY_PROFILES,
    MIN_ORIGIN_DISTANCE_M,
    compute_demand_delta,
    geojson_centroid,
    haversine_m,
)
from matrix_kernel.personas import ILOILO_MODE_SHARE

# A 3,000-seat school in Molo, Iloilo City (the canonical facility scenario).
MOLO = (122.5446, 10.6969)
GEOM_POINT = {"type": "Point", "coordinates": [MOLO[0], MOLO[1]]}
PARAMS = {"facility_kind": "school", "capacity": 3000}


def test_glass_box_provenance_present():
    dd = compute_demand_delta(GEOM_POINT, PARAMS)
    assert dd.equation_id == EQUATION_ID
    assert "PROVISIONAL" in dd.equation_id          # honest: not yet in the Locked methods §3.1
    assert dd.input_dataset_ids == ["Calderon2014"]
    assert dd.references == ["Calderon2014"]
    # Every gravity constant must be declared with provenance (PRD-F14).
    text = "\n".join(dd.assumptions)
    for needle in ("trips_per_capacity", "redirected_fraction", "catchment_radius_m",
                   "gravity_exponent", "depart window", "Change Record"):
        assert needle in text, f"assumption missing for {needle!r}"
    # Uncalibrated heuristics -> at least the four gravity constants carry the honest label.
    assert sum("PROVISIONAL" in a for a in dd.assumptions) >= 4


def test_confidence_is_computed_low_and_directional():
    dd = compute_demand_delta(GEOM_POINT, PARAMS)
    # Calderon2014 alone is M, but heuristic method maturity caps the tier at L (methods §2).
    assert dd.confidence == "L"
    assert dd.directional   # renders "directional only", never as precision (PRD-F5)


def test_deterministic_given_seed():
    a = compute_demand_delta(GEOM_POINT, PARAMS, seed=7)
    b = compute_demand_delta(GEOM_POINT, PARAMS, seed=7)
    assert a == b
    c = compute_demand_delta(GEOM_POINT, PARAMS, seed=8)
    assert a.trips != c.trips


def test_seed_falls_back_to_parameters_then_default():
    via_params = compute_demand_delta(GEOM_POINT, {**PARAMS, "seed": 7})
    via_arg = compute_demand_delta(GEOM_POINT, PARAMS, seed=7)
    assert via_params.trips == via_arg.trips
    assert compute_demand_delta(GEOM_POINT, PARAMS).seed == 42


def test_trip_count_and_redirected_split():
    dd = compute_demand_delta(GEOM_POINT, PARAMS)
    school = FACILITY_PROFILES["school"]
    expected = round(3000 * school.trips_per_capacity)         # 2700
    assert dd.demand_trips_total == expected == len(dd.trips)
    assert dd.demand_scale == 1.0
    assert dd.n_redirected == round(expected * school.redirected_fraction)
    assert dd.n_induced == len(dd.trips) - dd.n_redirected
    assert dd.n_induced > 0


def test_origins_inside_catchment_and_beyond_min_distance():
    dd = compute_demand_delta(GEOM_POINT, PARAMS)
    for t in dd.trips:
        d = haversine_m(t.origin_lonlat, dd.facility_lonlat)
        assert MIN_ORIGIN_DISTANCE_M - 1.0 <= d <= dd.catchment_radius_m + 1.0


def test_gravity_decay_concentrates_origins_near_facility():
    dd = compute_demand_delta(GEOM_POINT, PARAMS)
    distances = sorted(haversine_m(t.origin_lonlat, dd.facility_lonlat) for t in dd.trips)
    median = distances[len(distances) // 2]
    # beta = 2 -> log-uniform distances: the median sits well inside half the catchment.
    assert median < dd.catchment_radius_m / 2


def test_destination_is_facility_centroid():
    dd = compute_demand_delta(GEOM_POINT, PARAMS)
    assert dd.facility_lonlat == MOLO
    assert all(t.dest_lonlat == MOLO for t in dd.trips)


def test_departures_inside_window_and_sorted():
    dd = compute_demand_delta(GEOM_POINT, PARAMS)
    assert dd.depart_window == DEFAULT_DEPART_WINDOW
    departs = [t.depart_s for t in dd.trips]
    assert departs == sorted(departs)
    assert all(dd.depart_window[0] <= s <= dd.depart_window[1] for s in departs)


def test_mode_hints_follow_iloilo_anchor():
    dd = compute_demand_delta(GEOM_POINT, PARAMS)
    counts: dict[str, int] = {}
    for t in dd.trips:
        assert t.mode_hint in ILOILO_MODE_SHARE
        counts[t.mode_hint] = counts.get(t.mode_hint, 0) + 1
    # Jeepney (55% anchor) must be the modal mode over ~2,700 draws.
    assert max(counts, key=counts.get) == "jeepney"


def test_polygon_feature_centroid():
    square = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[122.544, 10.696], [122.545, 10.696],
                             [122.545, 10.697], [122.544, 10.697],
                             [122.544, 10.696]]],   # closing duplicate must not bias it
        },
    }
    lon, lat = geojson_centroid(square)
    assert lon == pytest.approx(122.5445)
    assert lat == pytest.approx(10.6965)
    dd = compute_demand_delta(square, PARAMS)
    assert dd.facility_lonlat == pytest.approx((122.5445, 10.6965))


def test_lonlat_fallback_without_geometry():
    dd = compute_demand_delta(None, {**PARAMS, "facility_lonlat": [MOLO[0], MOLO[1]]})
    assert dd.facility_lonlat == MOLO


def test_overrides_respected_and_labeled():
    dd = compute_demand_delta(GEOM_POINT, {
        **PARAMS,
        "catchment_radius_m": 1500.0,
        "trips_per_capacity": 0.5,
        "depart_window": [0.0, 600.0],
    })
    assert dd.catchment_radius_m == 1500.0
    assert dd.demand_trips_total == 1500
    assert dd.depart_window == (0.0, 600.0)
    assert all(haversine_m(t.origin_lonlat, dd.facility_lonlat) <= 1501.0 for t in dd.trips)
    assert all(t.depart_s <= 600.0 for t in dd.trips)
    # Overrides are still provenance-labeled — just as overrides, not defaults (PRD-F14).
    overridden = [a for a in dd.assumptions if "caller override" in a]
    assert len(overridden) == 3


def test_max_trips_cap_sets_demand_scale():
    dd = compute_demand_delta(GEOM_POINT, {**PARAMS, "max_trips": 100})
    assert len(dd.trips) == 100
    assert dd.demand_trips_total == 2700
    assert dd.demand_scale == 27.0
    assert any("demand_scale" in a for a in dd.assumptions)


def test_max_trips_float_is_coerced_and_logged_consistently():
    dd = compute_demand_delta(GEOM_POINT, {**PARAMS, "max_trips": 100.9})
    assert len(dd.trips) == 101   # rounded, not truncated
    # The provenance line must state the value actually applied (PRD-F14).
    assert any("max_trips = 101" in a for a in dd.assumptions)


def test_market_and_terminal_profiles():
    market = compute_demand_delta(GEOM_POINT, {"facility_kind": "market", "capacity": 200})
    assert market.demand_trips_total == round(200 * FACILITY_PROFILES["market"].trips_per_capacity)
    terminal = compute_demand_delta(GEOM_POINT, {"facility_kind": "terminal", "capacity": 40})
    assert terminal.demand_trips_total == round(40 * FACILITY_PROFILES["terminal"].trips_per_capacity)
    assert terminal.catchment_radius_m == FACILITY_PROFILES["terminal"].catchment_radius_m


def test_as_dict_is_json_ready():
    dd = compute_demand_delta(GEOM_POINT, {**PARAMS, "max_trips": 10})
    d = dd.as_dict()
    assert d["equation_id"] == EQUATION_ID
    assert len(d["trips"]) == 10
    assert d["trips"][0]["mode_hint"] in ILOILO_MODE_SHARE


@pytest.mark.parametrize("geometry,params,match", [
    (GEOM_POINT, {"facility_kind": "stadium", "capacity": 100}, "unknown facility_kind"),
    (GEOM_POINT, {"facility_kind": "school", "capacity": 0}, "capacity"),
    (GEOM_POINT, {"facility_kind": "school", "capacity": 0.4}, "rounds to 0"),
    (GEOM_POINT, {"facility_kind": "school", "capacity": -5}, "capacity"),
    (GEOM_POINT, {"facility_kind": "school"}, "capacity"),
    (None, PARAMS, "no facility location"),
    (GEOM_POINT, {**PARAMS, "redirected_fraction": 1.5}, "redirected_fraction"),
    (GEOM_POINT, {**PARAMS, "depart_window": [600.0, 0.0]}, "depart_window"),
    (GEOM_POINT, {**PARAMS, "catchment_radius_m": 50.0}, "catchment_radius_m"),
    (GEOM_POINT, {**PARAMS, "gravity_exponent": 0.0}, "gravity_exponent"),
    (GEOM_POINT, {**PARAMS, "max_trips": 0}, "max_trips"),
    ({"type": "Point"}, PARAMS, "unsupported geometry|no coordinates"),
])
def test_validation_fails_fast(geometry, params, match):
    with pytest.raises(ValueError, match=match):
        compute_demand_delta(geometry, params)


def test_non_default_gravity_exponent_branches():
    # beta != 2 exercises the power-law inverse-CDF branch; origins stay in the catchment.
    dd = compute_demand_delta(GEOM_POINT, {**PARAMS, "gravity_exponent": 1.5, "max_trips": 200})
    for t in dd.trips:
        d = haversine_m(t.origin_lonlat, dd.facility_lonlat)
        assert MIN_ORIGIN_DISTANCE_M - 1.0 <= d <= dd.catchment_radius_m + 1.0
