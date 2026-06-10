"""Scenario v2 model + intervention dispatch unit tests.

matrix_kernel.scenario is deliberately SUMO-free (handlers receive the traci module as an
argument), so these run in bare mode -- no importorskip needed. The fakes mirror the TraCI
surface the handlers use, verified against eclipse-sumo 1.27.0: edge.getLaneNumber,
edge.setMaxSpeed, lane.setDisallowed, lane.getMaxSpeed, lane.setMaxSpeed.
"""
import pytest

from matrix_kernel.scenario import (
    INTERVENTION_TYPES,
    KPH_TO_MS,
    Scenario,
    apply_intervention,
)


class FakeTraCIException(Exception):
    pass


class _FakeLane:
    def __init__(self, speeds=None):
        self.speeds = dict(speeds or {})   # lane id -> max speed m/s
        self.disallowed: dict[str, list] = {}

    def setDisallowed(self, lane_id, classes):
        self.disallowed[lane_id] = list(classes)

    def getMaxSpeed(self, lane_id):
        return self.speeds[lane_id]

    def setMaxSpeed(self, lane_id, speed):
        self.speeds[lane_id] = speed


class _FakeEdge:
    def __init__(self, lanes, fail=()):
        self.lanes = dict(lanes)           # edge id -> lane count
        self.max_speed: dict[str, float] = {}
        self.fail = set(fail)              # edge ids that raise (unknown edge etc.)

    def getLaneNumber(self, edge_id):
        if edge_id in self.fail:
            raise FakeTraCIException(edge_id)
        return self.lanes[edge_id]

    def setMaxSpeed(self, edge_id, speed):
        if edge_id in self.fail:
            raise FakeTraCIException(edge_id)
        self.max_speed[edge_id] = speed


class FakeTraci:
    TraCIException = FakeTraCIException

    def __init__(self, lanes, speeds=None, fail=()):
        self.edge = _FakeEdge(lanes, fail=fail)
        self.lane = _FakeLane(speeds)


# ---------------------------------------------------------------- Scenario model

def test_v1_positional_construction_is_a_lane_closure():
    """Back-compat: existing call sites construct positionally with corridor/lanes_closed."""
    sc = Scenario("s1", "close a lane on Diversion Rd", "diversion", 2)
    assert sc.corridor == "diversion"
    assert sc.lanes_closed == 2
    assert sc.intervention_type == "lane_closure"
    assert sc.geometry is None
    assert sc.parameters == {}
    assert sc.effective_location == "diversion"
    assert sc.effective_parameters() == {"lanes_closed": 2}


def test_v2_location_wins_over_corridor():
    sc = Scenario("s1", "d", corridor="diversion", location="molo")
    assert sc.effective_location == "molo"


def test_parameters_override_legacy_lanes_closed():
    sc = Scenario("s1", "d", lanes_closed=1, parameters={"lanes_closed": 3})
    assert sc.effective_parameters() == {"lanes_closed": 3}


def test_none_parameters_do_not_clobber_defaults():
    sc = Scenario("s1", "d", intervention_type="speed_change",
                  parameters={"max_speed_kph": None})
    assert sc.effective_parameters()["max_speed_kph"] == 30.0


def test_unknown_intervention_type_rejected_at_construction():
    with pytest.raises(ValueError, match="teleportation"):
        Scenario("s1", "d", intervention_type="teleportation")


def test_dispatch_rejects_unknown_type():
    class _Stub:  # bypasses Scenario validation to hit the dispatcher's own guard
        intervention_type = "teleportation"

    with pytest.raises(ValueError, match="teleportation"):
        apply_intervention(FakeTraci({}), _Stub(), [])


# ---------------------------------------------------------------- handlers

def test_lane_closure_closes_min_lanes_and_records_edit():
    fake = FakeTraci({"A": 2, "B": 1})
    sc = Scenario("s1", "d", corridor="x", lanes_closed=2)
    applied = apply_intervention(fake, sc, ["A", "B"])

    assert set(fake.lane.disallowed) == {"A_0", "A_1", "B_0"}  # min(2, nlanes) per edge
    assert all(v == ["passenger"] for v in fake.lane.disallowed.values())
    assert applied["intervention_type"] == "lane_closure"
    assert applied["edges"] == ["A", "B"]
    assert applied["edge_lanes"] == {"A": 2, "B": 1}
    assert applied["parameters"] == {"lanes_closed": 2}
    assert applied["lanes_closed_legacy"] == 2


def test_full_closure_closes_every_lane():
    fake = FakeTraci({"A": 3, "B": 1})
    sc = Scenario("s1", "flooded road", intervention_type="full_closure", location="x")
    applied = apply_intervention(fake, sc, ["A", "B"])

    assert set(fake.lane.disallowed) == {"A_0", "A_1", "A_2", "B_0"}
    assert applied["intervention_type"] == "full_closure"
    assert applied["lanes_closed_legacy"] == 3  # max lane count among affected edges
    assert applied["edge_lanes"] == {"A": 3, "B": 1}


def test_speed_change_sets_edge_speed_in_ms():
    fake = FakeTraci({"A": 2})
    sc = Scenario("s1", "school zone", intervention_type="speed_change",
                  location="x", parameters={"max_speed_kph": 30.0})
    applied = apply_intervention(fake, sc, ["A"])

    assert fake.edge.max_speed["A"] == pytest.approx(30.0 * KPH_TO_MS, abs=1e-3)
    assert applied["parameters"]["max_speed_kph"] == 30.0
    assert applied["parameters"]["max_speed_ms"] == pytest.approx(8.333, abs=1e-3)
    assert applied["lanes_closed_legacy"] == 0
    assert fake.lane.disallowed == {}  # nothing closed


def test_capacity_change_scales_lane_speeds_and_declares_proxy():
    fake = FakeTraci({"A": 2}, speeds={"A_0": 10.0, "A_1": 12.0})
    sc = Scenario("s1", "widen road", intervention_type="capacity_change",
                  location="x", parameters={"capacity_factor": 1.5})
    applied = apply_intervention(fake, sc, ["A"])

    assert fake.lane.speeds == {"A_0": 15.0, "A_1": 18.0}
    assert applied["parameters"] == {"capacity_factor": 1.5}
    assert applied["lane_speeds_ms"] == {"A_0": [10.0, 15.0], "A_1": [12.0, 18.0]}
    assert any("PROXY" in a for a in applied["assumptions"])  # honest about the speed proxy
    assert applied["lanes_closed_legacy"] == 0


def test_traci_error_skips_edge_but_applies_rest():
    fake = FakeTraci({"B": 1}, fail={"A"})
    sc = Scenario("s1", "d", corridor="x", lanes_closed=1)
    applied = apply_intervention(fake, sc, ["A", "B"])

    assert applied["edges"] == ["B"]
    assert "A" not in applied["edge_lanes"]
    assert set(fake.lane.disallowed) == {"B_0"}


def test_every_declared_type_has_a_handler_and_provenance_keys():
    fake_factory = lambda: FakeTraci({"A": 1}, speeds={"A_0": 10.0})
    for itype in INTERVENTION_TYPES:
        applied = apply_intervention(fake_factory(), Scenario("s", "d", intervention_type=itype), ["A"])
        # every dispatch record carries the keys Trajectory.meta provenance relies on
        for key in ("intervention_type", "edges", "edge_lanes", "parameters",
                    "traci_calls", "assumptions", "lanes_closed_legacy"):
            assert key in applied, f"{itype} missing {key}"
        assert applied["intervention_type"] == itype
