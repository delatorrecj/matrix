"""Tests for BEH-4 facility injection (mock TraCI)."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from matrix_kernel.demand_delta import DemandDelta, TripDelta
from matrix_kernel.facility_injection import inject_facility_demand


def _fake_net():
    net = MagicMock()

    def neighboring(xy, lon, lat):
        edge = MagicMock()
        edge.getID.return_value = "edge_a" if lon < 122.565 else "edge_b"
        return [(edge, 1.0)]

    def convert(lon, lat):
        return (lon, lat)

    net.convertLonLat2XY.side_effect = convert

    def get_neighboring(x, y, r=150):
        # x,y are from convertLonLat2XY — we encoded lon in x for the test
        edge = MagicMock()
        edge.getID.return_value = "edge_a" if x < 122.565 else "edge_b"
        return [(edge, 1.0)]

    net.getNeighboringEdges.side_effect = get_neighboring
    return net


def _trip(depart: float) -> TripDelta:
    return TripDelta(
        origin_lonlat=(122.56, 10.72),
        dest_lonlat=(122.57, 10.73),
        depart_s=depart,
        mode_hint="jeepney",
        redirected=False,
    )


def _delta(trips: list[TripDelta]) -> DemandDelta:
    return DemandDelta(
        facility_kind="school",
        facility_lonlat=(122.57, 10.73),
        capacity=3000,
        trips=trips,
        demand_trips_total=len(trips),
        demand_scale=1.0,
        redirected_fraction=0.0,
        catchment_radius_m=1500.0,
        gravity_exponent=2.0,
        trips_per_capacity=0.01,
        depart_window=(25200.0, 32400.0),
        seed=42,
        equation_id="BEH-4",
        input_dataset_ids=["OSM-ILO"],
        confidence="L",
        assumptions=["test"],
    )


def test_inject_facility_demand_schedules_vehicles():
    traci = MagicMock()
    route = SimpleNamespace(edges=["edge_a", "edge_b"])
    traci.simulation.findRoute.return_value = route

    delta = _delta([_trip(100.0), _trip(200.0)])

    record = inject_facility_demand(traci, _fake_net(), delta, max_inject=10)
    assert record["injected_vehicles"] == 2
    assert record["demand_trips_total"] == 2
    assert traci.vehicle.add.call_count == 2
    assert traci.route.add.call_count == 2


def test_inject_facility_demand_respects_max_inject():
    traci = MagicMock()
    traci.simulation.findRoute.return_value = SimpleNamespace(edges=["e1", "e2"])

    delta = _delta([_trip(float(i)) for i in range(5)])

    record = inject_facility_demand(traci, _fake_net(), delta, max_inject=2)
    assert record["injected_vehicles"] == 2
    assert traci.vehicle.add.call_count == 2
