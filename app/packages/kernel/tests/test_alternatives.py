"""Tests for alternatives.py rule-based alternative generation."""
from matrix_kernel.alternatives import generate_alternatives
from matrix_kernel.results import DimensionResult
from matrix_kernel.scenario import Scenario


def test_generate_alternatives_for_full_closure():
    primary = Scenario(
        scenario_id="sc-primary",
        description="Full closure of JM Basa St",
        corridor="edge1 edge2",
        lanes_closed=2,
        intervention_type="full_closure",
        location="JM Basa St",
        geometry=None,
        parameters={},
    )
    r1 = DimensionResult(
        dimension="social",
        metric="Displaced vendors",
        equation_id="SOC-2",
        value=24.0,
        range=(20.0, 28.0),
        unit="people",
        confidence="M",
        input_dataset_ids=["OSM"],
        references=[],
        assumptions=[],
    )
    alts = generate_alternatives(primary, [r1])
    assert len(alts) == 2
    assert alts[0].scenario.intervention_type == "lane_closure"
    assert alts[0].scenario.lanes_closed == 1
    assert "JM Basa St" in alts[0].scenario.description
    assert alts[0].triggered_by == "SOC-2"
    assert alts[1].scenario.intervention_type == "speed_change"


def test_generate_alternatives_for_lane_closure():
    primary = Scenario(
        scenario_id="sc-lane",
        description="Close 1 lane on JM Basa St",
        corridor="edge1",
        lanes_closed=1,
        intervention_type="lane_closure",
        location="JM Basa St",
        geometry=None,
        parameters={"lanes_closed": 1},
    )
    alts = generate_alternatives(primary, [])
    assert len(alts) >= 1
    assert alts[0].scenario.intervention_type == "speed_change"


def test_generate_alternatives_for_speed_change():
    primary = Scenario(
        scenario_id="sc-speed",
        description="30 kph limit on JM Basa St",
        corridor="edge1",
        lanes_closed=0,
        intervention_type="speed_change",
        location="JM Basa St",
        geometry=None,
        parameters={"max_speed_kph": 30.0},
    )
    alts = generate_alternatives(primary, [])
    assert len(alts) == 1
    assert alts[0].scenario.intervention_type == "capacity_change"


def test_generate_alternatives_for_capacity_change():
    primary = Scenario(
        scenario_id="sc-cap",
        description="Widen JM Basa St",
        corridor="edge1",
        lanes_closed=0,
        intervention_type="capacity_change",
        location="JM Basa St",
        geometry=None,
        parameters={"capacity_factor": 1.3},
    )
    alts = generate_alternatives(primary, [])
    assert len(alts) == 1
    assert alts[0].scenario.intervention_type == "speed_change"

