"""Orchestrator NL->Scenario mapping tests (no network -- a fake genai client is injected).

The Gemini call itself is not under test (that's an eval, not a unit test); what is under
test is the deterministic mapping ScenarioSchema -> Scenario v2: intervention typing,
parameter assembly, the legacy corridor back-fill, and the ambiguity guard.
"""
import pytest

# orchestrator imports google-genai + pydantic at module top; skip cleanly in bare envs.
pytest.importorskip("google.genai", reason="google-genai not installed; run `uv sync` in app/packages/kernel")

from matrix_kernel.orchestrator import ScenarioSchema, parse_scenario


class _FakeResponse:
    def __init__(self, parsed):
        self.parsed = parsed
        self.text = ""


class _FakeModels:
    def __init__(self, parsed):
        self._parsed = parsed

    def generate_content(self, **kwargs):
        return _FakeResponse(self._parsed)


class FakeClient:
    def __init__(self, parsed):
        self.models = _FakeModels(parsed)


def test_lane_closure_maps_with_legacy_backfill():
    schema = ScenarioSchema(
        description="Close one lane on Diversion Rd for roadworks",
        intervention_type="lane_closure", location="Diversion Rd",
        lanes_closed=1, is_ambiguous=False,
    )
    sc = parse_scenario("roadworks on Diversion Rd", client=FakeClient(schema))
    assert sc.intervention_type == "lane_closure"
    assert sc.location == "Diversion Rd"
    assert sc.corridor == "Diversion Rd"      # v1 channel back-filled for /scenario consumers
    assert sc.lanes_closed == 1
    assert sc.parameters == {"lanes_closed": 1}
    assert sc.geometry is None
    assert sc.scenario_id                      # a uuid was assigned


def test_speed_change_carries_stated_speed_only():
    schema = ScenarioSchema(
        description="30 km/h school zone on JM Basa St",
        intervention_type="speed_change", location="JM Basa",
        max_speed_kph=30.0, is_ambiguous=False,
    )
    sc = parse_scenario("school zone JM Basa 30kph", client=FakeClient(schema))
    assert sc.intervention_type == "speed_change"
    assert sc.parameters == {"max_speed_kph": 30.0}


def test_speed_change_without_stated_speed_leaves_parameters_empty():
    """The LLM never invents a number (PRD-F14); the kernel default is applied -- and
    recorded -- downstream."""
    schema = ScenarioSchema(
        description="Traffic calming in Molo", intervention_type="speed_change",
        location="Molo", max_speed_kph=None, is_ambiguous=False,
    )
    sc = parse_scenario("calm traffic in Molo", client=FakeClient(schema))
    assert sc.parameters == {}
    assert sc.effective_parameters()["max_speed_kph"] == 30.0  # documented kernel default


def test_full_closure_maps_with_no_parameters():
    schema = ScenarioSchema(
        description="JM Basa closed for Dinagyang", intervention_type="full_closure",
        location="JM Basa", is_ambiguous=False,
    )
    sc = parse_scenario("close JM Basa for Dinagyang", client=FakeClient(schema))
    assert sc.intervention_type == "full_closure"
    assert sc.parameters == {}


def test_capacity_change_carries_factor():
    schema = ScenarioSchema(
        description="Widen Diversion Rd by one lane", intervention_type="capacity_change",
        location="Diversion Rd", capacity_factor=1.5, is_ambiguous=False,
    )
    sc = parse_scenario("widen Diversion Rd", client=FakeClient(schema))
    assert sc.intervention_type == "capacity_change"
    assert sc.parameters == {"capacity_factor": 1.5}


def test_ambiguous_query_raises_with_clarification():
    schema = ScenarioSchema(
        description="", intervention_type="lane_closure", is_ambiguous=True,
        clarification_prompt="Where should the school be built?",
    )
    with pytest.raises(ValueError, match="Where should the school"):
        parse_scenario("what if we build a school?", client=FakeClient(schema))
